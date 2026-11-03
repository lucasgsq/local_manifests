#!/usr/bin/env python3
"""Generate a conservative, build-specific reference to LineageOS ASB batches.

This checks published Git ancestry, not full bulletin/CVE coverage. It never
fetches Git objects or modifies tracked sources. No network cache is trusted.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

GERRIT = 'https://review.lineageos.org'
MONTH = re.compile(r'20\d{2}-(?:0[1-9]|1[0-2])\Z')
SHA = re.compile(r'[0-9a-f]{40}\Z')
TOPIC = re.compile(r'([RS])_asb_(20\d{2})[-_](0[1-9]|1[0-2])(?:_[a-zA-Z0-9_-]+)?\Z')
RESOURCE = 'packages/apps/Settings/res/values/lineage_security_backport_generated.xml'


class Unverified(Exception):
    pass


def run(root, args):
    env = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')
    return subprocess.run(args, cwd=str(root), env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, timeout=60)


def git(path, *args):
    return run(path, ['git', '-C', str(path), *args])


def atomic_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding='utf-8') == text:
        return
    temporary = path.with_name(path.name + '.tmp-' + str(os.getpid()))
    temporary.write_text(text, encoding='utf-8')
    temporary.replace(path)


def write_overlay(overlay, month):
    if month and not MONTH.fullmatch(month):
        raise ValueError('Invalid reference month')
    xml = ET.Element('resources')
    item = ET.SubElement(xml, 'string', {
        'name': 'config_lineageSecurityBackportMonth', 'translatable': 'false'})
    item.text = month
    atomic_text(overlay / RESOURCE,
                '<?xml version="1.0" encoding="utf-8"?>\n'
                + ET.tostring(xml, encoding='unicode') + '\n')


def query_changes(branch, prefix, status, opener=urllib.request.urlopen):
    query = 'branch:{} status:{} intopic:^{}_asb_.*'.format(branch, status, prefix)
    result, seen = [], set()
    for page in range(40):
        parameters = urllib.parse.urlencode({
            'q': query, 'n': 500, 'S': page * 500, 'o': 'CURRENT_REVISION'})
        request = urllib.request.Request(GERRIT + '/changes/?' + parameters,
                                         headers={'User-Agent': 'Quark-ASB-check/1'})
        with opener(request, timeout=15) as response:
            raw = response.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024 or not raw.startswith(b")]}'"):
            raise Unverified('Invalid Gerrit response')
        changes = json.loads(raw.split(b'\n', 1)[1])
        if not isinstance(changes, list):
            raise Unverified('Incomplete Gerrit result')
        for change in changes:
            number = change.get('_number')
            if number is None or number in seen:
                raise Unverified('Repeated or invalid Gerrit page; retry the check')
            seen.add(number)
            if change.get('branch') != branch or change.get('status') != status.upper():
                # Gerrit represents open changes as NEW, not OPEN.
                if not (status == 'open' and change.get('branch') == branch
                        and change.get('status') == 'NEW'):
                    raise Unverified('Unexpected branch/status in Gerrit response')
            result.append(change)
        if not changes or not changes[-1].get('_more_changes'):
            return result
    raise Unverified('Gerrit pagination limit reached')


def catalog(branch, prefix, minimum_month, loader=query_changes):
    merged = loader(branch, prefix, 'merged')
    pending = loader(branch, prefix, 'open')
    batches = {}
    for status, changes in [('merged', merged), ('open', pending)]:
        for change in changes:
            match = TOPIC.fullmatch(change.get('topic', ''))
            if not match or match.group(1) != prefix:
                # Unrecognized ASB naming cannot silently disappear from the audit.
                raise Unverified('Unrecognized ASB topic: ' + change.get('topic', ''))
            month = match.group(2) + '-' + match.group(3)
            if month < minimum_month:
                continue
            if not SHA.fullmatch(change.get('current_revision', '')):
                raise Unverified('Missing current revision in Gerrit')
            batches.setdefault(month, {'merged': [], 'open': []})[status].append(change)
    if not any(batch['merged'] for batch in batches.values()):
        raise Unverified('No published batches found for this Android branch')
    return batches


def manifest_projects(root):
    result = run(root, ['repo', 'manifest'])
    if result.returncode:
        raise Unverified('Cannot inspect local manifest: ' + result.stderr[-1000:])
    projects = {}
    document = ET.fromstring(result.stdout)
    for item in document.iter('project'):
        name = item.get('name')
        relative = item.get('path') or name
        if not name or not relative:
            raise Unverified('Invalid project in local manifest')
        projects.setdefault(name, []).append(relative)
    return projects


def resolve_project(root, project, projects):
    paths = projects.get(project, [])
    if not paths:
        # Quark's owned forks retain the upstream repository basename.
        basename = project.rsplit('/', 1)[-1]
        paths = [path for name, values in projects.items()
                 if name.rsplit('/', 1)[-1] == basename for path in values]
    if not paths:
        return []
    result = []
    for relative in paths:
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            raise Unverified('Project path outside source tree: ' + relative)
        result.append((relative, path))
    return result


def inspect_repo(root, relative, path, minimum_month):
    record = {'path': relative}
    if not path.is_dir():
        record['problem'] = 'declared_project_missing'
        return record
    top = git(path, 'rev-parse', '--show-toplevel')
    if top.returncode or Path(top.stdout.strip()).resolve() != path:
        record['problem'] = 'not_the_expected_git_worktree'
        return record
    head = git(path, 'rev-parse', '--verify', 'HEAD^{commit}')
    if head.returncode or not SHA.fullmatch(head.stdout.strip()):
        record['problem'] = 'cannot_resolve_head'
        return record
    record['head'] = head.stdout.strip()
    changes = git(path, 'status', '--porcelain', '--untracked-files=normal')
    if changes.returncode or changes.stdout.strip():
        record['problem'] = 'local_changes_or_unresolved_conflicts'
        return record
    # Standard revert messages are a conservative rejection. Revert-of-revert
    # and equivalent cherry-picks require review rather than optimistic credit.
    history = git(path, 'log', '--format=%H%x00%B%x00', '--fixed-strings',
                  '--grep=This reverts commit', 'HEAD')
    if history.returncode:
        record['problem'] = 'cannot_check_revert_history'
        return record
    record['reverts'] = []
    parts = history.stdout.split('\0')
    for index in range(0, len(parts) - 1, 2):
        reverter, body = parts[index].strip(), parts[index + 1]
        if not SHA.fullmatch(reverter):
            raise Unverified('Cannot parse revert history in ' + relative)
        for target in re.findall(r'This reverts commit ([0-9a-f]{7,40})', body):
            record['reverts'].append({'reverter': reverter, 'target': target})
    record['shallow'] = git(path, 'rev-parse', '--is-shallow-repository').stdout.strip()
    return record


def verify_batches(root, projects, batches, minimum_month):
    repositories, rows = {}, []
    published = {(change['project'], change['current_revision']): month for month, batch in batches.items()
                 for change in batch['merged']}
    for month in sorted(batches):
        for change in batches[month]['merged']:
            project = change.get('project', '')
            paths = resolve_project(root, project, projects)
            common = {'month': month, 'topic': change['topic'], 'project': project,
                      'commit': change['current_revision'], 'change': change['_number']}
            if not paths:
                rows.append(dict(common, status='outside_current_manifest'))
                continue
            # Every local instance of a shared repository must contain the fix.
            for relative, path in paths:
                if relative not in repositories:
                    repositories[relative] = inspect_repo(root, relative, path, minimum_month)
                repo = repositories[relative]
                row = dict(common, path=relative, head=repo.get('head'))
                if repo.get('problem'):
                    row['status'] = repo['problem']
                else:
                    commit = common['commit']
                    exists = git(path, 'cat-file', '-e', commit + '^{commit}')
                    if exists.returncode:
                        row['status'] = 'commit_object_unavailable'
                    else:
                        ancestor = git(path, 'merge-base', '--is-ancestor', commit, 'HEAD')
                        if ancestor.returncode == 1:
                            row['status'] = 'not_ancestor_equivalence_not_assumed'
                        elif ancestor.returncode:
                            row['status'] = 'ancestry_check_failed'
                        else:
                            row['status'] = 'present'
                            reverts = [r for r in repo['reverts'] if commit.startswith(r['target'])]
                            # A revert published as part of an ASB batch is itself
                            # an expected upstream transition, not a local omission.
                            if any((project, r['reverter']) not in published for r in reverts):
                                row['status'] = 'explicit_revert_requires_review'
                            row['upstream_revert_months'] = [published[(project, r['reverter'])]
                                for r in reverts if (project, r['reverter']) in published]
                rows.append(row)
    summaries, verified = [], ''
    for month in sorted(batches):
        local = [row for row in rows if row['month'] <= month
                 and row['status'] != 'outside_current_manifest']
        # Any open change keeps this month's topic provisional. We do not
        # attribute newer months after an incomplete earlier batch.
        pending = sum(len(batch['open']) for key, batch in batches.items() if key <= month)
        current = any(row['month'] == month for row in local)
        complete = current and not pending and all(
            row['status'] == 'present' and all(m <= month for m in row.get('upstream_revert_months', []))
            for row in local)
        summaries.append({'month': month, 'applicable_checks': len(local),
                          'open_changes': pending, 'complete': complete})
        if complete:
            verified = month
    return {'month': verified, 'batches': summaries, 'checks': rows,
            'repositories': repositories}


def perform(root, config, loader=query_changes, project_loader=manifest_projects):
    branch, prefix = config['branch'], config['topic_prefix']
    if (branch, prefix) not in [('lineage-18.1', 'R'), ('lineage-19.1', 'S')]:
        raise ValueError('Unsupported Android branch/topic combination')
    minimum = config['minimum_month']
    if not MONTH.fullmatch(minimum):
        raise ValueError('Invalid minimum month')
    batches = catalog(branch, prefix, minimum, loader)
    result = verify_batches(root, project_loader(root), batches, minimum)
    # Detect source changes during the audit before giving credit.
    for relative, repo in result['repositories'].items():
        if 'head' not in repo:
            continue
        path = root / relative
        head = git(path, 'rev-parse', 'HEAD')
        dirty = git(path, 'status', '--porcelain', '--untracked-files=normal')
        if head.returncode or head.stdout.strip() != repo['head'] or dirty.returncode or dirty.stdout.strip():
            result['month'] = ''
            result['error'] = 'Sources changed or remained dirty during audit: ' + relative
    return result


def execute(root, overlay, report_path, config, audit=perform):
    # A failed online query must never retain the preceding build's month.
    write_overlay(overlay, '')
    report = {'schema': 1, 'checked_at_utc': datetime.datetime.now(
        datetime.timezone.utc).isoformat(), 'branch': config['branch'],
        'minimum_month': config['minimum_month'], 'month': '',
        'scope': 'Published ASB topics: Git ancestry and standard reverts, not full CVE coverage',
        'source': GERRIT, 'network_cache_used': False}
    try:
        report.update(audit(root, config))
    except (Unverified, OSError, ValueError, KeyError, subprocess.SubprocessError,
            ET.ParseError) as error:
        report['error'] = str(error)
    write_overlay(overlay, report['month'])
    atomic_text(report_path, json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print('Backports LineageOS: ' + (report['month'] or 'Nao verificado'), flush=True)
    if report.get('error'):
        print('Motivo: ' + report['error'], flush=True)
    print('Relatorio: ' + str(report_path), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.')
    parser.add_argument('--config', required=True)
    parser.add_argument('--variant', choices=['user', 'userdebug', 'eng'], required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve(strict=True)
    if not (root / 'build/envsetup.sh').is_file():
        raise SystemExit('Execute na raiz da arvore Android')
    device_mk = root / 'device/motorola/quark/device.mk'
    if not device_mk.is_file() or '$(QUARK_SECURITY_BACKPORT_OVERLAY)' not in device_mk.read_text(encoding='utf-8'):
        raise SystemExit('Sincronize a device tree com o suporte a checagem automatica de backports.')
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    overlay = root / 'device/motorola/quark/overlay-security-generated' / args.variant
    # Do not follow a symlink into another source/output directory.
    if overlay.resolve() != overlay or any(p.is_symlink() for p in [overlay, *overlay.parents]):
        raise SystemExit('Caminho do overlay gerado contem link simbolico')
    destination = Path(args.out).resolve() / 'quark-security-backports.json'
    print('Conferindo lotes de backports publicados para ' + config['branch'] + '...', flush=True)
    execute(root, overlay, destination, config)


if __name__ == '__main__':
    main()
