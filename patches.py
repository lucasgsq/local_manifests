#!/usr/bin/env python3
"""Apply the pinned Quark media/display backports after repo sync.

Python standard library only. No reset, stash, force push or automatic
conflict resolution. --check fetches source objects but creates no commits.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys


class PatchError(RuntimeError):
    pass


def git(repo, *args, check=True):
    env = os.environ.copy()
    env['GIT_TERMINAL_PROMPT'] = '0'
    result = subprocess.run(
        ['git', '-C', str(repo), *args], env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        encoding='utf-8', errors='replace',
    )
    if check and result.returncode:
        raise PatchError('git {} failed in {}:\n{}{}'.format(
            ' '.join(args), repo, result.stdout, result.stderr))
    return result


def load_plan(path):
    plan = json.loads(path.read_text(encoding='utf-8'))
    seen = set()
    for group in plan:
        relative = Path(group['path'])
        if relative.is_absolute() or '..' in relative.parts or not relative.parts:
            raise PatchError('Unsafe project path: {}'.format(relative))
        if group['path'] in seen or not group['commits']:
            raise PatchError('Duplicate project or empty commit list')
        seen.add(group['path'])
        if any(not re.fullmatch(r'[0-9a-f]{40}', c) for c in group['commits']):
            raise PatchError('Every patch must be pinned to a full commit SHA')
        if len(set(group['commits'])) != len(group['commits']):
            raise PatchError('Duplicate commit in {}'.format(relative))
    if not plan:
        raise PatchError('Empty patch plan')
    return plan


def preflight(root, plan, apply):
    if not (root / '.repo').is_dir():
        raise PatchError('Run from the Android source root containing .repo, '
                         'or pass --root /path/to/android')
    for group in plan:
        repo = (root / group['path']).resolve()
        try:
            repo.relative_to(root)
        except ValueError:
            raise PatchError('Project resolves outside Android root: {}'.format(repo))
        if not repo.is_dir():
            raise PatchError('Missing project: {}. Run repo sync first.'.format(repo))
        top = Path(git(repo, 'rev-parse', '--show-toplevel').stdout.strip()).resolve()
        if top != repo:
            raise PatchError('Expected a Git project at {}'.format(repo))
        for state in ('CHERRY_PICK_HEAD', 'MERGE_HEAD', 'REVERT_HEAD',
                      'rebase-apply', 'rebase-merge', 'sequencer'):
            location = Path(git(repo, 'rev-parse', '--git-path', state).stdout.strip())
            if not location.is_absolute():
                location = repo / location
            if location.exists():
                raise PatchError('Unfinished Git operation in {}. Resolve or abort '
                                 'it before running this script.'.format(repo))
        if git(repo, 'status', '--porcelain', '--untracked-files=normal').stdout:
            raise PatchError('Local changes or untracked files in {}. '
                             'Commit or move them before continuing.'.format(repo))
        git(repo, 'rev-parse', '--verify', 'HEAD')
        if apply:
            git(repo, 'var', 'GIT_COMMITTER_IDENT')


def fetch_sources(root, plan):
    # Validate all sources before creating any local patch commits.
    for group in plan:
        repo = root / group['path']
        print('Fetching {} ({})'.format(group['path'], group['branch']), flush=True)
        git(repo, 'fetch', '--no-tags', group['url'], group['branch'])
        fetched = git(repo, 'rev-parse', 'FETCH_HEAD').stdout.strip()
        for commit in group['commits']:
            git(repo, 'cat-file', '-e', commit + '^{commit}')
            parents = git(repo, 'rev-list', '--parents', '-n', '1', commit).stdout.split()
            if len(parents) != 2:
                raise PatchError('Expected a non-merge commit with one parent: ' + commit)
            git(repo, 'merge-base', '--is-ancestor', commit, fetched)


def already_present(repo, commit):
    result = git(repo, 'merge-base', '--is-ancestor', commit, 'HEAD', check=False)
    if result.returncode == 0:
        return True
    if result.returncode != 1:
        raise PatchError(result.stderr)
    # Limit the source side to one commit. Git also compares patch equivalence
    # against the destination history, catching earlier cherry-picks with new SHAs.
    lines = git(repo, 'cherry', 'HEAD', commit, commit + '^').stdout.splitlines()
    if len(lines) != 1 or lines[0][2:] != commit or lines[0][0] not in '+-':
        raise PatchError('Unexpected patch-equivalence result for ' + commit)
    return lines[0].startswith('- ')


def run(root, plan, apply=False):
    root = root.resolve()
    preflight(root, plan, apply)
    fetch_sources(root, plan)
    applied = skipped = pending = 0
    for group in plan:
        repo = root / group['path']
        for commit in group['commits']:
            if already_present(repo, commit):
                print('SKIP  {} {}'.format(group['path'], commit), flush=True)
                skipped += 1
                continue
            if not apply:
                print('TODO  {} {}'.format(group['path'], commit), flush=True)
                pending += 1
                continue
            print('APPLY {} {}'.format(group['path'], commit), flush=True)
            result = git(repo, '-c', 'rerere.enabled=false', 'cherry-pick', '-x', commit,
                         check=False)
            if result.returncode:
                raise PatchError(
                    '{}{}\nStopped at {} in {}. Earlier successful commits remain.\n'
                    'Inspect git status in that project. Resolve and use git cherry-pick '
                    '--continue, or cancel this pick with git cherry-pick --abort.\n'
                    'Then rerun the script. No automatic rollback or conflict '
                    'resolution was performed.'.format(
                        result.stdout, result.stderr, commit, repo))
            applied += 1
    print('Done: {} applied, {} already present, {} pending.'.format(
        applied, skipped, pending))
    if not apply:
        print('Check mode only: no patch commits created. This is not a build or '
              'conflict-free application test. Use --apply to apply pending patches.')
    return applied, skipped, pending


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='fetch and list patch status (default)')
    mode.add_argument('--apply', action='store_true', help='apply pending pinned commits in order')
    parser.add_argument('--root', type=Path, default=Path.cwd(), help='Android source root')
    args = parser.parse_args()
    try:
        plan = load_plan(Path(__file__).resolve().with_name('patches.json'))
        run(args.root, plan, args.apply)
    except (PatchError, OSError, ValueError, KeyError, TypeError) as error:
        print('ERROR: {}'.format(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
