#!/usr/bin/env python3
"""Back up and stash only locally validated files now committed upstream."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    plan = json.loads((Path(__file__).resolve().parent/'selinux-sync-plan.json').read_text())
    pending = []
    for item in plan['repositories']:
        repo = root/item['path']
        if not (repo/'.git').exists():
            raise SystemExit('Repositorio ausente: '+str(repo))
        dirty = set(git(repo, 'diff', '--name-only', 'HEAD', '-z').decode().split('\0'))
        dirty.update(git(repo, 'ls-files', '--others', '--exclude-standard', '-z').decode().split('\0'))
        names = sorted(dirty.intersection(item['files']))
        if not names:
            continue
        for name in names:
            path = repo/name
            if not path.is_file() or path.is_symlink():
                raise SystemExit('Arquivo removido/simbolico exige revisao: '+str(path))
            try:
                path.resolve().relative_to(repo.resolve())
            except ValueError:
                raise SystemExit('Arquivo fora do repositorio: '+str(path))
            data = path.read_bytes()
            if not item['files'][name]['binary']:
                data = data.replace(b'\r\n', b'\n')
            if hashlib.sha256(data).hexdigest() != item['files'][name]['sha256']:
                raise SystemExit('Edicao local difere da versao publicada: '+str(path)+
                                 '. Nenhum arquivo foi guardado ou alterado.')
        pending.append((item, repo, names))
    print('Repositorios com ajustes locais publicados: '+str(len(pending)))
    if not args.apply:
        print('Somente verificacao. Use --apply para backup e stash seletivo.')
        return
    if not pending:
        print('Nenhum stash necessario. Edicoes particulares foram preservadas.')
        return
    parent = Path.home()/'quark-sync-backups'
    backup = parent/(time.strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid()))
    backup.mkdir(parents=True, mode=0o700)
    os.chmod(str(backup), 0o700)
    records = []
    index = backup/'migration.json'
    # Complete all file backups before changing any working tree.
    for item, repo, names in pending:
        for name in names:
            dest = backup/item['path']/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(repo/name, dest)
            os.chmod(str(dest), 0o600)
        records.append({'path': item['path'], 'head': git(repo, 'rev-parse', 'HEAD').decode().strip(),
                        'files': names, 'stash': None})
    index.write_bytes((json.dumps(records, indent=2)+'\n').encode())
    try:
        for record, (item, repo, names) in zip(records, pending):
            git(repo, 'stash', 'push', '-u', '-m', 'quark: validated SELinux changes now published', '--', *names)
            record['stash'] = git(repo, 'rev-parse', 'refs/stash').decode().strip()
            index.write_bytes((json.dumps(records, indent=2)+'\n').encode())
            print('Guardado: '+item['path'])
    except BaseException:
        print('Operacao interrompida. Backups e stashes registrados em '+str(index))
        print('Nao execute repo sync antes de revisar esse registro.')
        raise
    print('Backup local: '+str(backup))
    print('Nao reaplique esses stashes apos o sync: o codigo ja esta nos commits publicados.')
    print('Configuracao local de assinatura e arquivos fora da lista nao foram alterados.')


if __name__ == '__main__':
    main()
