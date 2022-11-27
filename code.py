import  json, wifi, board, time, adafruit_ntp, socketpool, adafruit_datetime, adafruit_requests, rtc, ssl
from digitalio import DigitalInOut, Direction

cached_data = ""
already_used = []

def load_config():
    with open('config.json') as f: # Open the config.json file
        conf = json.load(f) # Load the config.json file
        # print (conf)
        return conf

def connect_to_wifi(SSID, PASSWORD, rgb_led):
    if wifi.radio.ipv4_address is None:
        print('connecting to network...') # Print message
        try:
            wifi.radio.connect(SSID, PASSWORD, timeout = 1)
        except ConnectionError:
            print("Bad SSID/Password could not connect")
            rgb_led[0].value = 1
            return

        if wifi.radio.ipv4_address is None: # If the device is not connected to the WiFi network
            while wifi.radio.ipv4_address is None and timeout < 10: # While the device is not connected to the network and the timeout is less than 10
                timeout += 1 # Increment the timeout
                # Blink the blue LED every half second
                rgb_led[2].value = 1
                wifi.radio.connect(SSID, PASSWORD, timeout = 0.75)
                rgb_led[2].value = 0
                time.sleep(0.25)
            if wifi.radio.ipv4_address is None: # If the device is not connected to the network
                print('failed to connect to network') # Print message
                # Turn on the Red LED
                rgb_led[0].value = 1
                return False
            print('network config: {IP:%s,GW:%s,SBN:%s,DNS:%s}' % (wifi.radio.ipv4_address,wifi.radio.ipv4_gateway,wifi.radio.ipv4_subnet,wifi.radio.ipv4_dns)) # Print message
            # Turn on the Green LED
            rgb_led[0].value = 0
            rgb_led[1].value = 1
            rgb_led[2].value = 0
            return True
    else:
        print('network already connected') # Print message
        print('network config: {IP:%s,GW:%s,SBN:%s,DNS:%s}' % (wifi.radio.ipv4_address,wifi.radio.ipv4_gateway,wifi.radio.ipv4_subnet,wifi.radio.ipv4_dns)) # Print message
        return True

def create_ntp(ntp_host = "time.nist.gov"):
    global ntptime
    ntptime = adafruit_ntp.NTP(pool, server=ntp_host)
    rtc.RTC().datetime = ntptime.datetime
    

def update_time_from_ntp():
    rtc.RTC().datetime = ntptime.datetime

def get_time(intime = None):
    if intime is None: 
        intime = time.localtime()
    else: 
        intime = time.localtime(intime)
    return adafruit_datetime.datetime(
        year=intime.tm_year,
        month=intime.tm_mon, 
        day=intime.tm_mday, 
        hour=intime.tm_hour, 
        minute=intime.tm_min,
        second=intime.tm_sec
    )
    
def get_eventlist(calendar_url, rgb_led):
    global cached_data
    try:
        caldata = http_req.get(calendar_url)
    except: 
        print("Error getting calendar data")
        return cached_data
    if caldata.status_code != 200:
        # turn on the red LED
        rgb_led[0].value = 1
        rgb_led[1].value = 0
        rgb_led[2].value = 0
        caldata.close()
        return cached_data
    else:
        # blink the blue LED for 2 tenths of a second and turn off the red LED
        rgb_led[0].value = 0
        rgb_led[1].value = 0
        rgb_led[2].value = 1
        time.sleep(0.2)
        rgb_led[1].value = 1
        rgb_led[2].value = 0
        cached_data = caldata.json()
        caldata.close()
        return cached_data

def get_next_event(caldata):
    global already_used
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

def cleanupAlreadyUsed():  #remove excess already_Used events
    for i in already_used:  #runs to the number of entries, i = to current entry
        if get_time(intime = i["End"]/ 1000) <= time.time():  #runs code if the end time for entry is less than current time
            print("Removeing " + i["ID"] + ", Its time has past")  #says its removing i event from already used
            already_used.remove(i)  #remove the i entry completely

