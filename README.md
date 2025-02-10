## LineageOS 18.1 local_manifests for Moto Maxx (Quark)

This is the current Moto Maxx (Quark) manifest for LineageOS 18.1 (Android 11). 
These repos are only validated to build LineageOS ROMs. Any other custom ROM is unsupported.

Steps to build

    Clone Lineage 18.1 repo and setup your build environment according to the Lineage documentation
    (you can use the Shamu's (Nexus 6) build guide as a reference guide, but remember we're building for Quark!)
    https://wiki.lineageos.org/devices/shamu/build/
    
Apply patches (in some point I will try to make a patches.sh, but for now:
    
    cd hardware/qcom-caf/apq8084/media/
    git fetch https://github.com/fgl27/android_hardware_qcom_media lineage-18.1-caf-apq8084 && git cherry-pick efd4fd850c712bc43b2462b2ad3d753a8e0af043^..cfe448c898ee4c0cf7c98b873e789c0fd58e6675
    cd -
    
    cd hardware/qcom-caf/apq8084/display/
    git fetch https://github.com/fgl27/android_hardware_qcom_display lineage-18.1-caf-apq8084 && git cherry-pick 2488ddb917b4fd36e25ad0fcd2bfe554e0357d42
    cd -

Copy quark.xml to {ANDROID_ROOT}/.repo/local_manifests/roomservice.xml - create the folder if it doesnt exist:

    mkdir .repo/local_manifests
    wget -O .repo/local_manifests/quark.xml 'https://raw.githubusercontent.com/lucasgsq/local_manifests/quark-(Moto-Maxx)/quark.xml'


Return to {ANDROID_ROOT} and repo sync
    
    source build/envsetup.sh
    
    lunch lineage_quark-[buildflag]
    
    make bacon -j[cpucorecount]

Replace buildflag with the type of ROM you are trying to build. Valid codenames:

    user: for user builds
    userdebug: for user-debug builds


Replace core count with the number of CPU cores you have.
