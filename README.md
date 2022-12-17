# GateController
This repository houses the code for the Watermark Woods gate controller, it is meant to be deployed on a Raspberry Pi Pico W via CircuitPython.
Edit the config.json file with the correct wifi settings, Magic URL, and relay configuration.

Custom Google Apps script must be uploaded to better format calender events for the gate controller to use.
The controller will cache events up-to two weeks in advance.
The controller will respond to each event in turn with the calendar event description triggering an action on the controller.

A calendar event should be in the following format
Subject = any event name for logging purposes
Description = ```TriggerName```
Start = date and time event should turn relay on
End = date and time event should turn relay off

So a example would be:  
```R8```

The Google Apps Script will default the relay name to GATE if a name not provided.

The calendar event title is used for logging in the python script. The calendar event start and stop times are used to create two events for the python script. The first event is the ON event, which starts at the calendar event time and goes until the end of the calendar event LESS one minute. The second event created is an OFF event, which starts when the calendar event ends and goes for 15 minutes.

The relay names can be customized in the settings file. Relay names must not contain a space.

## Installing and running
### Google Cloud
1. In the [google apps script console](https://www.google.com/script/start/), create a new project
2. Copy the contents of the googlecloudcode.js file to the project
3. Save the project
4. Click the depoy button on the top right of the page
5. Click the gear next to select type then choose Web App
6. Leave the Execute as you
7. Change the Who has access dropdown to Anyone
8. Click the deploy button
9. Copy the Web app URL to the magic link section of the config file.
### Raspberry Pi Pico W
1. Download the lates version of circutpython from [circutpython.org](https://circuitpython.org/board/raspberry_pi_pico_w/).
2. Hold down the BOOTSEL button on the board and power on the board.
3. Drag the uf2 file onto the board.
4. Wait for the board to boot up.
5. Ensure the latest Adafruit libraries for the correct CircuitPython version are installed in /lib for adafruit_datetime, adafruit_ntp, and adafruit_requests.
6. Copy the code.py file and the settings file to the filesystem of the Pico W.
7. Update the config.json file with the correct settings.
