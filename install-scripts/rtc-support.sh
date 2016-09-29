#!/bin/bash
#Add support for chinese RTC
echo "Adding support for ds3231"
echo "#add support for chinese RTC" >> /boot/config.txt
echo "dtoverlay=i2c-rtc,ds3231" >> /boot/config.txt
echo "Please reboot and use hwclock to write the current time to the rtc!"

