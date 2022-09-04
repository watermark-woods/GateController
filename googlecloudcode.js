// Derived from https://github.com/wilda17/ESP8266-Google-Calendar-Arduino/blob/master/calendar.gscript

function doGet() {
    var events = GetEvents();
    Logger.log(events);
    return ContentService.createTextOutput(JSON.stringify(events)).setMimeType(ContentService.MimeType.JSON);
}

function GetEvents() {
    var Cal = CalendarApp.getCalendarsByName('WW-Gate')[0]; // Get the calendar
    var Now = new Date();
    var Later = new Date();
    Later.setSeconds(Now.getSeconds() + 1036800); // Go 2 weeks from now
    var events = Cal.getEvents(Now, Later, {"max": 25}); // Get the events
    var outEvents = new Array();
    var calEvent, relayName;
    
    Logger.log(Now.getTime())
    events.forEach(element => {
        // get Relay of event
        relayName = element.getDescription().toUpperCase();

        // Default Relay to Gate if not specified
        if (relayName=="") {
           relayName = "GATE";
        };
        
        // Create On event with only the required fields based upon calendar Start time, for 15 minutes
        calEvent = {
            "Start": element.getStartTime().getTime(),
            "End": element.getStartTime().getTime() + (60*15),
            "Title": relayName + " ON",
            "ID": element.getId() + "ON"
        };
        // Add to output array
        outEvents.push(calEvent);
        
        // Create Off event with only the required fields based upon calendar Start time, for 15 minutes
        calEvent = {
            "Start": element.getEndTime().getTime(),
            "End": element.getEndTime().getTime() + (60*15),
            "Title": relayName + " OFF",
            "ID": element.getId() + "OFF"
        };
        // Add to output array
        outEvents.push(calEvent);
        
    });
    return outEvents;
}
