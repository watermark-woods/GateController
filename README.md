# GateController
This repository houses the code for the watermark woods gate controller, it is ment to be deployed on a Raspberry Pi Pico W via micropython.
edit the config.yaml file with the correct wifi settings, Magic URL, and Special Names

Custom google apps scripts must be uploaded to better format calender events for the gate controller to use.
The controller will cache events up-to two weeks in advance.
The controller will respond to each event intern with the subject being the key to triggering an action on the controller.

A event should be in the following format  
```TriggerName TriggerValue```

So a example would be:  
```R8 On```

Theses names can be customized in the settings file.

## Installing and running
### Google Cloud
1. In the google apps script console, create a new project
2. Copy the contents of the googlecloudcode.js file to the project
3. Save the project
4. Click the depoy button on the top right of the page
5. Click the gear next to select type then choose Web App
6. Leave the Execute as you
7. Change the Who has access dropdown to Anyone
8. Click the deploy button
9. Copy the Web app URL to the magic link section of the config file.
### Raspberry Pi Pico W
1. Download the lates version of micropython from [micropython.org](https://micropython.org/download/rp2-pico-w/).
2. Hold down the BOOTSEL button on the board and power on the board.
3. Drag the uf2 file onto the board.
4. Wait for the board to boot up.
5. Copy the code.py file and the settings file to the filesystem of the Pico W.
6. Update the config.json file with the correct settings.