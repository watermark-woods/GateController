import json, wifi, board, time, adafruit_ntp, socketpool, adafruit_datetime, adafruit_requests, rtc, ssl, microcontroller
import gc
from digitalio import DigitalInOut, Direction

# declare global variables
cached_data = ""   # used as a backup if we can't later access the calendar

# simple loading of the configuration
def load_config():
    with open('config.json') as f: # Open the config.json file
        conf = json.load(f) # Load the config.json file
    return conf


def connect_to_wifi(network_SSID, network_password, rgb_led):
    if wifi.radio.ipv4_address is None:
        print('connecting to network... %s with password of "%s"' % (network_SSID, network_password)) # Print message
        try:
            wifi.radio.connect(ssid = network_SSID, password = network_password, timeout=20)
        except ConnectionError:
            print("Bad SSID/Password could not connect")
            rgb_led[0].value = 1
            return False

        if wifi.radio.ipv4_address is None: # If the device is not connected to the WiFi network
            # keep trying until we want to give up
            trycount = 0
            while wifi.radio.ipv4_address is None and trycount < 10:
                trycount += 1 # Increment the timeout

                # Blink the blue LED every half second
                rgb_led[2].value = 1
                wifi.radio.connect(network_SSID, network_password, timeout = 0.75)
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
    else:
        print('network already connected') # Print message
        print('network config: {IP:%s,GW:%s,SBN:%s,DNS:%s}' % (wifi.radio.ipv4_address,wifi.radio.ipv4_gateway,wifi.radio.ipv4_subnet,wifi.radio.ipv4_dns)) # Print message

    return True


def create_ntp(pool, ntp_host = "pool.ntp.org"):
    global ntptime
    ntptime = adafruit_ntp.NTP(pool, server=ntp_host, tz_offset=0)
    try:
        rtc.RTC().datetime = ntptime.datetime
        print("Initial timesync done")
    except:
        print("could not get time from server, waiting 3 minutes then rebooting")
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

    gc.collect()
    print('-----------------------------')
    print('Free: {} Allocated: {}'.format(gc.mem_free(), gc.mem_alloc()))
    print('-----------------------------')


    # call the helper function that reads Google calendar and returns json list of next 2 weeks of events
    # the helper will include 30 minutes of past events as well to provide overlap in case of reboot during an event
    # so that the OFF action can be caught
    try:
        response = http_req.get(calendar_url, timeout=15)
    except BaseException as err:
        print("Error getting calendar data")
        print(err)
        return cached_data

    # check that we had a successful GET call
    if response.status_code != 200:
        # turn on the red LED
        rgb_led[0].value = 1
        rgb_led[1].value = 0
        rgb_led[2].value = 0
    else:
        # blink the blue LED for 2 tenths of a second and turn off the red LED
        rgb_led[0].value = 0
        rgb_led[1].value = 0
        rgb_led[2].value = 1
        time.sleep(0.2)
        rgb_led[1].value = 1
        rgb_led[2].value = 0

        # update our cached_data, as our internet may go in and out
        cached_data = response.json()

    response.close()
    return cached_data


def check_handled_event(currentEvent, already_used):
    #iterate through the already used list and report back if found

    for event in already_used:
        if event["ID"] == currentEvent["ID"]:
            return True

    return False


#remove excess already_Used events
def cleanup_already_used(already_used):
    print("Cleanup on aisle 5, cleaning past events out of list (%s)" % (len(already_used)))

    # keep events around for a period of time after their ending. Google is slow to drop past events off list
    history_retention = get_time() + adafruit_datetime.timedelta(hours=2)

    # to properly remove items in the array while iterating it at same time, we need to delete backwards so indexes don't get messed up
    # create a range starting at end accounting for base 0 index, decrementing by 1, and stopping when we get out of array range
    # example for array of 4 items the range would yield (3, 2, 1, 0)
    for i in range(len(already_used) -1, -1, -1):
        # see if retention time is already passed end of end of event
        if history_retention > get_time(intime = already_used[i]["End"]):
            print("    Removing " + already_used[i]["ID"] + ", Its time has past")
            del already_used[i]  #remove the i entry completely


# locates correct relay for event and triggers it on or off depending on calendar command
def trigger_relay(config, evtsubject, Relays):
    # keep track if we found the relay in the configuration settings
    bRelayFound = False

    # Run through the relay mappings
    for r_map in config['Relay_Mappings']:
        if evtsubject[0] == r_map["Name"]: # If the event subject matches the relay mapping name
            # mark that we found the relay finally
            bRelayFound = True
            print("        " + evtsubject[0] + " " + evtsubject[1])

            # set relay state based on action
            if evtsubject[1] == "ON":
                Relays[r_map["Relay_number"]].value = 1
            elif evtsubject[1] == "OFF":
                Relays[r_map["Relay_number"]].value = 0
            else:
                # means command used on the relay doesn't match what we expect
                print("        action %s is unknown. Use either ON or OFF for relay" % (evtsubject[1]))

            # no reason to keep looking
            break

    # if we didn't find the relay, report that out
    if not bRelayFound:
        print("        relay " + evtsubject[0] + " not found in configuration")


def print_calendar(caldata, already_used):
    print("-------------- START CALENDAR --------------")

    # loop through events and print them out nicely
    for event in caldata:
        # pull time out of the event and format it properly
        event_start = get_time(intime = event["Start"])
        event_end = get_time(intime = event["End"])

        print("%s | %s to %s | %s | %s | %s" % (str(check_handled_event(event, already_used)), event_start, event_end, event["Title"], event["Action"], event["ID"]))

    print("--------------  END CALENDAR  --------------")


