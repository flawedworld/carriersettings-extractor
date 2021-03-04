# carriersettings-extractor for GrapheneOs

Android Open Source Project (AOSP) [includes](https://source.android.com/devices/tech/config/update) APN settings ([`apns-full-conf.xml`](https://android.googlesource.com/device/sample/+/master/etc/apns-full-conf.xml)) and [carrier settings](https://source.android.com/devices/tech/config/carrier) ([`carrier_config_*.xml`](https://android.googlesource.com/platform/packages/apps/CarrierConfig/+/master/assets) + [`vendor.xml`](https://android.googlesource.com/platform/packages/apps/CarrierConfig/+/refs/heads/master/res/xml/vendor.xml)) in human-readable XML format. However, Google Pixel device images instead include APN and carrier settings as binary protobuf files for use by the CarrierSettings system app.

This script converts the CarrierSettings protobuf files (e.g., `carrier_list.pb`, `others.pb`) to XML format compatible with AOSP. This may be helpful for Android-based systems that do not bundle CarrierSettings, but wish to support carriers that are not included in AOSP.

Systems like GrapheneOS that do not ship proprietary google services and some other invasive apps need some cleanup for the carrierconfig vendor overlay. See generate-aosp-overlays.sh to see how these are generated

For a description of each APN and carrier setting, refer to the doc comments in [`Telephony.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/master/core/java/android/provider/Telephony.java) and [`CarrierConfigManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/master/telephony/java/android/telephony/CarrierConfigManager.java), respectively.

## Dependencies

 * curl - required, for android-prepare-vendor
 * e2fsprogs (debugfs) - required, for android-prepare-vendor
 * git - required, for android-prepare-vendor
 * protobuf-compiler (protoc) - optional, see below
 * python3-protobuf - required

## Usage

Download the [carrier ID database](https://source.android.com/devices/tech/config/carrierid) from AOSP.

    ./download_carrier_list.sh

To download a Pixel factory image and extract the CarrierSettings protobuf files, use this script to download android-prepare-vendor and copy the directory `CarrierSettings` containing the protobuf files.

    DEVICE=crosshatch BUILD=QQ3A.200605.001 ./download_factory_img.sh
    
You can get the build IDs from [here](https://developers.google.com/android/images)

Convert `CarrierSettings/*.pb` to `apns-full-conf.xml` and `vendor.xml` (see below for cleaning this output).

    ./carriersettings_extractor.py CarrierSettings
    
Copy apns-full-conf.xml to the device tree (device/google/$DEVICE)

To clean up the vendor overlays run this command

    bash generate-aosp-overlays.sh
    
This command assumes that the other steps were followed exactly as they were written here. The cleanup script will fail unless the factory image and carrierlist are already downloaded

Copy vendor.xml to the device tree overlays dir, example device/google/$DEVICE/overlay/packages/apps/CarrierConfig/res/xml/vendor.xml

In some cases that path may not be the right one, use device/google/\<device-family-common-name\>/$DEVICE/overlay/packages/apps/CarrierConfig/res/xml/vendor.xml and an example is [here](https://github.com/GrapheneOS/device_google_redfin/commit/c82eb636cd063066199b920dca0a328c915adfa3)

## Protobuf definitions

The definitions in [`carriersettings.proto`](carriersettings.proto) are useful for inspecting the CarrierSettings protobuf files.

    protoc --decode=CarrierList carriersettings.proto < CarrierSettings/carrier_list.pb
    protoc --decode=CarrierSettings carriersettings.proto < CarrierSettings/verizon_us.pb
    protoc --decode=MultiCarrierSettings carriersettings.proto < CarrierSettings/others.pb

To check schema or otherwise inspect the protobuf files without applying definitions, use the `--decode_raw` argument.

    protoc --decode_raw < CarrierSettings/carrier_list.pb
    protoc --decode_raw < CarrierSettings/verizon_us.pb
    protoc --decode_raw < CarrierSettings/others.pb
