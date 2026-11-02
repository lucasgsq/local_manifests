#!/usr/bin/env python3
"""Sincroniza os forks Quark e trata a troca de metadados com backup previo."""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


POLICIES = ['device/lineage/sepolicy', 'device/qcom/sepolicy-legacy', 'system/sepolicy']
METADATA_PROJECTS = POLICIES + ['hardware/qcom-caf/apq8084/media', 'hardware/qcom-caf/apq8084/display', 'packages/apps/Settings']
PROJECTS = ['hardware/qcom-caf/apq8084/media', 'hardware/qcom-caf/apq8084/display',
            'device/motorola/quark', 'kernel/motorola/apq8084', 'vendor/motorola',
            'device/qcom/sepolicy-legacy', 'system/sepolicy', 'device/lineage/sepolicy',
            'packages/apps/Settings']


def git(repo, *args):
    result = subprocess.run(['git', '-C', str(repo), *args], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError('Git falhou em '+str(repo)+': '+result.stderr.decode(errors='replace'))
    return result.stdout


def require_clean(repo):
    if git(repo, 'diff', '--name-only', 'HEAD', '-z').strip(b'\0'):
        raise RuntimeError('Ainda existem alteracoes rastreadas em '+str(repo)+
                           '. Nada sera forcado. Nao reaplique os stashes.')


def backup_policy(repo, output):
    require_clean(repo)
    output.mkdir(parents=True, mode=0o700)
    os.chmod(str(output), 0o700)
    head = git(repo, 'rev-parse', 'HEAD').decode().strip()
    bundle = output/'history.bundle'
    git(repo, 'bundle', 'create', str(bundle), '--all', 'HEAD')
    git(repo, 'bundle', 'verify', str(bundle))
    os.chmod(str(bundle), 0o600)
    refs = git(repo, 'for-each-ref', '--format=%(refname) %(objectname)').decode()
    (output/'refs.txt').write_bytes(refs.encode())
    # These files can contain personal settings; they stay in the private backup.
    for name in ['config', 'HEAD', 'index']:
        raw = git(repo, 'rev-parse', '--git-path', name).decode().strip()
        source = Path(raw)
        if not source.is_absolute():
            source = repo/source
        if source.is_file():
            shutil.copyfile(source, output/('git-'+name))
            os.chmod(str(output/('git-'+name)), 0o600)
    untracked = git(repo, 'ls-files', '--others', '--exclude-standard', '-z').decode().split('\0')
    preserved = []
    for name in filter(None, untracked):
        source = repo/name
        if source.is_symlink():
            preserved.append({'name': name, 'symlink': os.readlink(str(source))})
            continue
        try:
            source.resolve().relative_to(repo.resolve())
        except ValueError:
            raise RuntimeError('Arquivo fora do repositorio: '+str(source))
        if not source.is_file():
            raise RuntimeError('Arquivo nao rastreado exige revisao: '+str(source))
        dest = output/'untracked'/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        os.chmod(str(dest), 0o600)
        preserved.append({'name': name, 'bytes': source.stat().st_size})
    record = {'path': str(repo), 'head': head, 'bundle': str(bundle),
              'untracked': preserved, 'working_tree_clean': True}
    (output/'backup.json').write_bytes((json.dumps(record, indent=2)+'\n').encode())
    return record


def run_logged(root, command, logfile):
    print('\nExecutando: '+' '.join(command), flush=True)
    lines = []
    with logfile.open('w', encoding='utf-8') as stream:
        process = subprocess.Popen(command, cwd=str(root), stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, universal_newlines=True,
                                   errors='replace')
        for line in process.stdout:
            print(line, end='', flush=True)
            stream.write(line)
            lines.append(line)
        code = process.wait()
    return code, ''.join(lines)


def metadata_project(output):
    if '--force-sync' not in output or not any(x in output for x in ['hooks is different', 'not enabled', 'different object', 'overwrite a local work tree']):
        return None
    for path in METADATA_PROJECTS:
        if re.search(r'repo sync --force-sync\s+'+re.escape(path)+r'''(?=[\s`'"]|$)''', output) or re.search('/projects/'+re.escape(path)+r'''\.git(?=[\s`'"]|$)''', output):
            return path
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.')
    parser.add_argument('--branch', choices=['A11+KSU', 'A12+'], default='A11+KSU')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = Path(args.root).resolve(strict=True)
    manifests = root/'.repo/local_manifests'
    plan = json.loads((manifests/'selinux-sync-plan.json').read_text())
    if plan['branch'] != args.branch or not (root/'build/envsetup.sh').is_file():
        raise SystemExit('Arvore/branch nao corresponde ao plano selecionado.')
    for path in METADATA_PROJECTS:
        require_clean(root/path)
    print('Arvore: '+str(root))
    print('Somente politicas, media, display e Settings poderao receber --force-sync, apos backup.')
    print('Historicos, refs, stashes e arquivos particulares serao preservados antes do sync.')
    if not args.apply:
        print('Conferencia concluida. Acrescente --apply para fazer backup e sincronizar.')
        return
    if os.name != 'posix':
        raise SystemExit('Execute no Ubuntu.')
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid())
    backup = Path.home()/'quark-sync-backups'/('metadata-'+stamp)
    backup.mkdir(parents=True, mode=0o700)
    os.chmod(str(backup), 0o700)
    records = []
    for path in METADATA_PROJECTS:
        records.append(backup_policy(root/path, backup/path))
        print('Bundle verificado: '+path, flush=True)
    status = {'root': str(root), 'backups': records, 'forced_projects': [], 'completed': False}
    def save():
        (backup/'sync-result.json').write_bytes((json.dumps(status, indent=2)+'\n').encode())
    save()
    print('Backup privado: '+str(backup), flush=True)
    normal = ['repo', 'sync', '-j1', '--fail-fast', *PROJECTS]
    for attempt in range(len(METADATA_PROJECTS)+1):
        code, output = run_logged(root, normal, backup/('sync-'+str(attempt)+'.log'))
        if code == 0:
            for item in plan['repositories']:
                result = subprocess.run(['git', '-C', str(root/item['path']), 'merge-base',
                                         '--is-ancestor', item['commit'], 'HEAD'],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode:
                    raise SystemExit('Commit publicado ainda nao esta em '+item['path']+'. Veja '+str(backup))
            status['completed'] = True
            save()
            print('\nSincronizacao concluida. Os stashes antigos nao devem ser reaplicados.')
            print('Para compilar: bash .repo/local_manifests/build-quark.sh')
            return
        path = metadata_project(output)
        if path is None or path in status['forced_projects']:
            raise SystemExit('Sync interrompido por erro que exige revisao. Logs e backups: '+str(backup))
        require_clean(root/path)
        command = ['repo', 'sync', '--force-sync', '-j1', '--fail-fast', path]
        code, unused = run_logged(root, command, backup/('metadata-'+path.replace('/', '-')+'.log'))
        status['forced_projects'].append(path)
        save()
        if code:
            raise SystemExit('Troca de metadados interrompida. Veja '+str(backup))
    raise SystemExit('Numero de tentativas esgotado. Backups: '+str(backup))


if __name__ == '__main__':
    main()
