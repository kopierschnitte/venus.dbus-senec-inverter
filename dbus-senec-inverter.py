#!/usr/bin/env python
 
# import normal packages
import platform 
import logging
import sys
import os
import sys
if sys.version_info.major == 2:
    import gobject
else:
    from gi.repository import GLib as gobject
import sys
import time
import requests # for http GET
import configparser # for config/ini file
import struct
 
# our own packages from victron
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '/opt/victronenergy/dbus-systemcalc-py/ext/velib_python'))
from vedbus import VeDbusService


class DbusSenecInverterService:
  def __init__(self, servicename, deviceinstance, paths, productname='Senec Home Inverter', connection='Senec Home Inverter HTTP JSON service'):
    self._dbusservice = VeDbusService("{}.http_{:02d}".format(servicename, deviceinstance))
    self._paths = paths
 
    logging.debug("%s /DeviceInstance = %d" % (servicename, deviceinstance))

    # debug:
    #logging.info("Senec serial: %s" % (self._getSenecSerial()))

    # Create the management objects, as specified in the ccgx dbus-api document
    self._dbusservice.add_path('/Mgmt/ProcessName', __file__)
    self._dbusservice.add_path('/Mgmt/ProcessVersion', 'Unkown version, and running on Python ' + platform.python_version())
    self._dbusservice.add_path('/Mgmt/Connection', connection)
 
    # Create the mandatory objects
    self._dbusservice.add_path('/DeviceInstance', deviceinstance)
    #self._dbusservice.add_path('/ProductId', 16) # value used in ac_sensor_bridge.cpp of dbus-cgwacs
    #self._dbusservice.add_path('/ProductId', 0xFFFF) # id assigned by Victron Support from SDM630v2.py
    self._dbusservice.add_path('/ProductId', 126) # found on https://www.sascha-curth.de/projekte/005_Color_Control_GX.html#experiment - should be an ET340 Engerie Meter
    self._dbusservice.add_path('/DeviceType', 345) # found on https://www.sascha-curth.de/projekte/005_Color_Control_GX.html#experiment - should be an ET340 Engerie Meter
    self._dbusservice.add_path('/ProductName', productname)
    self._dbusservice.add_path('/CustomName', productname)    
    self._dbusservice.add_path('/Latency', None)    
    self._dbusservice.add_path('/FirmwareVersion', 0.1)
    self._dbusservice.add_path('/HardwareVersion', 0)
    self._dbusservice.add_path('/Connected', 1)
    #self._dbusservice.add_path('/ErrorCode', 0)
    #self._dbusservice.add_path('/MaxPower', 9000)
    #self._dbusservice.add_path('/Role', 'grid')
    #self._dbusservice.add_path('/Position', 1) # normaly only needed for pvinverter
    self._dbusservice.add_path('/Serial', self._getSenecSerial())
    self._dbusservice.add_path('/UpdateIndex', 0)
 
    # add path values to dbus
    for path, settings in self._paths.items():
      self._dbusservice.add_path(
        path, settings['initial'], gettextcallback=settings['textformat'], writeable=True, onchangecallback=self._handlechangedvalue)
 
    # last update
    self._lastUpdate = 0
 
    # add _update function 'timer'
    gobject.timeout_add(1000, self._update) # pause 1000ms before the next request
    
    # add _signOfLife 'timer' to get feedback in log every 5minutes
    gobject.timeout_add(self._getSignOfLifeInterval()*60*1000, self._signOfLife)
 
  def _getSenecSerial(self):
    meter_data = self._getSenecInverterData()  
    
    if not meter_data['FACTORY']['DEVICE_ID']:
        raise ValueError("Response does not contain 'SENEC_METER_SN' attribute")
    
    serial = meter_data['FACTORY']['DEVICE_ID']
    serial = "I" + serial[3:]
    return serial
 
 
  def _getConfig(self):
    config = configparser.ConfigParser()
    config.read("%s/config.ini" % (os.path.dirname(os.path.realpath(__file__))))
    return config;
 
 
  def _getSignOfLifeInterval(self):
    config = self._getConfig()
    value = config['DEFAULT']['SignOfLifeLog']
    
    if not value: 
        value = 0
    
    return int(value)
  
  
  def _getSenecStatusUrl(self):
    config = self._getConfig()
    accessType = config['DEFAULT']['AccessType']
    
    if accessType == 'OnPremise': 
        URL = "http://%s/lala.cgi" % (config['ONPREMISE']['Host'])
    else:
        raise ValueError("AccessType %s is not supported" % (config['DEFAULT']['AccessType']))
    
    return URL
    
 
  def _getSenecInverterData(self):
    URL = self._getSenecStatusUrl()
    #payload = "{ \"FACTORY\" : {} }"
    payload = "{\n            \"FACTORY\" : {},\n            \"PV1\" : {}\n}\n\n"

    headers = {}

    meter_r = requests.request("POST", URL, headers=headers, data=payload)
    
    # check for response
    if not meter_r:
        raise ConnectionError("No response from Senec - %s" % (URL))
    
    meter_data = meter_r.json()     
    
    # check for Json
    if not meter_data:
        raise ValueError("Converting response to JSON failed")
    

    # debug:
    #logging.info("Senec Test: %f" % (self._floatFromHex(meter_data['PM1OBJ1']['U_AC'][0])))
    #logging.info("Senec Test: %s" % (meter_data['PM1OBJ1']['U_AC'][0]))

    
    return meter_data
 
  def _floatFromHex(self, val):

    return struct.unpack('!f', bytes.fromhex(val[3:]))[0]
    #struct.unpack('!f', (val[3:]).decode('hex'))[0]
 
  def _signOfLife(self):
    logging.info("--- Start: sign of life ---")
    logging.info("Last _update() call: %s" % (self._lastUpdate))
    ##logging.info("Last '/Ac/Power': %s" % (self._dbusservice['/Ac/Power']))
    logging.info("--- End: sign of life ---")
    return True
 
  def _update(self):   
    try:
       #get data from Senec
       meter_data = self._getSenecInverterData()
       
       #send data to DBus
       self._dbusservice['/Ac/Power'] = self._floatFromHex(meter_data['PV1']['MPP_POWER'][0]) + self._floatFromHex(meter_data['PV1']['MPP_POWER'][1]) + self._floatFromHex(meter_data['PV1']['MPP_POWER'][2])
       self._dbusservice['/Ac/L1/Voltage'] = self._floatFromHex(meter_data['PV1']['MPP_VOL'][0])
       self._dbusservice['/Ac/L2/Voltage'] = self._floatFromHex(meter_data['PV1']['MPP_VOL'][1])
       self._dbusservice['/Ac/L3/Voltage'] = self._floatFromHex(meter_data['PV1']['MPP_VOL'][2])
       self._dbusservice['/Ac/L1/Current'] = self._floatFromHex(meter_data['PV1']['MPP_CUR'][0])
       self._dbusservice['/Ac/L2/Current'] = self._floatFromHex(meter_data['PV1']['MPP_CUR'][1])
       self._dbusservice['/Ac/L3/Current'] = self._floatFromHex(meter_data['PV1']['MPP_CUR'][2])
       self._dbusservice['/Ac/L1/Power'] = self._floatFromHex(meter_data['PV1']['MPP_POWER'][0])
       self._dbusservice['/Ac/L2/Power'] = self._floatFromHex(meter_data['PV1']['MPP_POWER'][1])
       self._dbusservice['/Ac/L3/Power'] = self._floatFromHex(meter_data['PV1']['MPP_POWER'][2])
       #self._dbusservice['/StatusCode'] = 7
       ##self._dbusservice['/Ac/L1/Energy/Forward'] = (meter_data['emeters'][0]['total']/1000)
       ##self._dbusservice['/Ac/L2/Energy/Forward'] = (meter_data['emeters'][1]['total']/1000)
       ##self._dbusservice['/Ac/L3/Energy/Forward'] = (meter_data['emeters'][2]['total']/1000)
       ##self._dbusservice['/Ac/L1/Energy/Reverse'] = (meter_data['emeters'][0]['total_returned']/1000) 
       ##self._dbusservice['/Ac/L2/Energy/Reverse'] = (meter_data['emeters'][1]['total_returned']/1000) 
       ##self._dbusservice['/Ac/L3/Energy/Reverse'] = (meter_data['emeters'][2]['total_returned']/1000) 
       ##self._dbusservice['/Ac/Energy/Forward'] = self._dbusservice['/Ac/L1/Energy/Forward'] + self._dbusservice['/Ac/L2/Energy/Forward'] + self._dbusservice['/Ac/L3/Energy/Forward']
       ##self._dbusservice['/Ac/Energy/Reverse'] = self._dbusservice['/Ac/L1/Energy/Reverse'] + self._dbusservice['/Ac/L2/Energy/Reverse'] + self._dbusservice['/Ac/L3/Energy/Reverse'] 
       
       #logging
       ##logging.info("House Consumption (/Ac/Power): %s" % (self._dbusservice['/Ac/Power']))
       #logging.info("L1: %s L2: %s L3: %s" % (self._dbusservice['/Ac/L1/Power'],self._dbusservice['/Ac/L2/Power'],self._dbusservice['/Ac/L3/Power']))
       ##logging.debug("House Forward (/Ac/Energy/Forward): %s" % (self._dbusservice['/Ac/Energy/Forward']))
       ##logging.debug("House Reverse (/Ac/Energy/Revers): %s" % (self._dbusservice['/Ac/Energy/Reverse']))
       ##logging.debug("---");
       
       # increment UpdateIndex - to show that new data is available
       index = self._dbusservice['/UpdateIndex'] + 1  # increment index
       if index > 255:   # maximum value of the index
         index = 0       # overflow from 255 to 0
       self._dbusservice['/UpdateIndex'] = index

       #update lastupdate vars
       self._lastUpdate = time.time()              
    except Exception as e:
       logging.critical('Error at %s', '_update', exc_info=e)
       
    # return true, otherwise add_timeout will be removed from GObject - see docs http://library.isr.ist.utl.pt/docs/pygtk2reference/gobject-functions.html#function-gobject--timeout-add
    return True
 
  def _handlechangedvalue(self, path, value):
    logging.debug("someone else updated %s to %s" % (path, value))
    return True # accept the change
 


