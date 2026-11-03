#!/usr/bin/env bash
set -e
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${1:-$PWD}"
source "$script_dir/quark-build.conf"
variant="${BUILD_VARIANT:-$QUARK_DEFAULT_VARIANT}"
jobs="${JOBS:-8}"
case "$variant" in user|userdebug|eng) ;; *) echo 'BUILD_VARIANT invalido.' >&2; exit 2;; esac
[[ "$jobs" =~ ^[1-9][0-9]*$ ]] || exit 2
out="${QUARK_OUT_DIR:-out-$variant}"
case "$out" in /*) export OUT_DIR="$out";; *) export OUT_DIR="$(pwd -P)/$out";; esac
printf 'Variante: %s | OUT_DIR: %s\n' "$variant" "$OUT_DIR"
# Generate the reference before lunch/Soong reads device overlays.
export QUARK_SECURITY_BACKPORT_OVERLAY="device/motorola/quark/overlay-security-generated/$variant"
python3 "$script_dir/check-security-backports.py" \
    --root "$(pwd -P)" --config "$script_dir/security-backport-check.json" \
    --variant "$variant" --out "$OUT_DIR"
source build/envsetup.sh
lunch "lineage_quark-$variant"
sdk="$(get_build_var PLATFORM_SDK_VERSION)"
ignore="$(get_build_var SELINUX_IGNORE_NEVERALLOWS)"
cmdline="$(get_build_var BOARD_KERNEL_CMDLINE)"
[[ "$sdk" == "$QUARK_EXPECTED_SDK" ]] || { echo 'SDK diferente do manifesto selecionado.' >&2; exit 1; }
case "$ignore" in ''|false) ;; *) echo 'SELINUX_IGNORE_NEVERALLOWS nao pode estar habilitado.' >&2; exit 1;; esac
if [[ "$QUARK_EXPECTED_SDK" == 30 || "$variant" == user ]]; then
    case " $cmdline " in *' androidboot.selinux=permissive '*|*' enforcing=0 '*|*' selinux=0 '*) echo 'Cmdline permissive inesperada.' >&2; exit 1;; esac
fi
python3 - "$script_dir" <<'PY'
import json,subprocess,sys,time
from pathlib import Path
folder=Path(sys.argv[1]);plan=json.loads((folder/'selinux-sync-plan.json').read_text())
records=[]
missing=[]
for item in plan['repositories']:
    head=subprocess.run(['git','-C',item['path'],'rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip()
    present=subprocess.run(['git','-C',item['path'],'merge-base','--is-ancestor',item['commit'],'HEAD'],capture_output=True).returncode==0
    dirty=bool(subprocess.run(['git','-C',item['path'],'status','--porcelain'],check=True,capture_output=True).stdout)
    records.append({'path':item['path'],'head':head,'published_head':item['commit'],'contains_published_commit':present,'local_changes':dirty})
    if not present:missing.append(item['path'])
Path('quark-build-sources.json').write_text(json.dumps({'time':time.time(),'sources':records},indent=2)+'\n')
if missing:raise SystemExit('Sincronize os commits publicados antes de compilar: '+', '.join(missing))
PY
set -o pipefail
set +e
mka bacon -j"$jobs" 2>&1 | tee "quark-build-$QUARK_BUILD_LABEL-$variant.log"
result=$?
set -e
exit "$result"
