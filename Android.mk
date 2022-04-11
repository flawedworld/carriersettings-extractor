# Use standalone carrier extraction on supported Pixels only
ifneq (,$(filter sunfish coral flame redfin bramble barbet oriole raven, $(TARGET_PRODUCT)))
    
TARGET_GENERATED_APN_XML := $(TARGET_OUT_INTERMEDIATES)/CARRIER_XML/$(TARGET_DEVICE)/apns-conf.xml
TARGET_GENERATED_CC_XML := $(TARGET_OUT_INTERMEDIATES)/CARRIER_XML/$(TARGET_DEVICE)/carrierconfig-vendor.xml

$(shell python $(LOCAL_PATH)/carriersettings_extractor.py vendor/google_devices/$(TARGET_DEVICE)/proprietary/product/etc/CarrierSettings/ $(ANDROID_BUILD_TOP) $(TARGET_GENERATED_APN_XML) $(TARGET_GENERATED_CC_XML))

PRODUCT_COPY_FILES += \
    $(TARGET_OUT_INTERMEDIATES)/CARRIER_XML/$(TARGET_DEVICE)/apns-conf.xml:$(TARGET_COPY_OUT_PRODUCT)/etc/apns-conf.xml \
    $(TARGET_OUT_INTERMEDIATES)/CARRIER_XML/$(TARGET_DEVICE)/carrierconfig-vendor.xml:$(TARGET_COPY_OUT_PRODUCT)/etc/carrierconfig-vendor.xmll \

endif
