import re
import machine, json, network, rp2, ntptime, time, urequests

cached_data = {}

def load_config():
    with open('config.json') as f: # Open the config.json file
        return json.load(f) # Load the config.json file

def connect_to_wifi(SSID, PASSWORD):
    global wlan
    rp2.country("US") # Set country to US for reliable WiFi connection
    wlan = network.WLAN(network.STA_IF) # Create WLAN object
    wlan.active(True) # Activate the WLAN interface
    if not wlan.isconnected(): # If the device is not connected to the WiFi network
        print('connecting to network...') # Print message
        wlan.connect(SSID, PASSWORD) # Connect to the network
        while not wlan.isconnected() and timeout < 10: # While the device is not connected to the network and the timeout is less than 10
            if wlan.status() < 0 or wlan.status() >= 3: # If the device is not connected to the network or the connection is lost
                break 
            timeout += 1 # Increment the timeout
            time.sleep(1) # Sleep for 1 second
        if wlan.status() != 3: # If the device is not connected to the network
            print('failed to connect to network') # Print message
            return False
        print('network config:', wlan.ifconfig()) # Print message
    else:
        print('network already connected') # Print message

def update_time():
    ntptime.settime() # Set the time from the NTP server
    print('time:', time.localtime())
    
def get_eventlist(calendar_url):
    try:
        caldata = urequests.get(calendar_url)
    except: 
        print("Error getting calendar data")
        return cached_data.json
    if caldata.status_code != 200:
      return cached_data.json
    else:
        cached_data = cached_data.json
        return caldata.json

already_used = []

def get_next_event(caldata):
    for event in caldata:  # runs to the number of entries, i = to current entry
        for aevent in already_used:  # Skip past events that have already been used
            if event["uid"] == aevent["uid"]:
                pass
        return event  #returns the next event
    return None  #returns none if no event is found

def cleanupAlreadyUsed():  #remove excess already_Used events
    for i in already_used:  #runs to the number of entries, i = to current entry
        if i["End"] <= time.time():  #runs code if the end time for entry is less than current time
            print("Removeing " + i["uid"] + ", Its time has past")  #says its removing i event from already used
            already_used.remove(i)  #remove the i entry completely

def main():
    config = load_config()
    connect_to_wifi(config['WiFi_Settings']['SSID'], config['WiFi_Settings']['PASSWORD']) 

    # Initialize the Relays
    Relays = {
            machine.Pin("GP8", machine.Pin.OUT),
            machine.Pin("GP9", machine.Pin.OUT),
            machine.Pin("GP10", machine.Pin.OUT),
            machine.Pin("GP11", machine.Pin.OUT),
            machine.Pin("GP12", machine.Pin.OUT),
            machine.Pin("GP13", machine.Pin.OUT),
            machine.Pin("GP14", machine.Pin.OUT),
            machine.Pin("GP15", machine.Pin.OUT)
        }
    for relay in Relays: 
        if config['Relays'][relay.id()]['state'] == 'on':
            Relays[relay].on()
        Relays[relay].off()
    
    update_time()
    next_time_update =  time.time() + 14400 # Set the next time update to be 4 hours from now
    next_already_used_cleanup = time.time() + 86,400 # Set the next already used cleanup to be 4 hours from now

    while True:
        if time.time() > next_time_update:
            update_time()
            next_time_update = time.time() + 14400
        if time.time() > next_already_used_cleanup:
            cleanupAlreadyUsed()
            next_already_used_cleanup = time.time() + 86,400
        if get_next_event()["Start"] < time.time():
            event = get_next_event()
            already_used.append(event)
            evtsubject = event["Subject"].split(" ")
            for r_map in config['Relay_Mappings']:
                if evtsubject[0] == r_map["Name"]:
                    if evtsubject[1] == r_map["High_Value"]:
                        Relays[r_map["Relay_number"]].high()
                    elif evtsubject == r_map["Low_Value"]:
                        Relays[r_map["Relay_number"]].low()
        

