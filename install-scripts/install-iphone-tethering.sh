#!/bin/bash
# Make sure only root can run our script
#This script installs automatic iphone tethering
if [ "$(id -u)" != "0" ]; then
        echo "This script must be run as root" 1>&2
            exit 1
        fi

apt-get -y install gvfs ipheth-utils libimobiledevice-utils gvfs-backends gvfs-bin gvfs-fuse ifuse usbmuxd
echo "allow-hotplug eth1" >> /etc/network/interfaces
echo "iface eth1 inet dhcp" >> /etc/network/interfaces
mkdir /media/iPhone
echo "#!/bin/bash
umount /media/iPhone #when the iPhone is unplugged, it is not automatically unmounted.
ifuse /media/iPhone
ipheth_pair" > /lib/udev/iphoneconnect
chmod 755 /lib/udev/iphoneconnect
echo '
# udev rules for setting correct configuration and pairing on tethered iPhones
ATTR{idVendor}!="05ac", GOTO="ipheth_rules_end"
# Execute pairing program when appropriate
ACTION=="add", SUBSYSTEM=="net", ENV{ID_USB_DRIVER}=="ipheth", SYMLINK+="iphone", RUN+="iphoneconnect"
LABEL="ipheth_rules_end"' > /lib/udev/rules.d/90-iphone-tether.rules
echo "iPhone tethering installed, please reboot!"

