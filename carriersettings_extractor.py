#!/usr/bin/env python3

from collections import OrderedDict
from glob import glob
from itertools import product
import os.path
import sys
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape, quoteattr

from carriersettings_pb2 import CarrierList, CarrierSettings, \
    MultiCarrierSettings
from vendor.carrierId_pb2 import CarrierList as CarrierIdList

pb_path = sys.argv[1]

android_build_top = sys.argv[2]

apn_out = sys.argv[3]

cc_out = sys.argv[4]

android_path_to_carrierid = "packages/providers/TelephonyProvider/assets/latest_carrier_id"
carrier_id_list = CarrierIdList()
carrier_attribute_map = {}
with open(os.path.join(android_build_top, android_path_to_carrierid, 'carrier_list.pb'), 'rb') as pb:
    carrier_id_list.ParseFromString(pb.read())
for carrier_id_obj in carrier_id_list.carrier_id:
    for carrier_attribute in carrier_id_obj.carrier_attribute:
        for carrier_attributes in product(*(
            (s.lower() for s in getattr(carrier_attribute, i) or [''])
            for i in [
                'mccmnc_tuple', 'imsi_prefix_xpattern', 'spn', 'plmn',
                'gid1', 'gid2', 'preferred_apn', 'iccid_prefix',
                'privilege_access_rule',
            ]
        )):
            carrier_attribute_map[carrier_attributes] = \
                carrier_id_obj.canonical_id

carrier_list = CarrierList()
all_settings = {}
for filename in glob(os.path.join(pb_path, '*.pb')):
    with open(filename, 'rb') as pb:
        if os.path.basename(filename) == 'carrier_list.pb':
            carrier_list.ParseFromString(pb.read())
        elif os.path.basename(filename) == 'others.pb':
            settings = MultiCarrierSettings()
            settings.ParseFromString(pb.read())
            for setting in settings.setting:
                if setting.canonicalName == 'telenor_se':
                    continue
                assert setting.canonicalName not in all_settings
                all_settings[setting.canonicalName] = setting
        else:
            setting = CarrierSettings()
            setting.ParseFromString(pb.read())
            assert setting.canonicalName not in all_settings
            all_settings[setting.canonicalName] = setting


# Unfortunately, python processors like xml and lxml, as well as command-line
# utilities like tidy, do not support the exact style used by AOSP for
# apns-full-conf.xml:
#
#  * indent: 2 spaces
#  * attribute indent: 4 spaces
#  * blank lines between elements
#  * attributes after first indented on separate lines
#  * closing tags of multi-line elements on separate, unindented lines
#
# Therefore, we build the file without using an XML processor.


class ApnElement:
    def __init__(self, apn, carrier_id):
        self.apn = apn
        self.carrier_id = carrier_id
        self.attributes = OrderedDict()
        self.add_attributes()

    def add_attribute(self, key, field=None, value=None):
        if value is not None:
            self.attributes[key] = value
        else:
            if field is None:
                field = key
            if self.apn.HasField(field):
                enum_type = self.apn.DESCRIPTOR.fields_by_name[field].enum_type
                value = getattr(self.apn, field)
                if enum_type is None:
                    if isinstance(value, bool):
                        self.attributes[key] = str(value).lower()
                    else:
                        self.attributes[key] = str(value)
                else:
                    self.attributes[key] = \
                        enum_type.values_by_number[value].name

    def add_attributes(self):
        try:
            self.add_attribute(
                'carrier_id',
                value=str(carrier_attribute_map[(
                    self.carrier_id.mccMnc,
                    self.carrier_id.imsi,
                    self.carrier_id.spn.lower(),
                    '',
                    self.carrier_id.gid1.lower(),
                    self.carrier_id.gid2.lower(),
                    '',
                    '',
                    '',
                )])
            )
        except KeyError:
            pass
        self.add_attribute('mcc', value=self.carrier_id.mccMnc[:3])
        self.add_attribute('mnc', value=self.carrier_id.mccMnc[3:])
        self.add_attribute('apn', 'value')
        self.add_attribute('proxy')
        self.add_attribute('port')
        self.add_attribute('mmsc')
        self.add_attribute('mmsproxy', 'mmscProxy')
        self.add_attribute('mmsport', 'mmscProxyPort')
        self.add_attribute('user')
        self.add_attribute('password')
        self.add_attribute('server')
        self.add_attribute('authtype')
        self.add_attribute(
            'type',
            value=','.join(
                apn.DESCRIPTOR.fields_by_name[
                    'type'
                ].enum_type.values_by_number[i].name
                for i in self.apn.type
            ).lower(),
        )
        self.add_attribute('protocol')
        self.add_attribute('roaming_protocol', 'roamingProtocol')
        self.add_attribute('carrier_enabled', 'carrierEnabled')
        self.add_attribute('bearer_bitmask', 'bearerBitmask')
        self.add_attribute('profile_id', 'profileId')
        self.add_attribute('modem_cognitive', 'modemCognitive')
        self.add_attribute('max_conns', 'maxConns')
        self.add_attribute('wait_time', 'waitTime')
        self.add_attribute('max_conns_time', 'maxConnsTime')
        self.add_attribute('mtu')
        mvno = self.carrier_id.WhichOneof('mvno')
        if mvno:
            self.add_attribute(
                'mvno_type',
                value='gid' if mvno.startswith('gid') else mvno,
            )
            self.add_attribute(
                'mvno_match_data',
                value=getattr(self.carrier_id, mvno),
            )
        self.add_attribute('apn_set_id', 'apnSetId')
        # No source for integer carrier_id?
        self.add_attribute('skip_464xlat', 'skip464Xlat')
        self.add_attribute('user_visible', 'userVisible')
        self.add_attribute('user_editable', 'userEditable')