def main():
  #configure logging
  logging.basicConfig(      format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            level=logging.INFO,
                            handlers=[
                                logging.FileHandler("%s/current.log" % (os.path.dirname(os.path.realpath(__file__)))),
                                logging.StreamHandler()
                            ])
 
  try:
      logging.info("Start");
  
      from dbus.mainloop.glib import DBusGMainLoop
      # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
      DBusGMainLoop(set_as_default=True)
     
      #formatting 
      _kwh = lambda p, v: (str(round(v, 2)) + ' KWh')
      _a = lambda p, v: (str(round(v, 1)) + ' A')
      _w = lambda p, v: (str(round(v, 1)) + ' W')
      _v = lambda p, v: (str(round(v, 1)) + ' V')   
     
      #start our main-service
      pvac_output = DbusSenecInverterService(
        servicename='com.victronenergy.pvinverter.senec',
        deviceinstance=263,
        paths={
          '/Ac/Power': {'initial': 0, 'textformat': _w},
          
          '/Ac/L1/Voltage': {'initial': 0, 'textformat': _v},
          '/Ac/L2/Voltage': {'initial': 0, 'textformat': _v},
          '/Ac/L3/Voltage': {'initial': 0, 'textformat': _v},
          '/Ac/L1/Current': {'initial': 0, 'textformat': _a},
          '/Ac/L2/Current': {'initial': 0, 'textformat': _a},
          '/Ac/L3/Current': {'initial': 0, 'textformat': _a},
          '/Ac/L1/Power': {'initial': 0, 'textformat': _w},
          '/Ac/L2/Power': {'initial': 0, 'textformat': _w},
          '/Ac/L3/Power': {'initial': 0, 'textformat': _w},
          '/StatusCode': {'initial': 7, 'textformat': ''},
          '/ErrorCode': {'initial': 0, 'textformat': ''},
	  '/MaxPower': {'initial': 0, 'textformat': _w},
          '/Position': {'initial': 1, 'textformat': ''},
        })
     
      logging.info('Connected to dbus, and switching over to gobject.MainLoop() (= event based)')
      mainloop = gobject.MainLoop()
      mainloop.run()            
  except Exception as e:
    logging.critical('Error at %s', 'main', exc_info=e)
if __name__ == "__main__":
  main()
