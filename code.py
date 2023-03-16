import json, wifi, board, time, adafruit_ntp, socketpool, adafruit_datetime, adafruit_requests, rtc, ssl, microcontroller
import gc
from digitalio import DigitalInOut, Direction

# declare global variables
cached_data = ""   # used as a backup if we can't later access the calendar

RGB_RED       = 0
RGB_GREEN     = 1
RGB_BLUE      = 2
RGB_PURPLE    = 3
RGB_YELLOW    = 4
RGB_TURQUOISE = 5
RGB_WHITE     = 6
RGB_OFF       = 7

# simple loading of the configuration
def load_config():
    with open('config.json') as f: # Open the config.json file
        conf = json.load(f) # Load the config.json file
    return conf

def set_rgb_led(rgb_led, rgb_color):

    if rgb_color == RGB_RED:
        rgb_led[RGB_RED].value   = 1
        rgb_led[RGB_GREEN].value = 0
        rgb_led[RGB_BLUE].value  = 0
    elif rgb_color == RGB_GREEN:
        rgb_led[RGB_RED].value   = 0
        rgb_led[RGB_GREEN].value = 1
        rgb_led[RGB_BLUE].value  = 0
    elif rgb_color == RGB_BLUE:
        rgb_led[RGB_RED].value   = 0
        rgb_led[RGB_GREEN].value = 0
        rgb_led[RGB_BLUE].value  = 1
    elif rgb_color == RGB_PURPLE:
        rgb_led[RGB_RED].value   = 1
        rgb_led[RGB_GREEN].value = 0
        rgb_led[RGB_BLUE].value  = 1
    elif rgb_color == RGB_YELLOW:
        rgb_led[RGB_RED].value   = 1
        rgb_led[RGB_GREEN].value = 1
        rgb_led[RGB_BLUE].value  = 0
    elif rgb_color == RGB_TURQUOISE:
        rgb_led[RGB_RED].value   = 0
        rgb_led[RGB_GREEN].value = 1
        rgb_led[RGB_BLUE].value  = 1
    elif rgb_color == RGB_WHITE:
        rgb_led[RGB_RED].value   = 1
        rgb_led[RGB_GREEN].value = 1
        rgb_led[RGB_BLUE].value  = 1
    else:
        rgb_led[RGB_RED].value   = 0
        rgb_led[RGB_GREEN].value = 0
        rgb_led[RGB_BLUE].value  = 0


def connect_to_wifi(network_SSID, network_password, rgb_led):
    if wifi.radio.ipv4_address is None:
        print('connecting to network... %s with password of "%s"' % (network_SSID, network_password)) # Print message
        try:
            wifi.radio.connect(ssid = network_SSID, password = network_password, timeout=20)
        except ConnectionError:
            print("Bad SSID/Password could not connect")
            set_rgb_led(rgb_led, RGB_RED)
            return False
        except:
            print("Error connecting to WiFi: unknown error")
            return False


        if wifi.radio.ipv4_address is None: # If the device is not connected to the WiFi network
            # keep trying until we want to give up
            trycount = 0
            while wifi.radio.ipv4_address is None and trycount < 10:
                trycount += 1 # Increment the timeout

                # Blink the blue LED while we attempt to connect
                set_rgb_led(rgb_led, RGB_BLUE)
                wifi.radio.connect(network_SSID, network_password, timeout = 0.75)
                set_rgb_led(rgb_led, RGB_OFF)

                time.sleep(0.25)

            if wifi.radio.ipv4_address is None: # If the device is not connected to the network
                print('failed to connect to network') # Print message
                set_rgb_led(rgb_led, RGB_RED)
                return False

            print('network config: {IP:%s,GW:%s,SBN:%s,DNS:%s}' % (wifi.radio.ipv4_address,wifi.radio.ipv4_gateway,wifi.radio.ipv4_subnet,wifi.radio.ipv4_dns)) # Print message

            # Turn on the Green LED
            set_rgb_led(rgb_led, RGB_GREEN)
    else:
        print('network already connected') # Print message
        print('network config: {IP:%s,GW:%s,SBN:%s,DNS:%s}' % (wifi.radio.ipv4_address,wifi.radio.ipv4_gateway,wifi.radio.ipv4_subnet,wifi.radio.ipv4_dns)) # Print message

    return True


def create_ntp(pool, rgb_led, ntp_host = "pool.ntp.org"):
    global ntptime
    ntptime = adafruit_ntp.NTP(pool, server=ntp_host, tz_offset=0)
    try:
        rtc.RTC().datetime = ntptime.datetime
        print("Initial timesync done")
    except:
        print("could not get time from server, waiting 3 minutes then rebooting")
        set_rgb_led(rgb_led, RGB_RED)

        time.sleep(180)
        microcontroller.reset()