def indent(elem, level=0):
    """Based on https://effbot.org/zone/element-lib.htm#prettyprint"""
    i = "\n" + level * "    "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "    "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

# Anything where the value is a package name
unwanted_configs = ["carrier_app_wake_signal_config",
                    "carrier_settings_activity_component_name_string",
                    "carrier_setup_app_string",
                    "config_ims_package_override_string",
                    "enable_apps_string_array",
                    "gps.nfw_proxy_apps",
                    "smart_forwarding_config_component_name_string",
                    "wfc_emergency_address_carrier_app_string",
                    "ci_action_on_sys_update_bool",
                    "ci_action_on_sys_update_extra_string",
                    "ci_action_on_sys_update_extra_val_string",
                    "ci_action_on_sys_update_intent_string",
                    "allow_adding_apns_bool",
                    "apn_expand_bool",
                    "hide_ims_apn_bool",
                    "hide_preset_apn_details_bool",
                    "read_only_apn_fields_string_array",
                    "read_only_apn_types_string_array",
                    "show_apn_setting_cdma_bool",
                    "carrier_provisioning_app_string",
                    "hide_enable_2g_bool",
                    "com.google.android.dialer.display_wifi_calling_button_bool"]

## TODO:
# "carrier_app_wake_signal_config" is still valid on GrapheneOS but we need to implement code for removing "com.google.android.carriersetup" we don't ship it
# "smart_forwarding_config_component_name_string" is still valid on Qualcomm Pixel devices but we don't currently ship xdivert
# "wfc_emergency_address_carrier_app_string" is still valid on GrapheneOS but we need to replace the string to be "com.android.imsserviceentitlement/.WfcActivationActivity"

carrier_config_root = ET.Element('carrier_config_list')

