# Quark A12+ â€” experimental LineageOS 19.1 manifest

This branch targets Android 12.1 / LineageOS 19.1. It is a source-selection
starting point, not a successfully built or boot-tested ROM. Keep the existing
LineageOS 18.1 workspace and A11+ manifest unchanged.

## Source selection

| Project | Branch |
|---|---|
| lucasgsq/device_motorola_quark | A12+ |
| lucasgsq/kernel_motorola_apq8084 | A12+ |
| lucasgsq/android_hardware_qcom_media | A11+ (legacy baseline) |
| lucasgsq/android_hardware_qcom_display | A11+ (legacy baseline) |
| LineageOS/android_hardware_qcom_audio | lineage-18.1-caf-apq8084 |
| LineageOS/android_device_qcom_sepolicy at device/qcom/sepolicy-legacy | lineage-18.1-legacy |
| LineageOS/android_system_qcom | lineage-19.1 |
| LineageOS/android_hardware_sony_timekeep | lineage-19.1 |
| lucasgsq/proprietary_vendor_motorola | A12+ (legacy blobs, optional third-party apps excluded) |

Upstream LineageOS 19.1 no longer declares APQ8084 projects or the legacy
Qualcomm policy path. quark.xml supplies them explicitly without removing
absent upstream projects. A device-project linkfile restores the APQ8084
Make namespace guard omitted upstream. Media/display patches remain in the
user's repositories; patches.json still selects these owned A11+ baselines.
Android 12 API compatibility of the legacy projects is not yet validated.

TurboToast and Kernel Adiutor are no longer preinstalled. The original
presigned Kernel Adiutor APK can be installed manually as an uninstallable
user app; see `OPTIONAL_APPS.md`. This does not change A12+ SELinux settings.

Kernel A12+ now includes A11+ through f9c074c2cab: keys/perf retained and the
problematic math64 change reverted. There is no distinct active Android 12
kernel patch series yet. Device A12+ includes A11+ through 06687bfe plus its
own Android 12 overlay/ueventd migrations. Pending A11+ audio experiments
are included; their device validation is still outstanding.

## Separate workspace

Run in a new build directory on the Ubuntu machine, preserving lineage18:

```bash
mkdir -p ~/android/lineage19
cd ~/android/lineage19
repo init -u https://github.com/LineageOS/android.git -b lineage-19.1
git clone --branch 'A12+' --single-branch https://github.com/lucasgsq/local_manifests.git .repo/local_manifests
repo sync -j4
```

Avoid duplicate roomservice.xml declarations. Do not reuse Android 11 out.
The first build is an integration check, not an expected bootable release:

```bash
source build/envsetup.sh
lunch lineage_quark-userdebug
mka bacon -j8
```

Preserve private signing keys separately. No keys or local certificate
overrides are copied automatically from lineage18. Use the same keys if
signed-update continuity is needed. Save `repo manifest -r` alongside each
build to record exact revisions; branch references intentionally advance.

## Open integration work

1. Resolve Android 12 build/API compatibility of legacy APQ8084 audio,
   media/display, device packages, shims and vendor blobs. Reconcile hardware
   dependencies and Soong namespaces instead of removing targets blindly.
2. Reconcile SELinux/property namespaces with Android 12, preserving enforcing;
   legacy policy availability does not establish compilation compatibility.
3. Align VINTF/HIDL packages/services for audio, power, keymaster, DRM, radio
   and camera with Quark blob symbols and the target framework.
4. Audit Linux 3.10 networking/BPF, binder and toolchain requirements against
   Android 12. A property declaration does not implement a kernel feature.
5. Preserve Quark partition sizes, boot offsets and encryption. Do not copy
   Shamu fstab or remove encryption as a generic boot workaround.
6. Defer IMS/VoLTE and perfd/audio_cutback path changes until matching binaries,
   policies, modem and carrier behavior have been analyzed together.
7. Validate build, recovery/update behavior, enforcing boot and hardware.

See device/motorola/quark/docs/A12-bringup.md for the device-side checkpoint.


## SELinux consolidation through stage 35

See [SELINUX_UPDATES.md](SELINUX_UPDATES.md) for matching forks, safe migration of local patches, absolute OUT_DIR builds and validation limits.
