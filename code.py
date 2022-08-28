import machine, json, network, rp2, ntptime, time, urequests

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
    try:
        ntptime.settime() # Set the time from the NTP server
    except:
        print("Could Not Get Time")
    print('time:', time.localtime(), time.time())
    
def get_eventlist(calendar_url, rgb_led):
    try:
        caldata = urequests.get(calendar_url)
    except: 
        print("Error getting calendar data")
        caldata.close()
        return cached_data
    if caldata.status_code != 200:
        # turn on the red LED
        rgb_led[0].value(1)
        rgb_led[1].value(0)
        rgb_led[2].value(0)
        caldata.close()
        return cached_data
    else:
        # blink the blue LED for 2 tenths of a second and turn off the red LED
        rgb_led[0].value(0)
        rgb_led[1].value(0)
        rgb_led[2].value(1)
        time.sleep(0.2)
        rgb_led[1].value(1)
        rgb_led[2].value(0)
        cached_data = caldata.json()
        caldata.close()
        return cached_data

def get_next_event(caldata, already_used):
    #print(already_used)
    for event in caldata:  # runs to the number of entries, i = to current entry
        found = False
        for aevent in already_used:  # Skip past events that have already been used
            if event["ID"] is aevent["ID"]:
                found = True
        if found == True:
            continue
        return event  #returns the next event
    return None  #returns none if no event is found

def cleanupAlreadyUsed(already_used):  #remove excess already_Used events
    for i in already_used:  #runs to the number of entries, i = to current entry
        if i["End"] <= time.time():  #runs code if the end time for entry is less than current time
            print("Removeing " + i["ID"] + ", Its time has past")  #says its removing i event from already used
            already_used.remove(i)  #remove the i entry completely

def main():
    rgb_led = [
        machine.Pin(3, machine.Pin.OUT), # Red LED
        machine.Pin(4, machine.Pin.OUT), # Green LED
        machine.Pin(5, machine.Pin.OUT)  # Blue LED
    ]
    config = load_config()
    connect_to_wifi(config['WiFi_Settings']['SSID'], config['WiFi_Settings']['Password'], rgb_led) 

    # Initialize the Relays
    Relays = [
            machine.Pin(8, machine.Pin.OUT),
            machine.Pin(9, machine.Pin.OUT),
            machine.Pin(10, machine.Pin.OUT),
            machine.Pin(11, machine.Pin.OUT),
            machine.Pin(12, machine.Pin.OUT),
            machine.Pin(13, machine.Pin.OUT),
            machine.Pin(14, machine.Pin.OUT),
            machine.Pin(15, machine.Pin.OUT)
        ]
    for index in range(len(Relays)): 
        Relays[index].value(config["Relays_InitalState"][index])
    
    next_time_update =  time.time() + 14400 # Set the next time update to be 4 hours from now
    update_time(config['WiFi_Settings']['NTP_server']) # Update the time
    next_already_used_cleanup = time.time() + 3628 # Set the next already used cleanup to be 1 hour from now
    next_calendar_update = time.time() + 60 # Set the next calendar update to be 10 minutes from now
    caldata = get_eventlist(config['magic_url'], rgb_led) # Get the calendar data
    already_used = []
    while True:
        time.sleep(1)
        if time.time() > next_time_update: # If the time is greater than the next time update
            update_time() # Update the time
            next_time_update = time.time() + 14400
        if time.time() > next_already_used_cleanup: # If the time is greater than the next already used cleanup
            cleanupAlreadyUsed(already_used) # Cleanup the already used events
            next_already_used_cleanup = time.time() + 3628
        if time.time() > next_calendar_update:  # If the time is greater than the next calendar update
            caldata = get_eventlist(config['magic_url'], rgb_led)
            next_calendar_update = time.time() + 60
        event = get_next_event(caldata, already_used) # Get the next event
        if event is not None:
            if event["Start"] < time.time():
                already_used.append(event) # Add the event to the already used list
                evtsubject = event["Title"].split(" ") # Split the event subject into an array
                if len(evtsubject) < 2:
                   continue
                for r_map in config['Relay_Mappings']: # Run through the relay mappings
                    if evtsubject[0] == r_map["Name"]: # If the event subject matches the relay mapping name
                        if evtsubject[1] == r_map["High_Value"]: # If the event subject matches the relay mapping high value
                            # Write a log message containing the name and action of the event
                            print(r_map["Name"] + " is " + r_map["High_Value"])
                            Relays[r_map["Relay_number"]].value(1) # Turn the relay on
                            break
                        elif evtsubject[1] == r_map["Low_Value"]: # If the event subject matches the relay mapping low value
                            # Write a log message containing the name and action of the event
                            print(r_map["Name"] + " is " + r_map["Low_Value"])
                            Relays[r_map["Relay_number"]].value(0) # Turn the relay off
                            break
                        else:
                            print("Action does not match config", evtsubject)
         
if __name__ == "__main__":
    main()
