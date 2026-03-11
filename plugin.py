"""
<plugin key="Quatt" name="Quatt" author="Mark Heinis" version="0.0.10" wikilink="http://www.domoticz.com/wiki/plugins/plugin.html" externallink="https://github.com/galadril/Domoticz-Quatt-Plugin">
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
import time

class QuattPlugin:
    httpConn = None
    sendAfterConnect = {'Verb': 'GET', 'URL': '/beta/feed/data.json'}

    def __init__(self):
        self.discovered_data = None

    def onStart(self):
        if mode6 := Parameters.get("Mode6", "-1"):
            Domoticz.Debugging(int(mode6))
            _dump_config_to_log()

        # Create basic devices first, dynamic devices will be created when we receive data
        _create_basic_devices(self)
            
        self.httpConn = Domoticz.Connection(Name="Quatt", Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=Parameters["Port"])
        self.httpConn.Connect()
        
        Domoticz.Heartbeat(30)
        
    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug(f"onConnect called: {Status} | {Connection.Address}:{Connection.Port}")
        if Status == 0:
            Domoticz.Debug(f"Connected successfully to: {Connection.Address}:{Connection.Port}")
            self.httpConn.Send(self.sendAfterConnect)
        else:
            Domoticz.Log(f"Failed to connect ({Status}) to: {Connection.Address}:{Connection.Port}")
            Domoticz.Debug(f"Failed to connect ({Status}) to: {Connection.Address}:{Connection.Port} with error: {Description}")
        return True

    def onStop(self):
        Domoticz.Debug("Quatt Plugin stopped")

    def onHeartbeat(self):
        if self.httpConn.Connecting():
            Domoticz.Error("onHeartBeat connecting")
        else:
            if self.httpConn.Connected():
                Domoticz.Error("onHeartBeat connected")
                self.httpConn.Disconnect()
                self.httpConn=None
                self.httpConn = Domoticz.Connection(Name="Quatt", Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=Parameters["Port"])
            else:
                Domoticz.Log("onHeartBeat unconnected")
            self.httpConn.Connect()

    def onMessage(self, Connection, Data):
        Domoticz.Debug(f"onMessage called with data: {Data}")
        try:
            response = json.loads(Data["Data"])
            
            # Create dynamic devices based on available data sections
            if self.discovered_data is None:
                self.discovered_data = response
                _create_dynamic_devices(self, response)
            
            _process_response(self, response)
        except Exception as e:
            Domoticz.Error(f"Error parsing Quatt json: {e}")

    def onDisconnect(self, Connection):
        Domoticz.Debug(f"onDisconnect called for connection to: {Connection.Address}:{Connection.Port}")


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

def _dump_config_to_log():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug(f"'{x}':'{Parameters[x]}'")
    Domoticz.Debug(f"Device count: {len(Devices)}")
    for x in Devices:
        Domoticz.Debug(f"Device:           {x} - {Devices[x]}")
        Domoticz.Debug(f"Device ID:       '{Devices[x].ID}'")
        Domoticz.Debug(f"Device Name:     '{Devices[x].Name}'")
        Domoticz.Debug(f"Device nValue:    {Devices[x].nValue}")
        Domoticz.Debug(f"Device sValue:   '{Devices[x].sValue}'")
        Domoticz.Debug(f"Device LastLevel: {Devices[x].LastLevel}")
    return

def _create_basic_devices(self):
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
        (35, "Time Delay", "Custom", {"ValueQuantity": "Delay", "ValueUnits": "millis"}),
    ]
    
    for unit, name, type_name, *options in basic_device_definitions:
        if unit not in Devices:
            Domoticz.Device(Name=name, Unit=unit, TypeName=type_name, Options=options[0] if options else {}, Image=options[1] if len(options) > 1 else 0).Create()

def _create_dynamic_devices(self, data):
    """Create devices dynamically based on available JSON sections"""
    
    # HP1 devices (units 4, 5, 9, 11, 12, 13, 22, 23)
    if data.get("hp1"):
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
    if data.get("hp2"):
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
    if data.get("flowMeter"):
        flowMeter_devices = [
            (25, "Water Supply Temperature", "Temperature")
        ]
        for unit, name, type_name, *options in flowMeter_devices:
            if unit not in Devices:
                Domoticz.Device(Name=name, Unit=unit, TypeName=type_name, Options=options[0] if options else {}, Image=options[1] if len(options) > 1 else 0).Create()

def _process_response(self, data):
    Domoticz.Log("processResponse called: " + str(data))
    try:
        # Process basic status and thermostat data
        if (qc := data.get("qc")) is not None and (QuattCM := qc.get("supervisoryControlMode")) is not None:
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
            _update_device(self, 1, Quatt_Status, 1)
        
        # Process thermostat data
        if (thermo := data.get("thermostat")) is not None:
            if (value := thermo.get("otFtRoomTemperature")) is not None:
                _update_device(self, 2, round(value, 2), 1)
            if (value := thermo.get("otFtRoomSetpoint")) is not None:
                _update_device(self, 3, round(value, 1), 1)
            if (value := thermo.get("otFtControlSetpoint")) is not None:
                _update_device(self, 10, round(value, 2), 1)
            if (value := thermo.get("otFtChEnabled")) is not None:
                _update_device(self, 19, '', int(value))
            if (value := thermo.get("otFtCoolingEnabled")) is not None:
                _update_device(self, 20, '', int(value))
            if (value := thermo.get("otFtDhwEnabled")) is not None:
                _update_device(self, 21, '', int(value))
        
        # Process HP1 data
        if (hp1 := data.get("hp1")) is not None:
            if (powerInput := hp1.get("powerInput", 0)) > 0 and (power := hp1.get("power")) is not None:
                COP1 = power / powerInput
                _update_device(self, 13, round(COP1, 2), 1)

            if (value := hp1.get("temperatureWaterIn")) is not None:
                _update_device(self, 4, round(value, 2), 1)
            if (value := hp1.get("temperatureWaterOut")) is not None:
                _update_device(self, 5, round(value, 2), 1)
            if (value := hp1.get("temperatureOutside")) is not None:
                _update_device(self, 9, round(value, 1), 1)
            if (value := hp1.get("power")) is not None:
                _update_device(self, 11, round(value, 2), 1)
            if (value := hp1.get("powerInput")) is not None:
                _update_device(self, 12, round(value, 2), 1)
            if (value := hp1.get("limitedByCop")) is not None:
                _update_device(self, 22, '', int(value))
            if (value := hp1.get("silentModeStatus")) is not None:
                _update_device(self, 23, '', int(value))
        
        # Process HP2 data
        if (hp2 := data.get("hp2")) is not None:
            if (powerInput := hp2.get("powerInput", 0)) > 0 and (power := hp2.get("power")) is not None:
                COP2 = power / powerInput
                _update_device(self, 31, round(COP2, 2), 1)
            
            if (value := hp2.get("temperatureWaterIn")) is not None:
                _update_device(self, 26, round(value, 2), 1)
            if (value := hp2.get("temperatureWaterOut")) is not None:
                _update_device(self, 27, round(value, 2), 1)
            if (value := hp2.get("temperatureOutside")) is not None:
                _update_device(self, 28, round(value, 1), 1)
            if (value := hp2.get("power")) is not None:
                _update_device(self, 29, round(value, 2), 1)
            if (value := hp2.get("powerInput")) is not None:
                _update_device(self, 30, round(value, 2), 1)
            if (value := hp2.get("limitedByCop")) is not None:
                _update_device(self, 32, '', int(value))
            if (value := hp2.get("silentModeStatus")) is not None:
                _update_device(self, 33, '', int(value))
        
        # Process boiler data
        if (boiler := data.get("boiler")) is not None:
            if (value := boiler.get("otFbSupplyOutletTemperature"))  is not None:
                _update_device(self, 6, round(value, 2), 1)
            if (value := boiler.get("otFbSupplyInletTemperature"))  is not None:
                _update_device(self, 7, round(value, 2), 1)
            if (value := boiler.get("oTtbTurnOnOffBoilerOn")) is not None:
                _update_device(self, 15, '', int(value))
            if (value := boiler.get("otFbChModeActive")) is not None:
                _update_device(self, 16, '', int(value))
            if (value := boiler.get("otFbDhwActive")) is not None:
                _update_device(self, 17, '', int(value))
            if (value := boiler.get("otFbFlameOn")) is not None:
                _update_device(self, 18, '', int(value))
            if (value := boiler.get("otFbWaterPressure")) is not None:
                _update_device(self, 34, round(value, 2), 1)
        
        # Process QC data
        if (qc := data.get("qc")) is not None:
            if (value := qc.get("flowRateFiltered")) is not None:
                _update_device(self, 14, round(value, 1), 1)
            if (value := qc.get("stickyPumpProtectionEnabled")) is not None:
                _update_device(self, 24, '', int(value))
        
        # Process flow meter data
        if (flowMeter := data.get("flowMeter")) is not None:
            if (value := flowMeter.get("waterSupplyTemperature")) is not None:
                _update_device(self, 25, round(value, 1), 1)

        # Time Delay
        if (cic_time := data.get("time")) is not None:
            if (cic_ts := cic_time.get("ts")) is not None:
                cic_ts_millis = cic_ts
                system_ts_millis = time.time_ns() // 1_000_000
                delay = system_ts_millis - cic_ts_millis
                _update_device(self, 35, delay, 0)

    except Exception as e:
        Domoticz.Error(f"Error fetching Quatt data: {e}")

def _update_device(self, unit, sValue, nValue):
    try:
        if unit in Devices:
            Devices[unit].Update(nValue=nValue, sValue=str(sValue), TimedOut=0)
        else:
            Domoticz.Debug(f"Device {unit} not found, skipping update")
    except Exception as e:
        Domoticz.Error(f"Error updating device {unit}: {e}")
