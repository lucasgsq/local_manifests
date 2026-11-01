# Optional Quark applications

TurboToast (com.bhb27.turbotoast) and Kernel Adiutor
(com.bhb27.kerneladiutor) are not selected for the A11+/A12+ ROM builds.
Their original APKs remain archived in the vendor repository. No kernel
changes or automatic first-boot installer are required.

Kernel Adiutor may be installed manually as a regular user app. First install
the new ROM and reboot. Installing the APK over an old system copy only
creates an update to that system app and does not make it fully uninstallable.

The APK is available after syncing the appropriate vendor branch:

```bash
vendor/motorola/quark/proprietary/vendor/app/KernelAdiutor/KernelAdiutor.apk
```

Transfer the APK to the phone and open it with the Android package installer,
or install it with adb from the build machine:

```bash
adb install -r vendor/motorola/quark/proprietary/vendor/app/KernelAdiutor/KernelAdiutor.apk
adb shell pm path com.bhb27.kerneladiutor
```

Once installed as a normal app, its active APK should be under /data/app and
Settings should offer Uninstall. If an earlier user-installed update still
retains system-app status after migration, uninstall that package before
reinstalling the APK; this removes its saved app data/settings:

```bash
adb uninstall com.bhb27.kerneladiutor
adb install vendor/motorola/quark/proprietary/vendor/app/KernelAdiutor/KernelAdiutor.apk
```

The APK and its signing certificate have not been modified. Root-dependent
features still require the app's original root access setup.
