# GateController
This repository houses the code for the watermark woods gate controller, it is ment to be deployed on a Raspberry Pi Pico W via micropython.
edit the config.yaml file with the correct wifi settings, Magic URL, and Special Names

Custom google code must be uploaded to better format calender events for the gate controller to use.
The controller will respond to each event intern with the subject being the key to triggering an action on the controller.

A event should be in the following format  
```TriggerName TriggerValue```

So a example would be:  
```R8 On```

Theses names can be customized in the settings file.

## Installing and running
To run this code copy the code.py file and the settings file to the filesystem of the Pico W.