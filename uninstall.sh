#!/bin/bash

rm /service/dbus-senec-inverter
kill $(pgrep -f 'supervise dbus-senec-inverter')
chmod a-x /data/dbus-senec-inverter/service/run
./restart.sh