with open(apn_out, 'w', encoding='utf-8') as f:
    f.write('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n\n')
    f.write('<apns version="8">\n\n')

    version_suffix = all_settings['default'].version % 1000000000
    for entry in carrier_list.entry:
        setting = all_settings[entry.canonicalName]
        for apn in setting.apns.apn:
            f.write('  <apn carrier={}\n'.format(quoteattr(apn.name)))
            apn_element = ApnElement(apn, entry.carrierId)
            for (key, value) in apn_element.attributes.items():
                f.write('      {}={}\n'.format(escape(key), quoteattr(value)))
            f.write('  />\n\n')

        carrier_config_element = ET.SubElement(
            carrier_config_root,
            'carrier_config',
        )
        carrier_config_element.set('mcc', entry.carrierId.mccMnc[:3])
        carrier_config_element.set('mnc', entry.carrierId.mccMnc[3:])
        for field in ['spn', 'imsi', 'gid1', 'gid2']:
            if entry.carrierId.HasField(field):
                carrier_config_element.set(
                    field,
                    getattr(entry.carrierId, field),
                )

        # Add version key composed of canonical name and versions
        carrier_config_subelement = ET.SubElement(
            carrier_config_element,
            'string'
        )
        carrier_config_subelement.set('name', 'carrier_config_version_string')
        carrier_config_subelement.text = '{}-{}.{}'.format(
            setting.canonicalName,
            setting.version,
            version_suffix
        )

        for config in setting.configs.config:
            if config.key in unwanted_configs:
                continue
            value_type = config.WhichOneof('value')
            if value_type == 'textValue':
                carrier_config_subelement = ET.SubElement(
                    carrier_config_element,
                    'string',
                )
                carrier_config_subelement.set('name', config.key)
                carrier_config_subelement.text = getattr(config, value_type)
            elif value_type == 'intValue':
                carrier_config_subelement = ET.SubElement(
                    carrier_config_element,
                    'int',
                )
                carrier_config_subelement.set('name', config.key)
                carrier_config_subelement.set(
                    'value',
                    str(getattr(config, value_type)),
                )
            elif value_type == 'longValue':
                carrier_config_subelement = ET.SubElement(
                    carrier_config_element,
                    'long',
                )
                carrier_config_subelement.set('name', config.key)
                carrier_config_subelement.set(
                    'value',
                    str(getattr(config, value_type)),
                )
            elif value_type == 'boolValue':
                carrier_config_subelement = ET.SubElement(
                    carrier_config_element,
                    'boolean',
                )
                carrier_config_subelement.set('name', config.key)
                carrier_config_subelement.set(
                    'value',
                    str(getattr(config, value_type)).lower(),
                )
            elif value_type == 'textArray':
                carrier_config_subelement = ET.SubElement(
                    carrier_config_element,
                    'string-array',
                )
                carrier_config_subelement.set('name', config.key)
                carrier_config_subelement.set(
                    'num',
                    str(len(getattr(config, value_type).item)),
                )
                for value in getattr(config, value_type).item:
                    carrier_config_item = ET.SubElement(
                        carrier_config_subelement,
                        'item',
                    )
                    carrier_config_item.set('value', value)
            elif value_type == 'intArray':
                carrier_config_subelement = ET.SubElement(
                    carrier_config_element,
                    'int-array',
                )
                carrier_config_subelement.set('name', config.key)
                carrier_config_subelement.set(
                    'num',
                    str(len(getattr(config, value_type).item)),
                )
                for value in getattr(config, value_type).item:
                    carrier_config_item = ET.SubElement(
                        carrier_config_subelement,
                        'item',
                    )
                    carrier_config_item.set('value', str(value))
            else:
                raise TypeError("Unknown value type: {}".format(value_type))

    f.write('</apns>\n')

indent(carrier_config_root)
carrier_config_tree = ET.ElementTree(carrier_config_root)
root_carrier_config_tree = carrier_config_tree.getroot()

# dict containing lookups for each mccmnc combo representing each file,
# which contains a list of all configs which are dicts
carrier_config_mccmnc_aggregated = {}

for lone_carrier_config in root_carrier_config_tree:
    # append mnc to mcc to form identifier used to lookup carrier XML in CarrierConfig app
    if ("gid1" not in lone_carrier_config.attrib) and ("gid2" not in lone_carrier_config.attrib) and ("spn" not in lone_carrier_config.attrib) and ("imsi" not in lone_carrier_config.attrib):
        front = True
    else:
        front = False

    mccmnc_combo = "carrier_config_mccmnc_" + lone_carrier_config.attrib["mcc"] + lone_carrier_config.attrib["mnc"] + ".xml"

    # handle multiple carrier configurations under the same mcc and mnc combination
    if mccmnc_combo not in carrier_config_mccmnc_aggregated:
        blank_list = []
        carrier_config_mccmnc_aggregated[mccmnc_combo] = blank_list
    temp_list = carrier_config_mccmnc_aggregated[mccmnc_combo]
    if front == True:
        temp_list.insert(0,lone_carrier_config)
    else:
        temp_list.append(lone_carrier_config)
    carrier_config_mccmnc_aggregated[mccmnc_combo] = temp_list


with open(cc_out, 'w', encoding='utf-8') as f:
    f.write('<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n')
    f.write('<carrier_config_list>\n')
    for configfile in carrier_config_mccmnc_aggregated:
        config_list = carrier_config_mccmnc_aggregated[configfile]
        for config in config_list:
            config_tree =  ET.ElementTree(config)
            config_tree = config_tree.getroot()
            indent(config_tree)
            single_carrier_config = ET.tostring(config_tree, encoding='unicode')
            single_carrier_config = str(single_carrier_config)
            f.write(single_carrier_config)
    f.write('</carrier_config_list>\n')
    f.close()
