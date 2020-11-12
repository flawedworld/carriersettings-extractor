#!/bin/bash
a=(
	"ci_action_on_sys_update"
	"config_ims_package_override_string"
	"com.google.android"
	"com.google.android"
	"sprintdm"
	"sprinthm"
)
for i in ${a[@]}; do
	sed -i "/$i/d" ./vendor.xml
done
