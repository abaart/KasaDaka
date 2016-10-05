#!/bin/bash
# This script configures the Raspberry Pi to host a wifi-hotspot, for easy ssh access.
# Make sure only root can run our script
if [ "$(id -u)" != "0" ]; then
        echo "This script must be run as root" 1>&2
            exit 1
        fi

apt-get install hostapd dnsmasq
rm /etc/dhcpcd.conf
cp ../etc/dhcpcd.conf /etc/dhcpcd.conf
rm /etc/network/interfaces
cp ../etc/network/interfaces /etc/network/interfaces
/etc/init.d/dhcpcd restart
ifdown wlan0
ifup wlan0
rm /etc/hostapd/hostapd.conf
cp ../etc/hostapd/hostapd.conf /etc/hostapd/hostapd.conf       
rm /etc/default/hostapd
cp ../etc/default/hostapd /etc/default/hostapd
mv /etc/dnsmasq.conf /etc/dnsmasq.conf.orig
cp ../etc/dnsmasq.conf /etc/dnsmasq.conf
/etc/init.d/hostapd restart
/etc/init.d/dnsmasq restart