def main():
    # print out how much memory we are starting with
    gc.collect()
    print('-----------------------------')
    print('Free: {} Allocated: {}'.format(gc.mem_free(), gc.mem_alloc()))
    print('-----------------------------')

    # set up our LED
    rgb_led = [
        DigitalInOut(board.GP3), # Red LED
        DigitalInOut(board.GP4), # Green LED
        DigitalInOut(board.GP5)  # Blue LED
    ]
    for led in rgb_led:
        led.direction = Direction.OUTPUT

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
    create_ntp(pool, config['WiFi_Settings']['NTP_server'])

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
    for r_map in config['Relay_Mappings']:
        Relays[r_map["Relay_number"]].direction = Direction.OUTPUT
        Relays[r_map["Relay_number"]].value = r_map["Initial_state"]

    # setup our time tracker and initial refresh times
    INTERVAL_CALENDAR_UDPATE = 60 * 2       # check once every 2 minutes
    INTERVAL_TIME_UPDATE = 60 * 60 * 12     # resynch every 12 hours 60 seconds * 60 minutes * 12 hours
    INTERVAL_ALREADY_USED_CLEANUP = 60 * 60 # check hourly 60 seconds * 60 minutes

    current_time = get_time()
    next_calendar_update = current_time + adafruit_datetime.timedelta(seconds=INTERVAL_CALENDAR_UDPATE)
    next_time_update = current_time + adafruit_datetime.timedelta(seconds=INTERVAL_TIME_UPDATE)
    next_already_used_cleanup = current_time + adafruit_datetime.timedelta(seconds=INTERVAL_ALREADY_USED_CLEANUP)

    # keep a list of all the events we've processed
    already_used = []

    print("Performing first retrieval")
    caldata = get_eventlist(http_req, config['magic_url'], rgb_led)
    print_calendar(caldata, already_used)

    # all setup. now we just loop forever doing our tasks
    while True:
        current_time = get_time()
        print("current time %s" % (current_time))

        # pico loses time easily, so regularly resync the real time clock (RTC)
        if current_time >= next_time_update:
            update_time_from_ntp()

            # schecule the next time update
            next_time_update = current_time + adafruit_datetime.timedelta(seconds=INTERVAL_TIME_UPDATE)

        # we clean up past events on a schedule
        if current_time >= next_already_used_cleanup:
            cleanup_already_used(already_used)

            # schedule the next cleanup event
            next_already_used_cleanup = current_time + adafruit_datetime.timedelta(seconds=INTERVAL_ALREADY_USED_CLEANUP)

        # we check the calendar on a schedule
        if current_time >= next_calendar_update:
            print("Performing Calander Update")
            caldata = get_eventlist(http_req, config['magic_url'], rgb_led)
            print_calendar(caldata, already_used)

            # schedule the next calendar refresh
            next_calendar_update =  current_time + adafruit_datetime.timedelta(seconds=INTERVAL_CALENDAR_UDPATE)

        # inspect all events and handle any that are due. There may be more than one calendar event/relay at the same time
        for event in caldata:
            # make sure we haven't already handled this event
            if check_handled_event(event, already_used):
                print("    skipping event(" + event["ID"] + "). already handled")
            else:
                # pull time out of the event and format it properly
                event_start = get_time(intime = event["Start"])
                event_end = get_time(intime = event["End"])

                # if event hasn't been handled, but it has also passed, we can skip it. Possible on new calendar entries or reboot
                if  current_time > event_end:
                    # record it so we can skip on future passes
                    already_used.append(event)

                    print("too late for %s" % event["ID"])

                # if current time is equal or past the event start time and we are still within the window to perform the task
                elif current_time >= event_start :
                    print("    Working on event: %s, with action of '%s', and start at %s" % (event["ID"],event["Action"],event_start))

                    # record it so we can skip on future passes
                    already_used.append(event)

                    # Split the event action into an array of exactly 2 dimensions with a space of divider. 
                    # format should be <relay name> <action>
                    # ex: "GATE ON" from Google Apps Script
                    # and in calendar the event description should just be "GATE" or whatever relay name from config
                    # problems if the calendar event has more than one word on description, which should just be relay name
                    # relay names cannot have a space in them

                    evtsubject = event["Action"].split(" ")
                    if len(evtsubject) != 2:
                        print("    event lacks proper relay and action from calendar helper function")
                    else:
                        # Run through the relay mappings
                        trigger_relay(config, evtsubject, Relays)

                # last condition possible musbe be it just isn't time for the event yet
                else:
                    print("    too early for %s" % event["ID"])

        # I'm wondering if we should set a time period for a daily/weekly reboot
        # if internet connection is lost, I don't see how program reestablishes internet/time server connection again in future
        # downside though is anything cached on the calendar would be lost on reboot

        # reboot daily. since time is in UTC and gate located on east coast it is mainly -5, will plan for 1AM if DST is on, and mindnight if it isnt
        # will limit reboot check for first 15 minutes of the hour
        if current_time.hour == 5 and current_time.minute < 15 and False:   #FORCE THIS NOT TO RUN
            # wait 16 minutes to ensure after reboot we don't do this again for 24 hours
            print("------------- time for our daily reboot in 16 minutes. Just chill till then -------------")
            time.sleep(60*16)
            microcontroller.reset()

        # always take a break between loop iterations
        time.sleep(30)


# kick things off         
if __name__ == "__main__":
    main()
