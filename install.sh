#!/bin/bash

# set permissions for script files
chmod a+x /data/dbus-senec-inverter/restart.sh
chmod 744 /data/dbus-senec-inverter/restart.sh

chmod a+x /data/dbus-senec-inverter/uninstall.sh
chmod 744 /data/dbus-senec-inverter/uninstall.sh

chmod a+x /data/dbus-senec-inverter/service/run
chmod 755 /data/dbus-senec-inverter/service/run



# create sym-link to run script in deamon
ln -s /data/dbus-senec-inverter/service /service/dbus-senec-inverter



# add install-script to rc.local to be ready for firmware update
filename=/data/rc.local
if [ ! -f $filename ]
then
    touch $filename
    chmod 755 $filename
    echo "#!/bin/bash" >> $filename
    echo >> $filename
fi

grep -qxF '/data/dbus-senec-inverter/install.sh' $filename || echo '/data/dbus-senec-inverter/install.sh' >> $filename
