# GateController
This repository houses the code for the Watermark Woods gate controller, it is meant to be deployed on a Raspberry Pi Pico W via CircuitPython.
Edit the config.json file with the correct wifi settings, Magic URL, and relay configuration.

Custom Google Apps script must be uploaded to better format calender events for the gate controller to use.
The controller will cache events up-to two weeks in advance.
The controller will respond to each event in turn with the calendar event description triggering an action on the controller.

The Google calendar used by the googlecloudcode.js script must be configured for UTC time.

A calendar event should be in the following format
1. Subject = any event name for logging purposes
2. Description = ```RelayName``` with NO formatting. Must be plain text, no hidden HTML tags.
3. Start = date and time event should turn relay on
4. End = date and time event should turn relay off

So an example calendar event description would be:  
```R2```

The Google Apps Script will default the relay name to GATE if no event description is present. The calendar event title is used for logging in the Python script. The relay names can be customized in the settings file. Relay names must not contain a space, and are case insensitive.

## Installing and running
### Google Cloud
1. In the [google apps script console](https://www.google.com/script/start/), create a new project
2. Copy the contents of the googlecloudcode.js file to the project
3. Update the googlecloudcode.js to reference correct calendar name
4. Save the project
5. Click the depoy button on the top right of the page
6. Click the gear next to select type then choose Web App
7. Leave the Execute as you
8. Change the Who has access dropdown to Anyone
9. Click the deploy button
10. Copy the Web app URL to the magic URL section of the config file.
### Raspberry Pi Pico W
1. Download the lates version of circutpython from [circutpython.org](https://circuitpython.org/board/raspberry_pi_pico_w/).
2. Hold down the BOOTSEL button on the board and power on the board.
3. Drag the uf2 file onto the board.
4. Wait for the board to boot up.
5. Ensure the latest Adafruit libraries for the correct CircuitPython version are installed in /lib for adafruit_datetime, adafruit_ntp, adafruit_requests, and adafruit_connection_manager which can be downloaded at https://circuitpython.org/libraries.
6. Copy the code.py file and the settings file to the filesystem of the Pico W.
7. Update the config.json file with the correct settings.

## Hardware
1. Raspbery Pi PICO W
2. VOGURTIME 5V Relay Module with Optocoupler Isolation Support High and Low Level Trigger Relay Red Board (8 Channel 5V Relay) 
3. RGB LED
