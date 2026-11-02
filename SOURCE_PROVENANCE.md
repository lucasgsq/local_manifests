# Preserved Quark APQ8084 sources

The `A12+` manifest uses the following owned copies. These are standalone repositories with the selected full Git history, rather than build-time references to the previous maintainer's repositories.

| Project | Official LineageOS 18.1 base | Owned test branch tip |
|---|---|---|
| `lucasgsq/android_hardware_qcom_media` | `09bc40392ee7b78f385093765146758c7472b546` | `cfe448c898ee4c0cf7c98b873e789c0fd58e6675` |
| `lucasgsq/android_hardware_qcom_display` | `26a54aa24bda9626ff5b21d6023f0032296b34d5` | `2488ddb917b4fd36e25ad0fcd2bfe554e0357d42` |

The preserved patches were originally obtained from `fgl27/android_hardware_qcom_media` and `fgl27/android_hardware_qcom_display`, branch `lineage-18.1-caf-apq8084`. Those names are recorded here for attribution only; neither `quark.xml` nor the patch plan fetches from them.

The five media commits, in order:

1. `efd4fd850c712bc43b2462b2ad3d753a8e0af043` â€” libOmxVdec allow profile level up to 5.2
2. `5cd7a23f4afe611a541ce4446068112ff6c8b513` â€” media: Include display headers
3. `ebb806f4a0b611653af90ffe4821f7d737d805e3` â€” media: Add media headers lib
4. `51f6e084e952ba14cc610db76575f5a00e84f015` â€” libc2dcolorconvert: Remove dependency on stagefright
5. `cfe448c898ee4c0cf7c98b873e789c0fd58e6675` â€” media: change way of accessing aosp project headers

The display commit:

1. `2488ddb917b4fd36e25ad0fcd2bfe554e0357d42` â€” display: Add display headers lib

Both selected histories are direct continuations of their listed official bases. No additional source changes were introduced during preservation. The original hashes, authors, messages, source trees and license files are retained.

Future changes should use the owned `A12+` branches. The original endpoints above are reproducibility references, not a claim that future branch tips will remain unchanged. Build and device testing remain necessary after synchronization.
