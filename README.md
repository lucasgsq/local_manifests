## LineageOS 18.1 local_manifests for Moto Maxx (Quark)

This is the current Moto Maxx (Quark) manifest for LineageOS 18.1 (Android 11). 
These repos are only validated to build lineage ROMs. Any other custom ROM is unsupported.
Steps to build

    Clone Lineage 18.1 repo and setup your build environment according to the Lineage documentation
    Clone patches (lineage-18.1 branch) and follow the instructions to apply them. THIS IS REQUIRED FOR WORKING BUILDS AND IS MANDATORY
    Copy quark.xml to {ANDROID_ROOT}/.repo/local_manifests/roomservice.xml - create the folder if it doesnt exist
    Return to {ANDROID_ROOT} and repo sync
    source build/envsetup.sh
    lunch lineage_quark-[buildflag]
    make bacon -j[cpucorecount]

Replace buildflag with the type of ROM you are trying to build. Valid codenames:

    user: for user builds
    userdebug: for user-debug builds


Replace core count with the number of CPU cores you have.
