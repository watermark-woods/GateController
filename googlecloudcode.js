// Derived from https://github.com/wilda17/ESP8266-Google-Calendar-Arduino/blob/master/calendar.gscript

function doGet() {
    var events = GetEvents();
    Logger.log(events);
    return ContentService.createTextOutput(JSON.stringify(events)).setMimeType(ContentService.MimeType.JSON);
}

function formatReadableDate(nDateTime) {
    var sFormattedDT, dtEvent;
    evtDT = new Date(nDateTime)

    sFormattedDT = evtDT.getFullYear() + "-" + String(evtDT.getMonth()+1).padStart(2, "0") + "-" + String(evtDT.getDate()).padStart(2,"0") + " " + String(evtDT.getHours()).padStart(2, "0") + ":" + String(evtDT.getMinutes()).padStart(2, "0") + ":00";
    return sFormattedDT;
}

function GetEvents() {
    var Cal = CalendarApp.getCalendarsByName('WW-Gate')[0]; // Get the calendar
    var Now = new Date();
    var Later = new Date();
    Later.setDate(Now.getDate() + 14); // Go 2 weeks from now
    var events = Cal.getEvents(Now, Later, {"max": 25}); // Get the events
    var outEvents = new Array();
    var calEvent, relayName, dtStart, dtEnd;
    
    Logger.log(Now.getTime())
    events.forEach(element => {
        // get Relay of event and force all caps for comparisons
        relayName = element.getDescription().toUpperCase();

        // Default Relay to Gate if not specified
        if (relayName=="") {
           relayName = "GATE";
        };
        
        // Create On event with only the required fields based upon calendar Start time, valid for the entire duration
        // less one minute to avoid overlap with the off event
        dtStart = element.getStartTime();
        dtEnd = element.getEndTime();
        dtEnd.setMinutes(dtEnd.getMinutes() - 1);
        calEvent = {
            "Start": formatReadableDate(dtStart),
            "End": formatReadableDate(dtEnd),
            "Action": relayName + " ON",
            "ID": element.getId() + "ON"
        };
        // Add to output array
        outEvents.push(calEvent);
        
        // Create Off event with only the required fields based upon calendar end time, for 15 minutes
        dtStart = element.getEndTime();
        dtEnd = element.getEndTime();
        dtEnd.setMinutes(dtEnd.getMinutes() + 15);
        calEvent = {
            "Start": formatReadableDate(dtStart),
            "End": formatReadableDate(dtEnd),
            "Action": relayName + " OFF",
            "ID": element.getId() + "OFF"
        };
        // Add to output array
        outEvents.push(calEvent);
        
    });
    return outEvents;
}
