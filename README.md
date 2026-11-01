## Quark A11+KSU experimental LineageOS 18.1 manifest

This branch selects kernel `A11+KSU`, with pinned backslashxx KernelSU
21a0a46155d964927afab6fde40b9a09aa995357 built into the ARM32 kernel.
Device and vendor remain `A11+`, including the optional-app changes.
Global SELinux remains enforcing. This is an experimental root integration,
not a boot-tested release. See the kernel's Documentation/quark-kernelsu.md.

To select this manifest in a separate LineageOS 18.1 workspace, download
quark.xml from branch A11+KSU rather than A11+. Do not change manifests or
sync while a build is running. Only the kernel selection differs from A11+.
The general A11+ build instructions below still apply; substitute A11+KSU
only in local_manifests download URLs, not in device/vendor references.

This is the current Moto Maxx (Quark) manifest for LineageOS 18.1 (Android 11). 

Vendor sources use `lucasgsq/proprietary_vendor_motorola` branch `A11+`.
TurboToast and Kernel Adiutor are no longer preinstalled. To install Kernel
Adiutor as an uninstallable user app, use the original presigned APK at
`vendor/motorola/quark/proprietary/vendor/app/KernelAdiutor/KernelAdiutor.apk`
after installing the updated ROM. The APK remains archived in Git but is not
selected in PRODUCT_PACKAGES. See `OPTIONAL_APPS.md` for installation details.

This branch selects the `A11+` Quark test kernel and includes `system/qcom` for the `libqsap_sdk` dependency required by `libqsapshim`.

The device tree also uses `A11+`. Its boot command line explicitly requests global SELinux enforcing mode (`enforcing=1 androidboot.selinux=enforcing`) for policy testing. After updating this manifest, sync both `device/motorola/quark` and `kernel/motorola/apq8084`, rebuild the ROM, then verify `adb shell getenforce` reports `Enforcing`. Do not assume that installing a newly built image proves the runtime mode. The pre-existing userdebug `sudaemon` permissive-domain policy and recovery-specific permissive service are unchanged. Keep the previously booting ROM available while testing policy denials; unrelated local build modifications or root tools can still affect the observed runtime mode.

The APQ8084 media and display projects now come from owned repositories, both on `A11+`:

- https://github.com/lucasgsq/android_hardware_qcom_media
- https://github.com/lucasgsq/android_hardware_qcom_display

Their original Git histories and the six requested patch commits are preserved. Media ends at `cfe448c898ee4c0cf7c98b873e789c0fd58e6675`; display ends at `2488ddb917b4fd36e25ad0fcd2bfe554e0357d42`. Normal synchronization and the optional patch checker no longer fetch from fgl27. Author credits, commit messages, and licenses remain intact. See `SOURCE_PROVENANCE.md` for the preserved bases and patch list.
These repos are only validated to build LineageOS ROMs. Any other custom ROM is unsupported.

Steps to build

    Clone Lineage 18.1 repo and setup your build environment according to the Lineage documentation
    (you can use the Shamu's (Nexus 6) build guide as a reference guide, but remember we're building for Quark!)
    https://wiki.lineageos.org/devices/shamu/build/
    
Download the manifest and patch automation from this test branch. Run these commands from the Android source root:

    mkdir -p .repo/local_manifests
    for file in quark.xml patches.sh patches.py patches.json; do
        wget -O ".repo/local_manifests/$file" "https://raw.githubusercontent.com/lucasgsq/local_manifests/A11+/$file" || break
    done

Keep only one copy of the Quark manifest: if `roomservice.xml` already declares the same projects, replace that manifest rather than keeping duplicate declarations in both XML files. Back up local edits before replacing files.

For an existing build tree, preserve local edits and commits before changing project sources. For example, create backup branches in the two projects before the first sync with this updated manifest:

    git -C hardware/qcom-caf/apq8084/media branch backup-before-owned-sources-20261030 HEAD
    git -C hardware/qcom-caf/apq8084/display branch backup-before-owned-sources-20261030 HEAD

These commands preserve committed history only; commit or separately back up any uncommitted work. If a backup branch with this name already exists, choose a new name rather than replacing it.

With this manifest, sync already includes all six patches. No manual cherry-picking or `--apply` step is normally needed:

    repo sync
    sh .repo/local_manifests/patches.sh --check

If sync reports a project-source mismatch, stop and inspect the saved branches and the error before using any force option. This update does not run sync or rewrite your existing build tree automatically.

The patch script is retained as an optional checker and migration tool. If a compatible older checkout still needs the patches, use `sh .repo/local_manifests/patches.sh --apply`. Its fetch URLs now point to your owned repositories.

The script requires Python 3 and Git, normally available in the Android 11 build environment. It can also be run directly with `python3 .repo/local_manifests/patches.py`. Use `--root /path/to/android` when running from another directory. Without an option it defaults to `--check`.

`--check` fetches the source branches and lists pending/already-present commits. It creates no patch commits and does not test compilation or conflict-free application. `--apply` cherry-picks only missing patches, in the order pinned in `patches.json`, recording source SHAs with `-x`. The five media commits match the original inclusive range `efd4fd850c712bc43b2462b2ad3d753a8e0af043^..cfe448c898ee4c0cf7c98b873e789c0fd58e6675`; display uses `2488ddb917b4fd36e25ad0fcd2bfe554e0357d42`.

All project working trees must be clean, with no pending merge/rebase/cherry-pick. Existing commits are detected by ancestry or Git patch equivalence, so repeating the script does not duplicate equivalent patches. Contextually adapted implementations with different patch content may still require manual review.

Detection uses Git history, not a semantic audit of the final source. If a patch was later reverted or replaced, review that history before relying on an `SKIP` result.

If a cherry-pick conflicts, the script stops and leaves Git's recovery state intact. In the reported project, inspect `git status`, resolve the conflict and run `git cherry-pick --continue`, or cancel the current pick with `git cherry-pick --abort`. Then rerun the script. Earlier successful commits remain; there is no automatic reset, stash, rollback, or push. Do not run `repo sync` or another patch process concurrently with the script.

Recheck after future `repo sync` operations. The script does not install a sync hook or replace the source projects with forks. Kernel patches are already tracked by the `A11+` kernel branch and are not repeated here.

After the patches have been applied successfully:

    source build/envsetup.sh
    
    lunch lineage_quark-[buildflag]
    
    make bacon -j[cpucorecount]

Replace buildflag with the type of ROM you are trying to build. Valid codenames:

    user: for user builds
    userdebug: for user-debug builds


Replace core count with the number of CPU cores you have.