# routine to reach out to time server and set real time clock, using existing time connection
def update_time_from_ntp():
    try:
        rtc.RTC().datetime = ntptime.datetime
        print("Follow-on timesync done")
    except:
        print("could not get time from server")
        pass      


def get_time(intime = None):
    # we default to current time unless a particular time was passed
    if intime is None: 
        event_date_time = time.localtime()

        ada_datetime =  adafruit_datetime.datetime(
            year=event_date_time.tm_year,
            month=event_date_time.tm_mon, 
            day=event_date_time.tm_mday, 
            hour=event_date_time.tm_hour, 
            minute=event_date_time.tm_min,
            second=event_date_time.tm_sec
        )
    else:
        # time format is "YYYY-MM-DD HH:MM:SS"
        datetimeparts = intime.split(" ") # split date from time
        dateparts = datetimeparts[0].split("-") # chunk the date up
        timeparts = datetimeparts[1].split(":") # chunk the time up

        # need to convert time format into datetime format
        ada_datetime = adafruit_datetime.datetime(
            year=int(dateparts[0]),
            month=int(dateparts[1]), 
            day=int(dateparts[2]), 
            hour=int(timeparts[0]), 
            minute=int(timeparts[1]),
            second=int(timeparts[2])
        )

    return ada_datetime


def get_eventlist(http_req, calendar_url, rgb_led):
    # let python know we want to use the global variable
    global cached_data

    # set LED to blue to show we are accessing the network
    set_rgb_led(rgb_led, RGB_BLUE)
    time.sleep(0.2)    

    # call the helper function that reads Google calendar and returns json list of next 2 weeks of events
    # the helper will include 30 minutes of past events as well to provide overlap in case of reboot during an event
    # so that the OFF action can be caught
    try:
        response = http_req.get(calendar_url, timeout=15)
    except BaseException as err:
        print("Error getting calendar data")
        print(err)
        return cached_data
    except:
        print("Error getting calendar data: Unknown error")
        return cached_data


    # check that we had a successful GET call
    if response.status_code != 200:
        # turn on the red LED
        set_rgb_led(rgb_led, RGB_RED)
    else:
        # update our cached_data, as our internet may go in and out
        cached_data = response.json()

    response.close()
    return cached_data


def find_event_relay(config, event_relay_name, Relays):
    nRelayNumber = -1

    # Run through the relay mappings
    for r_map in config['Relay_Mappings']:
        if event_relay_name == r_map["Name"]: # If the event subject matches the relay mapping name
            nRelayNumber = r_map["Relay_number"]

    return nRelayNumber


def print_calendar(caldata):
    print("-------------- CALENDAR --------------")

    # loop through events and print them out nicely
    for event in caldata:
        # pull time out of the event and format it properly
        event_start = get_time(intime = event["Start"])
        event_end = get_time(intime = event["End"])

        print("%s to %s | %s | %s | %s" % (event_start, event_end, event["Title"], event["Action"], event["ID"]))

def initialize_rgb_led(rgb_led):
    #set pin direction
    for led in rgb_led:
        led.direction = Direction.OUTPUT

    # turn on each color in sequence to provide visual verification
    print("RED")
    set_rgb_led(rgb_led, RGB_RED)
    time.sleep(1)

    print("GREEN")
    set_rgb_led(rgb_led, RGB_GREEN)
    time.sleep(1)

    print("BLUE")
    set_rgb_led(rgb_led, RGB_BLUE)
    time.sleep(1)

    print("ALL")
    set_rgb_led(rgb_led, RGB_WHITE)
    time.sleep(1)

    set_rgb_led(rgb_led, RGB_OFF)


def initialize_relays(config, Relays):
    # loop through full array list and set the correct pin direction, then toggle it on and off as a visual/audio confirmation wired correctly at bootup
    for r_map in config['Relay_Mappings']:
        Relays[r_map["Relay_number"]].direction = Direction.OUTPUT

    for r_map in config['Relay_Mappings']:
        print("%s(%s) CONNECTION TEST" % (r_map["Name"], r_map["Relay_number"]+1))
        Relays[r_map["Relay_number"]].value = True
        time.sleep(0.3)
        Relays[r_map["Relay_number"]].value = False