def main():
    rgb_led = [
        DigitalInOut(board.GP3), # Red LED
        DigitalInOut(board.GP4), # Green LED
        DigitalInOut(board.GP5)  # Blue LED
    ]
    for led in rgb_led:
        led.direction = Direction.OUTPUT

    config = load_config()
    wifi_connected = connect_to_wifi(config['WiFi_Settings']['SSID'], config['WiFi_Settings']['Password'], rgb_led) 

    if not wifi_connected: 
        print("Could Not Connect to wifi, Waiting 30 minutes the powercycleing")
        time.sleep(1800)
        import supervisor
        supervisor.reload()

    global pool
    global http_req
    pool = socketpool.SocketPool(wifi.radio)

    http_req = adafruit_requests.Session(pool, ssl_context=ssl.create_default_context())
    create_ntp(config['WiFi_Settings']['NTP_server']) # Update the time

    # Initialize the Relays
    Relays = [
            DigitalInOut(board.GP8),
            DigitalInOut(board.GP9),
            DigitalInOut(board.GP10),
            DigitalInOut(board.GP11),
            DigitalInOut(board.GP12),
            DigitalInOut(board.GP13),
            DigitalInOut(board.GP14),
            DigitalInOut(board.GP15)
        ]
    for index, relay in enumerate(Relays):
        relay.direction = Direction.OUTPUT
        relay.value = config["Relays_InitalState"][index]
    
    print("Performing first retrival")
    curent_time = get_time() 
    next_already_used_cleanup = curent_time + adafruit_datetime.timedelta(hours=1) # Set the next already used cleanup to be 1 hour from now
    next_calendar_update = curent_time + adafruit_datetime.timedelta(minutes=10) # Set the next calendar update to be 10 minutes from now
    next_time_update = curent_time + adafruit_datetime.timedelta(hours=4)
    caldata = get_eventlist(config['magic_url'], rgb_led) # Get the calendar data
    if caldata == "":
        print("Could not get data")
    # else: 
    #     print(caldata)
    while True:
        time.sleep(1)
        curent_time = get_time()
        if curent_time > next_time_update:
            update_time_from_ntp()
            next_time_update = curent_time + adafruit_datetime.timedelta(hours=4)
        if curent_time > next_already_used_cleanup: # If the time is greater than the next already used cleanup
            print("Cleanup on aisle 5, cleaning past events")
            cleanupAlreadyUsed() # Cleanup the already used events
            next_already_used_cleanup = curent_time + adafruit_datetime.timedelta(hours=1)
        if curent_time > next_calendar_update:  # If the time is greater than the next calendar update
            print("Performaing Calander Update")
            caldata = get_eventlist(config['magic_url'], rgb_led)
            next_calendar_update = curent_time + adafruit_datetime.timedelta(minutes=10)
        event = get_next_event(caldata) # Get the next event
        if event is not None:
            if get_time(intime = event["Start"] / 1000) < curent_time:
                print("Working on event: %s, with action of %s" % (event["ID"],event["Start"]))
                already_used.append(event) # Add the event to the already used list
                print(already_used)
                evtsubject = event["Title"].split(" ") # Split the event subject into an array
                if len(evtsubject) < 2:
                   continue
                for r_map in config['Relay_Mappings']: # Run through the relay mappings
                    if evtsubject[0] == r_map["Name"]: # If the event subject matches the relay mapping name
                        if evtsubject[1] == r_map["High_Value"]: # If the event subject matches the relay mapping high value
                            # Write a log message containing the name and action of the event
                            print(r_map["Name"] + " is " + r_map["High_Value"])
                            Relays[r_map["Relay_number"]].value = 1 # Turn the relay on
                            break
                        elif evtsubject[1] == r_map["Low_Value"]: # If the event subject matches the relay mapping low value
                            # Write a log message containing the name and action of the event
                            print(r_map["Name"] + " is " + r_map["Low_Value"])
                            Relays[r_map["Relay_number"]].value = 0 # Turn the relay off
                            break
                        else:
                            print("Action does not match config", evtsubject)
         
if __name__ == "__main__":
    main()