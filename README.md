## LineageOS 18.1 local_manifests for Moto Maxx (Quark)

This is the current Moto Maxx (Quark) manifest for LineageOS 18.1 (Android 11). 

This branch selects the `Shamu-LOS-18.1-based` Quark test kernel and includes `system/qcom` for the `libqsap_sdk` dependency required by `libqsapshim`.
These repos are only validated to build LineageOS ROMs. Any other custom ROM is unsupported.

Steps to build

    Clone Lineage 18.1 repo and setup your build environment according to the Lineage documentation
    (you can use the Shamu's (Nexus 6) build guide as a reference guide, but remember we're building for Quark!)
    https://wiki.lineageos.org/devices/shamu/build/
    
Download the manifest and patch automation from this test branch. Run these commands from the Android source root:

    mkdir -p .repo/local_manifests
    for file in quark.xml patches.sh patches.py patches.json; do
        wget -O ".repo/local_manifests/$file" "https://raw.githubusercontent.com/lucasgsq/local_manifests/Shamu-LOS-18.1-based/$file" || break
    done

Keep only one copy of the Quark manifest: if `roomservice.xml` already declares the same projects, replace that manifest rather than keeping duplicate declarations in both XML files. Back up local edits before replacing files.

Sync first, then check and apply the pinned media/display patches:

    repo sync
    sh .repo/local_manifests/patches.sh --check
    sh .repo/local_manifests/patches.sh --apply

The script requires Python 3 and Git, normally available in the Android 11 build environment. It can also be run directly with `python3 .repo/local_manifests/patches.py`. Use `--root /path/to/android` when running from another directory. Without an option it defaults to `--check`.

`--check` fetches the source branches and lists pending/already-present commits. It creates no patch commits and does not test compilation or conflict-free application. `--apply` cherry-picks only missing patches, in the order pinned in `patches.json`, recording source SHAs with `-x`. The five media commits match the original inclusive range `efd4fd850c712bc43b2462b2ad3d753a8e0af043^..cfe448c898ee4c0cf7c98b873e789c0fd58e6675`; display uses `2488ddb917b4fd36e25ad0fcd2bfe554e0357d42`.

All project working trees must be clean, with no pending merge/rebase/cherry-pick. Existing commits are detected by ancestry or Git patch equivalence, so repeating the script does not duplicate equivalent patches. Contextually adapted implementations with different patch content may still require manual review.

Detection uses Git history, not a semantic audit of the final source. If a patch was later reverted or replaced, review that history before relying on an `SKIP` result.

If a cherry-pick conflicts, the script stops and leaves Git's recovery state intact. In the reported project, inspect `git status`, resolve the conflict and run `git cherry-pick --continue`, or cancel the current pick with `git cherry-pick --abort`. Then rerun the script. Earlier successful commits remain; there is no automatic reset, stash, rollback, or push. Do not run `repo sync` or another patch process concurrently with the script.

Recheck after future `repo sync` operations. The script does not install a sync hook or replace the source projects with forks. Kernel patches are already tracked by the `Shamu-LOS-18.1-based` kernel branch and are not repeated here.

After the patches have been applied successfully:

    source build/envsetup.sh
    
    lunch lineage_quark-[buildflag]
    
    make bacon -j[cpucorecount]

Replace buildflag with the type of ROM you are trying to build. Valid codenames:

    user: for user builds
    userdebug: for user-debug builds


Replace core count with the number of CPU cores you have.