def set_relays_to_calendar(caldata, Relays, current_time, config):

    # track which relays should be on, assuming they should all be off
    relay_active_events = [False] * len(Relays)

    # inspect all events and record any active event for which relay it is related to.  
    # There may be more than one calendar event/relay at the same time. 
    # There may be overlapping active events for the same relay.
    for event in caldata:
        # pull time out of the event and format it properly
        event_start = get_time(intime = event["Start"])
        event_end = get_time(intime = event["End"])

        # if current time is equal or past the event start time and we are still within the window to perform the task
        if current_time >= event_start and current_time <= event_end:
            # figure out which relay number and if found, record that it should be on
            relay_number = find_event_relay(config, event["Action"], Relays)

            # make sure the calendar event referenced a relay we know about, otherwise we have to skip it
            if relay_number != -1:
                relay_active_events[relay_number] = True

    # now set the relays according to our calculated status
    for i in range(0,len(Relays)):
        if Relays[i].value == True and relay_active_events[i] == False:
            # time to turn a relay off
            print("   turning OFF %s (relay %s)" % (config['Relay_Mappings'][i]["Name"], i+1))
            Relays[i].value = False
        elif Relays[i].value == False and relay_active_events[i] == True:
            # time to turn a relay on
            print("   turning ON %s (relay %s)" % (config['Relay_Mappings'][i]["Name"], i+1))
            Relays[i].value = True


def main():
    # not sure what garbage collection is default, explicitly turning on
    gc.enable()
    
    # set up our LED
    rgb_led = [
        DigitalInOut(board.GP3), # Red LED
        DigitalInOut(board.GP4), # Green LED
        DigitalInOut(board.GP5)  # Blue LED
    ]
    initialize_rgb_led(rgb_led)

    # load configuration
    config = load_config()

    # attempt to connect to WiFi based upon configuration setting
    wifi_connected = connect_to_wifi(config['WiFi_Settings']['SSID'], config['WiFi_Settings']['Password'], rgb_led) 
    if not wifi_connected: 
        print("Could Not Connect to wifi, Waiting 30 minutes then powercycling")
        time.sleep(1800)
        microcontroller.reset()

    # establish our interface to the network
    pool = socketpool.SocketPool(wifi.radio)
    http_req = adafruit_requests.Session(pool, ssl_context=ssl.create_default_context())

    # since no battery in PICO, update the time so we can compare to calendar
    create_ntp(pool, rgb_led, config['WiFi_Settings']['NTP_server'])

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
    initialize_relays(config, Relays)

    # setup our time tracker and initial refresh times
    INTERVAL_CALENDAR_UDPATE = 60 * 1       # check once every 1 minutes
    INTERVAL_TIME_UPDATE = 60 * 60 * 12     # resynch every 12 hours (60 seconds * 60 minutes * 12 hours)
    INTERVAL_BLINK       = 2                # frequency of blinking

    current_time = get_time()
    next_calendar_update = current_time - adafruit_datetime.timedelta(seconds=INTERVAL_CALENDAR_UDPATE) # force an initial load
    next_time_update = current_time + adafruit_datetime.timedelta(seconds=INTERVAL_TIME_UPDATE)
    next_blink_update = current_time + adafruit_datetime.timedelta(seconds=INTERVAL_BLINK)


    # all setup. now we just loop forever doing our tasks
    while True:
        current_time = get_time()
        
        # pico loses time easily, so regularly resync the real time clock (RTC)
        if current_time >= next_time_update:
            update_time_from_ntp()
            next_time_update = current_time + adafruit_datetime.timedelta(seconds=INTERVAL_TIME_UPDATE)

        # refresh our calendar on a schedule
        if current_time >= next_calendar_update:
            caldata = get_eventlist(http_req, config['magic_url'], rgb_led)
            print_calendar(caldata)
            print("current time %s" % (current_time))
            next_calendar_update =  current_time + adafruit_datetime.timedelta(seconds=INTERVAL_CALENDAR_UDPATE)

            # forcing garbage collection each calendar update
            gc.collect()

        # Every loop iteration we process the calendar
        set_relays_to_calendar(caldata, Relays, current_time, config)

        # reboot daily around midnight. Not factoring in DST so this could be 1 am.
        if current_time.hour + config['GMT_offset'] == 0 and current_time.minute < 5:
            # wait 5 minutes to ensure after reboot we don't do this again for 24 hours
            print("------------- time for our daily reboot in 10 minutes. Just chill till then -------------")
            set_rgb_led(rgb_led, RGB_WHITE)
            time.sleep(60*5)
            microcontroller.reset()

        if current_time >= next_blink_update:
            # blink so we know the main program is still running
            set_rgb_led(rgb_led, RGB_OFF)
            time.sleep(0.2)
            set_rgb_led(rgb_led, RGB_GREEN)
            next_blink_update = current_time + adafruit_datetime.timedelta(seconds=INTERVAL_BLINK)


# kick things off         
if __name__ == "__main__":
    main()
