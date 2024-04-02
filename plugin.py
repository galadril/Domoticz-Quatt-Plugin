"""
<plugin key="Quatt" name="Quatt" author="Mark Heinis" version="0.0.3" wikilink="http://www.domoticz.com/wiki/plugins/plugin.html" externallink="https://github.com/galadril/Domoticz-Quatt-Plugin">
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
    oustandingPings = 0
    
    def __init__(self):
        self.update_interval = 3
        self.debug_level = None

    def onStart(self):
        if Parameters["Mode6"] == "":
            Parameters["Mode6"] = "-1"
        if Parameters["Mode6"] != "0": 
            Domoticz.Debugging(int(Parameters["Mode6"]))
            DumpConfigToLog()
            
        self.debug_level = Parameters["Mode6"]
        
        if ( 1 not in Devices ):
            Domoticz.Device(Name="Status", Unit=1, TypeName="Text", Image=7).Create()
        if ( 2 not in Devices ):            
            Domoticz.Device(Name="Room Temperature", Unit=2, TypeName="Temperature").Create()
        if ( 3 not in Devices ):
            Domoticz.Device(Name="Set Room Temperature", Unit=3, TypeName="Temperature").Create()
        if ( 4 not in Devices ):            
            Domoticz.Device(Name="Water Inlet Temperature", Unit=4, TypeName="Temperature").Create()
        if ( 5 not in Devices ):
            Domoticz.Device(Name="Water Outlet Temperature", Unit=5, TypeName="Temperature").Create()
        if ( 6 not in Devices ):            
            Domoticz.Device(Name="Supply Outlet Temperature", Unit=6, TypeName="Temperature").Create()
        if ( 7 not in Devices ):
            Domoticz.Device(Name="Supply Inlet Temperature", Unit=7, TypeName="Temperature").Create()
        if ( 8 not in Devices ):            
            Domoticz.Device(Name="Flow Rate", Unit=8, TypeName="Custom", Image=11).Create()
        if ( 9 not in Devices ):            
            Domoticz.Device(Name="OutsideTemperature", Unit=9, TypeName="Temperature").Create()
        if ( 10 not in Devices ):
            Domoticz.Device(Name="Request Room Temperature", Unit=10, TypeName="Temperature").Create()
        if ( 11 not in Devices ):
            Domoticz.Device(Name="Power", Unit=11, TypeName="Usage").Create()
        if ( 12 not in Devices ):
            Domoticz.Device(Name="Power Input", Unit=12, TypeName="Usage").Create()
        if ( 13 not in Devices ):
            Domoticz.Device(Name="COP", Unit=13, TypeName="Custom", Options={"ValueQuantity": "Custom", "ValueUnits": "COP"}).Create() 
        if ( 14 not in Devices ):            
            Domoticz.Device(Name="Flow Rate Filtered", Unit=14, TypeName="Custom", Image=11).Create()
            
        self.httpConn = Domoticz.Connection(Name="Quatt", Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=Parameters["Port"])
        self.httpConn.Connect()
        
        Domoticz.Heartbeat(30)
        
    def onConnect(self, Connection, Status, Description):
        Domoticz.Log("onConnect called: " + str(Status) + " | " + Connection.Address + ":" + Connection.Port)
        if Status == 0:
            Domoticz.Log("Connected successfully to: " + Connection.Address + ":" + Connection.Port)
            self.httpConn.Send(self.sendAfterConnect)
        else:
            Domoticz.Log("Failed to connect (" + str(Status) + ") to: " + Connection.Address + ":" + Connection.Port)
            Domoticz.Debug("Failed to connect (" + str(Status) + ") to: " + Connection.Address + ":" + Connection.Port + " with error: " + Description)
        return True

    def onStop(self):
        Domoticz.Debug("Quatt Plugin stopped")

    def onHeartbeat(self):
        try:
            if (self.httpConn.Connected()):
                if (self.oustandingPings > 3):
                    self.httpConn.Send(self.sendAfterConnect)
                    self.oustandingPings = 0
                else:
                    self.oustandingPings = self.oustandingPings + 1
            else:
                self.oustandingPings = 0
                self.httpConn.Connect()
            return True
        except:
            Domoticz.Log("Unhandled exception in onHeartbeat, forcing disconnect.")

    def onMessage(self, Connection, Data):
        Domoticz.Debug("onMessage called with data: " + str(Data))
        try:
            Response = json.loads(Data["Data"])
            processResponse(self, Response) 
        except Exception as e:
            Domoticz.Error("Error parsing Quatt json: {}".format(str(e)))

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called for connection to: " + Connection.Address + ":" + Connection.Port)
 
def processResponse(self, data):
    Domoticz.Debug("processResponse called: " + str(data))
    try:
        QuattCM = data["qc"]["supervisoryControlMode"]
        Quatt_Status = {
            0: 'Standby',
            1: 'Standby - heating',
            2: 'Heating - heatpump only',
            3: 'Heating - heatpump + boiler',
            4: 'Heating - boiler only',
            96: 'Anti-Freeze protection - boiler only',
            97: 'Anti-Freeze protection - boiler pre-pump',
            98: 'Anti-Freeze protection - water circulation',
            99: 'Fault - circulation pump on',
        }.get(QuattCM, 'Unknown')
        Domoticz.Log("Quatt Status: " + Quatt_Status)
        COP = round(data["hp1"]["power"] / data["hp1"]["powerInput"], 2)
        
        try:
            Devices[1].Update(nValue=1, sValue=str(Quatt_Status), TimedOut=0)
        except Exception as e:
            Domoticz.Error("Error updating device 1: {}".format(str(e)))            
        try:
            Devices[2].Update(nValue=1, sValue=str(data["thermostat"]["otFtRoomTemperature"]), TimedOut=0)
        except Exception as e:
            Domoticz.Error("Error updating device 1: {}".format(str(e)))
        try:
            Devices[3].Update(nValue=1, sValue=str(data["thermostat"]["otFtRoomSetpoint"]), TimedOut=0)
        except Exception as e:
            Domoticz.Error("Error updating device 1: {}".format(str(e)))
        try:
            Devices[4].Update(nValue=1, sValue=str(data["hp1"]["temperatureWaterIn"]), TimedOut=0)
        except Exception as e:
            Domoticz.Error("Error updating device 1: {}".format(str(e)))
        try:
            Devices[5].Update(nValue=1, sValue=str(data["hp1"]["temperatureWaterOut"]), TimedOut=0)
        except Exception as e:
            Domoticz.Error("Error updating device 1: {}".format(str(e)))
        try:
            Devices[6].Update(nValue=1, sValue=str(data["boiler"]["otFbSupplyOutletTemperature"]), TimedOut=0)
        except Exception as e:
            Domoticz.Error("Error updating device 1: {}".format(str(e)))
        try:
            Devices[7].Update(nValue=1, sValue=str(data["boiler"]["otFbSupplyInletTemperature"]), TimedOut=0)
        except Exception as e:
            Domoticz.Error("Error updating device 1: {}".format(str(e)))
        try:
            Devices[8].Update(nValue=1, sValue=str(data["flowMeter"]["flowRate"]), TimedOut=0)
        except Exception as e:
            Domoticz.Error("Error updating device 1: {}".format(str(e)))
        try:
            Devices[9].Update(nValue=1, sValue=str(data["hp1"]["temperatureOutside"]), TimedOut=0)
        except Exception as e:
            Domoticz.Error("Error updating device 1: {}".format(str(e)))
        try:
            Devices[10].Update(nValue=1, sValue=str(data["thermostat"]["otFtControlSetpoint"]), TimedOut=0)
        except Exception as e:
            Domoticz.Error("Error updating device 1: {}".format(str(e)))
        try:
            Devices[11].Update(nValue=1, sValue=str(round(data["hp1"]["power"], 2)) + ";" + str(round(data["hp1"]["power"], 2)), TimedOut=0)
        except Exception as e:
            Domoticz.Error("Error updating device 1: {}".format(str(e)))
        try:
            Devices[12].Update(nValue=1, sValue=str(round(data["hp1"]["powerInput"], 2)) + ";" + str(round(data["hp1"]["powerInput"], 2)), TimedOut=0)
        except Exception as e:
            Domoticz.Error("Error updating device 1: {}".format(str(e)))
        try:
            Devices[13].Update(nValue=1, sValue=str(COP), TimedOut=0)
        except Exception as e:
            Domoticz.Error("Error updating device 1: {}".format(str(e)))
        try:
            Devices[14].Update(nValue=1, sValue=str(data["qc"]["flowRateFiltered"]), TimedOut=0)
        except Exception as e:
            Domoticz.Error("Error updating device 1: {}".format(str(e)))
            
    except Exception as e:
        Domoticz.Error("Error fetching Quatt data: {}".format(str(e)))
        
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

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

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
