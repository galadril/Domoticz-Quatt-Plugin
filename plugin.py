"""
<plugin key="Quatt" name="Quatt" author="Mark Heinis" version="0.0.8" wikilink="http://www.domoticz.com/wiki/plugins/plugin.html" externallink="https://github.com/galadril/Domoticz-Quatt-Plugin">
    <description>
        Plugin for retrieving and updating Quatt data.
        Connect to your CiC at http://local-cic-IP:8080/ to see how this works.
        More info about Quatt: https://www.quatt.io/
    </description>
    <params>
        <param field="Address" label="IP Address" width="200px" required="true" default="127.0.0.1"/>
        <param field="Port" label="Port" width="40px" required="true" default="8080"/>
        <param field="Mode6" label="Debug" width="200px">
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
        self.discovered_data = None

    def onStart(self):
        if Parameters["Mode6"] == "":
            Parameters["Mode6"] = "-1"
        if Parameters["Mode6"] != "0": 
            Domoticz.Debugging(int(Parameters["Mode6"]))
            DumpConfigToLog()
            
        self.debug_level = Parameters["Mode6"]
        
        # Create basic devices first, dynamic devices will be created when we receive data
        createBasicDevices(self)
            
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
            
            # Create dynamic devices based on available data sections
            if self.discovered_data is None:
                self.discovered_data = Response
                createDynamicDevices(self, Response)
            
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

def createBasicDevices(self):
    """Create basic devices that are always available"""
    basic_device_definitions = [
        (1, "Status", "Text", 7),
        (2, "Room Temperature", "Temperature"),
        (3, "Set Room Temperature", "Temperature"),
        (10, "Request Room Temperature", "Temperature"),
        (14, "Flow Rate Filtered", "Custom", 11),
        (19, "CH Enabled", "Switch"),
        (20, "Cooling Enabled", "Switch"),
        (21, "DHW Enabled", "Switch"),
        (24, "Sticky Pump Protection Enabled", "Switch"),
    ]
    
    for unit, name, type_name, *options in basic_device_definitions:
        if unit not in Devices:
            Domoticz.Device(Name=name, Unit=unit, TypeName=type_name, Options=options[0] if options else {}, Image=options[1] if len(options) > 1 else 0).Create()

def createDynamicDevices(self, data):
    """Create devices dynamically based on available JSON sections"""
    
    # HP1 devices (units 4, 5, 9, 11, 12, 13, 22, 23)
    if "hp1" in data and data["hp1"] is not None:
        hp1_devices = [
            (4, "HP1 Water Inlet Temperature", "Temperature"),
            (5, "HP1 Water Outlet Temperature", "Temperature"),
            (9, "HP1 Outside Temperature", "Temperature"),
            (11, "HP1 Power Heat", "Usage", 10),
            (12, "HP1 Power Electric", "Usage"),
            (13, "HP1 COP", "Custom", {"ValueQuantity": "Custom", "ValueUnits": "COP"}),
            (22, "HP1 Limited by COP", "Switch"),
            (23, "HP1 Silent Mode Status", "Switch"),
        ]
        for unit, name, type_name, *options in hp1_devices:
            if unit not in Devices:
                Domoticz.Device(Name=name, Unit=unit, TypeName=type_name, Options=options[0] if options else {}, Image=options[1] if len(options) > 1 else 0).Create()
    
    # HP2 devices (units 26-31)
    if "hp2" in data and data["hp2"] is not None:
        hp2_devices = [
            (26, "HP2 Water Inlet Temperature", "Temperature"),
            (27, "HP2 Water Outlet Temperature", "Temperature"),
            (28, "HP2 Outside Temperature", "Temperature"),
            (29, "HP2 Power Heat", "Usage", 10),
            (30, "HP2 Power Electric", "Usage"),
            (31, "HP2 COP", "Custom", {"ValueQuantity": "Custom", "ValueUnits": "COP"}),
            (32, "HP2 Limited by COP", "Switch"),
            (33, "HP2 Silent Mode Status", "Switch"),
        ]
        for unit, name, type_name, *options in hp2_devices:
            if unit not in Devices:
                Domoticz.Device(Name=name, Unit=unit, TypeName=type_name, Options=options[0] if options else {}, Image=options[1] if len(options) > 1 else 0).Create()
    
    # Boiler devices (units 6, 7, 15, 16, 17, 18, 34)
    if data.get("boiler"):
        boiler_devices = [
            (6, "Boiler Supply Outlet Temperature", "Temperature"),
            (7, "Boiler Supply Inlet Temperature", "Temperature"),
            (15, "Boiler On/Off", "Switch"),
            (16, "Boiler CH Mode Active", "Switch"),
            (17, "Boiler DHW Active", "Switch"),
            (18, "Boiler Flame On", "Switch"),
            (34, "Boiler Water Pressure", "Pressure"),
        ]
        for unit, name, type_name, *options in boiler_devices:
            if unit not in Devices:
                Domoticz.Device(Name=name, Unit=unit, TypeName=type_name, Options=options[0] if options else {}, Image=options[1] if len(options) > 1 else 0).Create()
    
    # Flow meter devices (unit 25)
    if "flowMeter" in data and data["flowMeter"] is not None:
        flowMeter_devices = [
            (25, "Water Supply Temperature", "Temperature")
        ]
        for unit, name, type_name, *options in flowMeter_devices:
            if unit not in Devices:
                Domoticz.Device(Name=name, Unit=unit, TypeName=type_name, Options=options[0] if options else {}, Image=options[1] if len(options) > 1 else 0).Create()

def processResponse(self, data):
    Domoticz.Log("processResponse called: " + str(data))
    try:
        # Process basic status and thermostat data
        if "qc" in data and "supervisoryControlMode" in data["qc"]:
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
            updateDevice(self, 1, Quatt_Status, 1)
        
        # Process thermostat data
        if "thermostat" in data:
            thermo = data["thermostat"]
            if "otFtRoomTemperature" in thermo:
                updateDevice(self, 2, round(thermo["otFtRoomTemperature"], 2), 1)
            if "otFtRoomSetpoint" in thermo:
                updateDevice(self, 3, round(thermo["otFtRoomSetpoint"], 1), 1)
            if "otFtControlSetpoint" in thermo:
                updateDevice(self, 10, round(thermo["otFtControlSetpoint"], 2), 1)
            if "otFtChEnabled" in thermo:
                updateDevice(self, 19, '', int(thermo["otFtChEnabled"]))
            if "otFtCoolingEnabled" in thermo:
                updateDevice(self, 20, '', int(thermo["otFtCoolingEnabled"]))
            if "otFtDhwEnabled" in thermo:
                updateDevice(self, 21, '', int(thermo["otFtDhwEnabled"]))
        
        # Process HP1 data
        if "hp1" in data and data["hp1"] is not None:
            hp1 = data["hp1"]
            COP1 = 0
            if "powerInput" in hp1 and hp1["powerInput"] > 0 and "power" in hp1:
                COP1 = hp1["power"] / hp1["powerInput"]
                updateDevice(self, 13, round(COP1, 2), 1)
            
            if "temperatureWaterIn" in hp1:
                updateDevice(self, 4, round(hp1["temperatureWaterIn"], 2), 1)
            if "temperatureWaterOut" in hp1:
                updateDevice(self, 5, round(hp1["temperatureWaterOut"], 2), 1)
            if "temperatureOutside" in hp1:
                updateDevice(self, 9, round(hp1["temperatureOutside"], 1), 1)
            if "power" in hp1:
                updateDevice(self, 11, round(hp1["power"], 2), 1)
            if "powerInput" in hp1:
                updateDevice(self, 12, round(hp1["powerInput"], 2), 1)
            if "limitedByCop" in hp1:
                updateDevice(self, 22, '', int(hp1["limitedByCop"]))
            if "silentModeStatus" in hp1:
                updateDevice(self, 23, '', int(hp1["silentModeStatus"]))
        
        # Process HP2 data
        if "hp2" in data and data["hp2"] is not None:
            hp2 = data["hp2"]
            COP2 = 0
            if "powerInput" in hp2 and hp2["powerInput"] > 0 and "power" in hp2:
                COP2 = hp2["power"] / hp2["powerInput"]
                updateDevice(self, 31, round(COP2, 2), 1)
            
            if "temperatureWaterIn" in hp2:
                updateDevice(self, 26, round(hp2["temperatureWaterIn"], 2), 1)
            if "temperatureWaterOut" in hp2:
                updateDevice(self, 27, round(hp2["temperatureWaterOut"], 2), 1)
            if "temperatureOutside" in hp2:
                updateDevice(self, 28, round(hp2["temperatureOutside"], 1), 1)
            if "power" in hp2:
                updateDevice(self, 29, round(hp2["power"], 2), 1)
            if "powerInput" in hp2:
                updateDevice(self, 30, round(hp2["powerInput"], 2), 1)
            if "limitedByCop" in hp2:
                updateDevice(self, 32, '', int(hp2["limitedByCop"]))
            if "silentModeStatus" in hp2:
                updateDevice(self, 33, '', int(hp2["silentModeStatus"]))
        
        # Process boiler data
        if (boiler := data.get("boiler")) is not None:
            if "otFbSupplyOutletTemperature" in boiler and boiler["otFbSupplyOutletTemperature"] is not None:
                updateDevice(self, 6, round(boiler["otFbSupplyOutletTemperature"], 2), 1)
            if "otFbSupplyInletTemperature" in boiler and boiler["otFbSupplyInletTemperature"] is not None:
                updateDevice(self, 7, round(boiler["otFbSupplyInletTemperature"], 2), 1)
            if "oTtbTurnOnOffBoilerOn" in boiler and boiler["oTtbTurnOnOffBoilerOn"] is not None:
                updateDevice(self, 15, '', int(boiler["oTtbTurnOnOffBoilerOn"]))
            if "otFbChModeActive" in boiler and boiler["otFbChModeActive"] is not None:
                updateDevice(self, 16, '', int(boiler["otFbChModeActive"]))
            if "otFbDhwActive" in boiler and boiler["otFbDhwActive"] is not None:
                updateDevice(self, 17, '', int(boiler["otFbDhwActive"]))
            if "otFbFlameOn" in boiler and boiler["otFbFlameOn"] is not None:
                updateDevice(self, 18, '', int(boiler["otFbFlameOn"]))
            if (value := boiler.get("otFbWaterPressure")) is not None:
                updateDevice(self, 34, round(value, 2), 1)
        
        # Process QC data
        if "qc" in data:
            qc = data["qc"]
            if "flowRateFiltered" in qc:
                updateDevice(self, 14, round(qc["flowRateFiltered"], 1), 1)
            if "stickyPumpProtectionEnabled" in qc:
                updateDevice(self, 24, '', int(qc["stickyPumpProtectionEnabled"]))
        
        # Process flow meter data
        if "flowMeter" in data and data["flowMeter"] is not None:
            flowMeter = data["flowMeter"]
            if "waterSupplyTemperature" in flowMeter:
                updateDevice(self, 25, round(flowMeter["waterSupplyTemperature"], 1), 1)
            
    except Exception as e:
        Domoticz.Error("Error fetching Quatt data: {}".format(str(e)))

def updateDevice(self, unit, sValue, nValue):
    try:
        if unit in Devices:
            Devices[unit].Update(nValue=nValue, sValue=str(sValue), TimedOut=0)
        else:
            Domoticz.Debug("Device {} not found, skipping update".format(unit))
    except Exception as e:
        Domoticz.Error("Error updating device {}: {}".format(unit, e))
