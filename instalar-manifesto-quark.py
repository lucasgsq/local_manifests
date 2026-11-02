#!/usr/bin/env python3
"""Instala o manifesto Quark preservando a pasta anterior e XMLs particulares."""
import argparse
import datetime
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


URL = 'https://github.com/lucasgsq/local_manifests.git'
PATHS = {
    'hardware/qcom-caf/apq8084/media', 'hardware/qcom-caf/apq8084/display',
    'device/motorola/quark', 'kernel/motorola/apq8084', 'vendor/motorola',
    'device/qcom/sepolicy-legacy', 'system/sepolicy', 'device/lineage/sepolicy',
    'system/qcom', 'hardware/sony/timekeep',
}
NAMES = {
    'lucasgsq/android_hardware_qcom_media', 'lucasgsq/android_hardware_qcom_display',
    'lucasgsq/device_motorola_quark', 'lucasgsq/kernel_motorola_apq8084',
    'lucasgsq/proprietary_vendor_motorola', 'lucasgsq/android_device_qcom_sepolicy',
    'lucasgsq/android_system_sepolicy', 'lucasgsq/android_device_lineage_sepolicy',
    'LineageOS/android_hardware_qcom_media', 'LineageOS/android_hardware_qcom_display',
    'LineageOS/android_device_qcom_sepolicy', 'LineageOS/android_system_sepolicy',
    'LineageOS/android_device_lineage_sepolicy', 'LineageOS/android_system_qcom',
    'LineageOS/android_hardware_sony_timekeep',
}


def parse_xml(path):
    if path.is_symlink() or path.stat().st_size > 4*1024*1024:
        raise ValueError('XML simbolico ou grande demais: '+str(path))
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    tree = ET.parse(str(path), parser=parser)
    if tree.getroot().tag != 'manifest':
        raise ValueError('XML nao e manifesto: '+str(path))
    return tree


def preserve_xmls(old, staging):
    """Drop replaced project entries, retaining unrelated manifest settings."""
    preserved = []
    if not old.exists():
        return preserved
    files = sorted(old.rglob('*.xml'))
    for source in files:
        rel = source.relative_to(old)
        if '.git' in rel.parts:
            continue
        # Refuse symlinked parents as well as symlinked files.
        if any(p.is_symlink() for p in [source, *source.parents] if p != old.parent):
            raise ValueError('XML atravessa link simbolico: '+str(source))
        tree = parse_xml(source)
        root = tree.getroot()
        for node in list(root):
            if node.tag in ('project', 'extend-project', 'remove-project'):
                path = node.get('path')
                if path in PATHS or not path and node.get('name') in NAMES:
                    root.remove(node)
        if not any(isinstance(node.tag, str) for node in root):
            continue
        target = staging/rel
        if target.exists():
            if rel != Path('quark.xml'):
                raise ValueError('XML particular conflita com arquivo publicado: '+str(rel))
            target = staging/'local-preserved-quark.xml'
            if target.exists():
                raise ValueError('Nome de preservacao ja existe no checkout novo.')
        target.parent.mkdir(parents=True, exist_ok=True)
        tree.write(str(target), encoding='utf-8', xml_declaration=True)
        preserved.append(target.relative_to(staging).as_posix())
    return preserved


def activate(root, staging, backup):
    metadata = (root/'.repo').resolve()
    old = root/'.repo/local_manifests'
    for path in [old, staging, backup]:
        if path.is_symlink() or path.resolve().parent != metadata:
            raise ValueError('Caminho de instalacao fora do local esperado: '+str(path))
    if backup.exists():
        raise ValueError('Backup ja existe: '+str(backup))
    had_old = old.exists()
    if had_old:
        old.rename(backup)
    try:
        staging.rename(old)
    except BaseException:
        if had_old:
            backup.rename(old)
        raise
    return old


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.')
    parser.add_argument('--branch', choices=['A11+KSU', 'A12+'], default='A11+KSU')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = Path(args.root).resolve(strict=True)
    if not (root/'build/envsetup.sh').is_file() or not (root/'.repo').is_dir() or not (root/'device/motorola/quark').is_dir():
        raise SystemExit('Execute na raiz Android do Quark ou informe --root CAMINHO.')
    if (root/'.repo').is_symlink():
        raise SystemExit('.repo e um link; requer revisao antes de reorganizar os manifestos.')
    old = root/'.repo/local_manifests'
    if old.is_symlink() or old.exists() and not old.is_dir():
        raise SystemExit('local_manifests nao e uma pasta regular; nada foi alterado.')
    print('Arvore: '+str(root))
    print('Branch: '+args.branch)
    print('A pasta atual sera preservada integralmente fora de local_manifests.')
    if not args.apply:
        print('Somente planejamento. Acrescente --apply para instalar e preparar os patches locais.')
        return
    if os.name != 'posix':
        raise SystemExit('Execute a instalacao no Ubuntu, nao no Windows.')
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid())
    staging = root/'.repo'/('quark-manifest-install-'+stamp)
    backup = root/'.repo'/('local_manifests-before-'+stamp)
    assert not staging.exists()
    subprocess.run(['git', 'clone', '--depth', '1', '--branch', args.branch, URL, str(staging)], check=True)
    preserved = preserve_xmls(old, staging)
    if preserved:
        exclude = staging/'.git/info/exclude'
        with exclude.open('a', encoding='utf-8') as stream:
            stream.write('\n# Local XMLs preserved by the Quark installer.\n')
            for name in preserved:
                if any(c in name for c in '\n\r*?[]!#\\'):
                    raise ValueError('Nome XML requer revisao: '+name)
                stream.write('/'+name+'\n')
    # Detect duplicate project paths across all active local manifests.
    paths = {}
    for xml in staging.glob('*.xml'):
        for node in parse_xml(xml).getroot().findall('project'):
            path = node.get('path', node.get('name'))
            if path in paths:
                raise ValueError('Projeto duplicado: '+str(path)+' em '+str(xml))
            paths[path] = xml.name
    installed = activate(root, staging, backup)
    print('Manifesto instalado como repositorio Git: '+str(installed))
    print('Pasta anterior preservada: '+str(backup))
    print('XMLs particulares preservados: '+str(len(preserved)))
    print('Conferindo os patches locais antes de repo sync...', flush=True)
    subprocess.run(['python3', str(installed/'prepare-sync.py'), '--root', str(root), '--apply'], check=True)
    print('\nPreparacao concluida. Agora execute repo sync. Nao reaplique os stashes guardados.')
    print('Nenhuma fonte foi descartada; nenhuma limpeza ou sincronizacao forcada foi executada.')


if __name__ == '__main__':
    main()
