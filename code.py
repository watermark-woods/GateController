import machine, json, network, rp2, ntptime, time, urequests

cached_data = {}

def load_config():
    with open('config.json') as f: # Open the config.json file
        return json.load(f) # Load the config.json file

def connect_to_wifi(SSID, PASSWORD, rgb_led):
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
            # Blink the blue LED every half second
            rgb_led[2].value(1)
            time.sleep(0.5)
            rgb_led[2].value(0)
            time.sleep(0.5)
        if wlan.status() != 3: # If the device is not connected to the network
            print('failed to connect to network') # Print message
            # Turn on the Red LED
            rgb_led[0].value(1)
            return False
        print('network config:', wlan.ifconfig()) # Print message
        # Turn on the Green LED
        rgb_led[0].value(0)
        rgb_led[1].value(1)
        rgb_led[2].value(0)
        return True
    else:
        print('network already connected') # Print message

def update_time(ntp_host = "time.nist.gov"):
    ntptime.host = ntp_host # Set the host to pool.ntp.org
    ntptime.settime() # Set the time from the NTP server
    print('time:', time.localtime())
    
def get_eventlist(calendar_url, rgb_led):
    try:
        caldata = urequests.get(calendar_url)
    except: 
        print("Error getting calendar data")
        caldata.close()
        return cached_data.json
    if caldata.status_code != 200:
        # turn on the red LED
        rgb_led[0].value(1)
        rgb_led[1].value(0)
        rgb_led[2].value(0)
        caldata.close()
        return cached_data.json
    else:
        # blink the blue LED for 2 tenths of a second and turn off the red LED
        rgb_led[0].value(0)
        rgb_led[1].value(0)
        rgb_led[2].value(1)
        time.sleep(0.2)
        rgb_led[1].value(1)
        rgb_led[2].value(0)
        cached_data = cached_data.json
        caldata.close()
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
    rgb_led = [
        machine.Pin("GP3", machine.Pin.OUT), # Red LED
        machine.Pin("GP4", machine.Pin.OUT), # Green LED
        machine.Pin("GP5", machine.Pin.OUT)  # Blue LED
    ]
    config = load_config()
    connect_to_wifi(config['WiFi_Settings']['SSID'], config['WiFi_Settings']['PASSWORD'], rgb_led) 

    # Initialize the Relays
    Relays = [
            machine.Pin("GP8", machine.Pin.OUT),
            machine.Pin("GP9", machine.Pin.OUT),
            machine.Pin("GP10", machine.Pin.OUT),
            machine.Pin("GP11", machine.Pin.OUT),
            machine.Pin("GP12", machine.Pin.OUT),
            machine.Pin("GP13", machine.Pin.OUT),
            machine.Pin("GP14", machine.Pin.OUT),
            machine.Pin("GP15", machine.Pin.OUT)
        ]
    for relay in Relays: 
        if config['Relays'][relay.id()]['state'] == 'on':
            Relays[relay].on()
        Relays[relay].off()
    
    next_time_update =  time.time() + 14400 # Set the next time update to be 4 hours from now
    update_time(config['NTP_Settings']['NTP_server']) # Update the time
    next_already_used_cleanup = time.time() + 86,400 # Set the next already used cleanup to be 4 hours from now
    next_calendar_update = time.time() + 600 # Set the next calendar update to be 10 minutes from now
    caldata = get_eventlist(config['Calendar_URL'], rgb_led) # Get the calendar data
    while True:
        if time.time() > next_time_update: # If the time is greater than the next time update
            update_time() # Update the time
            next_time_update = time.time() + 14400
        if time.time() > next_already_used_cleanup: # If the time is greater than the next already used cleanup
            cleanupAlreadyUsed() # Cleanup the already used events
            next_already_used_cleanup = time.time() + 86,400
        if time.time() > next_calendar_update:  # If the time is greater than the next calendar update
            caldata = get_eventlist(config['Calendar_URL'], rgb_led)
            next_calendar_update = time.time() + 600
        if get_next_event(caldata)["Start"] < time.time():
            event = get_next_event(caldata) # Get the next event
            already_used.append(event) # Add the event to the already used list
            evtsubject = event["Subject"].split(" ") # Split the event subject into an array
            for r_map in config['Relay_Mappings']: # Run through the relay mappings
                if evtsubject[0] == r_map["Name"]: # If the event subject matches the relay mapping name
                    if evtsubject[1] == r_map["High_Value"]: # If the event subject matches the relay mapping high value
                        # Write a log message containing the name and action of the event
                        print(r_map["Name"] + " is " + r_map["High_Value"])
                        Relays[r_map["Relay_number"]].value(1) # Turn the relay on
                    elif evtsubject == r_map["Low_Value"]: # If the event subject matches the relay mapping low value
                        # Write a log message containing the name and action of the event
                        print(r_map["Name"] + " is " + r_map["Low_Value"])
                        Relays[r_map["Relay_number"]].value(0) # Turn the relay off
        

