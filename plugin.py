"""
<plugin key="Quatt" name="Quatt" author="Mark Heinis" version="0.0.8" wikilink="http://www.domoticz.com/wiki/plugins/plugin.html" externallink="https://github.com/galadril/Domoticz-Quatt-Plugin">
    <description>
        Plugin for retrieving and updating Quatt data.
        More info about Quatt: https://www.quatt.io/
    </description>
    <params>
        <param field="Address" label="IP Address" width="200px" required="true" default="127.0.0.1"/>
        <param field="Port" label="Port" width="30px" required="true" default="8080"/>
        <param field="Mode6" label="Debug" width="150px">
            <options>
                <option label="None" value="0"  default="true" />
                <option label="Python Only" value="2"/>
                <option label="Basic Debugging" value="62"/>
                <option label="Basic+Messages" value="126"/>
                <option label="Connections Only" value="16"/>
                <option label="Connections+Queue" value="144"/>
                <option label="All" value="-1"/>
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz
import json

class QuattPlugin:
    httpConn = None
    sendAfterConnect = {'Verb': 'GET', 'URL': '/beta/feed/data.json'}
    
    def __init__(self):
        self.update_interval = 3
        self.debug_level = None
        self.devices_created = False
        self.system_config = {
            'has_hp1': False,
            'has_hp2': False,
            'has_boiler': False,
            'has_thermostat': False,
            'has_flow_meter': False
        }

    def onStart(self):
        if Parameters["Mode6"] == "":
            Parameters["Mode6"] = "-1"
        if Parameters["Mode6"] != "0": 
            Domoticz.Debugging(int(Parameters["Mode6"]))
            DumpConfigToLog()
            
        self.debug_level = Parameters["Mode6"]
        
        # Don't create devices immediately - wait for first data response
        # createDevices(self, self.system_config)
            
        self.httpConn = Domoticz.Connection(Name="Quatt", Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=Parameters["Port"])
        self.httpConn.Connect()
        
        Domoticz.Heartbeat(30)
        
    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug("onConnect called: " + str(Status) + " | " + Connection.Address + ":" + Connection.Port)
        if Status == 0:
            Domoticz.Debug("Connected successfully to: " + Connection.Address + ":" + Connection.Port)
            self.httpConn.Send(self.sendAfterConnect)
        else:
            Domoticz.Log("Failed to connect (" + str(Status) + ") to: " + Connection.Address + ":" + Connection.Port)
            Domoticz.Debug("Failed to connect (" + str(Status) + ") to: " + Connection.Address + ":" + Connection.Port + " with error: " + Description)
        return True

    def onStop(self):
        Domoticz.Debug("Quatt Plugin stopped")

    def onHeartbeat(self):
        if (self.httpConn.Connecting()):
            Domoticz.Error("onHeartBeat connecting")
        else:
            if (self.httpConn.Connected()):
                Domoticz.Error("onHeartBeat connected")
                self.httpConn.Disconnect()
                self.httpConn=None
                self.httpConn = Domoticz.Connection(Name="Quatt", Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=Parameters["Port"])
            else:
                Domoticz.Log("onHeartBeat unconnected")
            self.httpConn.Connect()

    def onMessage(self, Connection, Data):
        Domoticz.Debug("onMessage called with data: " + str(Data))
        try:
            Response = json.loads(Data["Data"])
            processResponse(self, Response) 
        except Exception as e:
            Domoticz.Error("Error parsing Quatt json: {}".format(str(e)))

    def onDisconnect(self, Connection):
        Domoticz.Debug("onDisconnect called for connection to: " + Connection.Address + ":" + Connection.Port)
        
global _plugin
_plugin = QuattPlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return
 
def createDevices(self, system_config):
    device_definitions = []
    
    # Always create basic system devices
    device_definitions.extend([
        (1, "Status", "Text", 7),
        (14, "Flow Rate Filtered", "Custom", 11),
        (24, "Sticky Pump Protection Enabled", "Switch")
    ])
    
    # Create thermostat devices if thermostat data is available
    if system_config.get('has_thermostat', False):
        device_definitions.extend([
            (2, "Room Temperature", "Temperature"),
            (3, "Set Room Temperature", "Temperature"),
            (10, "Request Room Temperature", "Temperature"),
            (19, "CH Enabled", "Switch"),
            (20, "Cooling Enabled", "Switch"),
            (21, "DHW Enabled", "Switch")
        ])
    
    # Create boiler devices if boiler data is available
    if system_config.get('has_boiler', False):
        device_definitions.extend([
            (6, "Supply Outlet Temperature", "Temperature"),
            (7, "Supply Inlet Temperature", "Temperature"),
            (15, "Boiler On/Off", "Switch"),
            (16, "CH Mode Active", "Switch"),
            (17, "DHW Active", "Switch"),
            (18, "Flame On", "Switch")
        ])
    
    # Create HP1 devices if HP1 data is available
    if system_config.get('has_hp1', False):
        device_definitions.extend([
            (4, "HP1 Water Inlet Temperature", "Temperature"),
            (5, "HP1 Water Outlet Temperature", "Temperature"),
            (9, "HP1 Outside Temperature", "Temperature"),
            (11, "HP1 Power Heat", "Usage", 10),
            (12, "HP1 Power Electric", "Usage"),
            (13, "HP1 COP", "Custom", {"ValueQuantity": "Custom", "ValueUnits": "COP"}),
            (22, "HP1 Limited by COP", "Switch"),
            (23, "HP1 Silent Mode Status", "Switch")
        ])
    
    # Create HP2 devices if HP2 data is available
    if system_config.get('has_hp2', False):
        device_definitions.extend([
            (26, "HP2 Water Inlet Temperature", "Temperature"),
            (27, "HP2 Water Outlet Temperature", "Temperature"),
            (28, "HP2 Outside Temperature", "Temperature"),
            (29, "HP2 Power Heat", "Usage", 10),
            (30, "HP2 Power Electric", "Usage"),
            (31, "HP2 COP", "Custom", {"ValueQuantity": "Custom", "ValueUnits": "COP"}),
            (32, "HP2 Limited by COP", "Switch"),
            (33, "HP2 Silent Mode Status", "Switch")
        ])
    
    # Create flow meter devices if flow meter data is available
    if system_config.get('has_flow_meter', False):
        device_definitions.extend([
            (25, "Water Supply Temperature", "Temperature")
        ])
    
    # Create the devices
    for unit, name, type_name, *options in device_definitions:
        if unit not in Devices:
            Domoticz.Device(Name=name, Unit=unit, TypeName=type_name, Options=options[0] if options else {}, Image=options[1] if len(options) > 1 else 0).Create()
            Domoticz.Debug("Created device: {} (Unit: {})".format(name, unit))

def processResponse(self, data):
    Domoticz.Log("processResponse called: " + str(data))
    try:
        # First time processing - detect available components and create devices
        if not self.devices_created:
            self.system_config['has_hp1'] = 'hp1' in data and data['hp1'] is not None
            self.system_config['has_hp2'] = 'hp2' in data and data['hp2'] is not None
            self.system_config['has_boiler'] = 'boiler' in data and data['boiler'] is not None
            self.system_config['has_thermostat'] = 'thermostat' in data and data['thermostat'] is not None
            self.system_config['has_flow_meter'] = 'flowMeter' in data and data['flowMeter'] is not None
            
            Domoticz.Log("Detected system components: {}".format(self.system_config))
            createDevices(self, self.system_config)
            self.devices_created = True
        
        QuattCM = data["qc"]["supervisoryControlMode"]
        Quatt_Status = {
             0: 'Standby',
             1: 'Standby - heating',
             2: 'Heating - heatpump only',
             3: 'Heating - heatpump + boiler',
             4: 'Heating - boiler only',
            95: 'Sticky Pump Protection',
            96: 'Anti-Freeze protection - boiler only',
            97: 'Anti-Freeze protection - boiler pre-pump',
            98: 'Anti-Freeze protection - water circulation',
            99: 'Fault - circulation pump on',
        }.get(QuattCM, 'Unknown')
        Domoticz.Status(Quatt_Status)
        
        # Always update basic system devices
        updateDevice(self, 1, Quatt_Status, 1)
        updateDevice(self, 14, round(data["qc"]["flowRateFiltered"], 1), 1)
        updateDevice(self, 24, '', int(data["qc"]["stickyPumpProtectionEnabled"]))
        
        # Update thermostat devices if available
        if self.system_config['has_thermostat']:
            updateDevice(self, 2, round(data["thermostat"]["otFtRoomTemperature"], 2), 1)
            updateDevice(self, 3, round(data["thermostat"]["otFtRoomSetpoint"], 1), 1)
            updateDevice(self, 10, round(data["thermostat"]["otFtControlSetpoint"], 2), 1)
            updateDevice(self, 19, '', int(data["thermostat"]["otFtChEnabled"]))
            updateDevice(self, 20, '', int(data["thermostat"]["otFtCoolingEnabled"]))
            updateDevice(self, 21, '', int(data["thermostat"]["otFtDhwEnabled"]))
        
        # Update boiler devices if available
        if self.system_config['has_boiler']:
            if (data["boiler"]["otFbSupplyOutletTemperature"] is not None):
                updateDevice(self, 6, round(data["boiler"]["otFbSupplyOutletTemperature"], 2), 1)
            if (data["boiler"]["otFbSupplyInletTemperature"] is not None):
                updateDevice(self, 7, round(data["boiler"]["otFbSupplyInletTemperature"], 2), 1)
            if (data["boiler"]["oTtbTurnOnOffBoilerOn"] is not None):
                updateDevice(self, 15, '', int(data["boiler"]["oTtbTurnOnOffBoilerOn"]))
            if (data["boiler"]["otFbChModeActive"] is not None):
                updateDevice(self, 16, '', int(data["boiler"]["otFbChModeActive"]))
            if (data["boiler"]["otFbDhwActive"] is not None):
                updateDevice(self, 17, '', int(data["boiler"]["otFbDhwActive"]))
            if (data["boiler"]["otFbFlameOn"] is not None):
                updateDevice(self, 18, '', int(data["boiler"]["otFbFlameOn"]))
        
        # Update HP1 devices if available
        if self.system_config['has_hp1']:
            # Calculate COP for HP1
            COP_HP1 = 0
            if (data["hp1"]["powerInput"] > 0):
                COP_HP1 = data["hp1"]["power"] / data["hp1"]["powerInput"]
                
            updateDevice(self, 4, round(data["hp1"]["temperatureWaterIn"], 2), 1)
            updateDevice(self, 5, round(data["hp1"]["temperatureWaterOut"], 2), 1)
            updateDevice(self, 9, round(data["hp1"]["temperatureOutside"], 1), 1)
            updateDevice(self, 11, round(data["hp1"]["power"], 2), 1)
            updateDevice(self, 12, round(data["hp1"]["powerInput"], 2), 1)
            updateDevice(self, 13, round(COP_HP1, 2), 1)
            updateDevice(self, 22, '', int(data["hp1"]["limitedByCop"]))
            updateDevice(self, 23, '', int(data["hp1"]["silentModeStatus"]))
        
        # Update HP2 devices if available
        if self.system_config['has_hp2']:
            # Calculate COP for HP2
            COP_HP2 = 0
            if (data["hp2"]["powerInput"] > 0):
                COP_HP2 = data["hp2"]["power"] / data["hp2"]["powerInput"]
                
            updateDevice(self, 26, round(data["hp2"]["temperatureWaterIn"], 2), 1)
            updateDevice(self, 27, round(data["hp2"]["temperatureWaterOut"], 2), 1)
            updateDevice(self, 28, round(data["hp2"]["temperatureOutside"], 1), 1)
            updateDevice(self, 29, round(data["hp2"]["power"], 2), 1)
            updateDevice(self, 30, round(data["hp2"]["powerInput"], 2), 1)
            updateDevice(self, 31, round(COP_HP2, 2), 1)
            updateDevice(self, 32, '', int(data["hp2"]["limitedByCop"]))
            updateDevice(self, 33, '', int(data["hp2"]["silentModeStatus"]))
        
        # Update flow meter devices if available
        if self.system_config['has_flow_meter']:
            updateDevice(self, 25, round(data["flowMeter"]["waterSupplyTemperature"], 1), 1)
            
    except Exception as e:
        Domoticz.Error("Error fetching Quatt data: {}".format(str(e)))

def updateDevice(self, unit, sValue, nValue):
    try:
        Devices[unit].Update(nValue=nValue, sValue=str(sValue), TimedOut=0)
    except Exception as e:
        Domoticz.Error("Error updating device {}: {}".format(unit, e))
