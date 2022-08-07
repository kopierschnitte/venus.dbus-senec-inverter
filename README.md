# dbus-senec-inverter
Integrate the internal inverter readings of a Senec Home storage system into [Victron Energies Venus OS](https://github.com/victronenergy/venus)

It can be used in concert with my other script [venus.dbus-senec-enfluri](https://github.com/kopierschnitte/venus.dbus-senec-enfluri) to fully integrate a Senec Home system into Victron's ecosystem.

## Purpose
With the scripts in this repo it should be easy possible to install, uninstall, restart a service that reads the current values of Senec Home's internal inverters and publishes them to the VenusOS and GX devices from Victron.
Idea is pasend on @RalfZim project linked below.

## Inspiration
This project is my first on GitHub and with the Victron Venus OS, so I took some ideas and approaches from the following projects - many thanks for sharing the knowledge:
- https://github.com/RalfZim/venus.dbus-fronius-smartmeter
- https://github.com/victronenergy/dbus-smappee
- https://github.com/Louisvdw/dbus-serialbattery
- https://community.victronenergy.com/questions/85564/eastron-sdm630-modbus-energy-meter-community-editi.html

## How it works
### My setup
- Senec Home v3 Duo Hybrid storage system
  - ABB EnFluRi meter, connected to the Senec system using Modbus/RS485
  - 3-Phase installation (normal for Germany)
  - IP 192.168.37.123/24  

### Details / Process
As mentioned above the script is inspired by @RalfZim fronius smartmeter implementation.
So what is the script doing:
- Running as a service
- connecting to DBus of the Venus OS `com.victronenergy.pvinverters.http_40`
- After successful DBus connection, EnFluRi's readings are accessed via an unsupported/undocumented API of the Senec system (lala.cgi)
- Serial is taken from the response as device serial
- Paths are added to the DBus with default value 0 - including some settings like name, etc
- After that a "loop" is started which polls Senec/EnFluRi data every 1000ms from the REST-API and updates the values in the DBus

Thats it 😄

## Install & Configuration
### Get the code
Just grap a copy of the main branch and copy them to `/data/dbus-senec-inverter`.
Edit the config.ini file and fill in the IP of your Senec Home
After that call the install.sh script.

## Used documentation
- https://github.com/victronenergy/venus/wiki/dbus#grid   DBus paths for Victron namespace
- https://github.com/victronenergy/venus/wiki/dbus-api   DBus API from Victron
- https://www.victronenergy.com/live/ccgx:root_access   How to get root access on GX device/Venus OS
