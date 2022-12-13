// Derived from https://github.com/wilda17/ESP8266-Google-Calendar-Arduino/blob/master/calendar.gscript

function doGet() {
    var events = GetEvents();
    Logger.log(events);
    return ContentService.createTextOutput(JSON.stringify(events)).setMimeType(ContentService.MimeType.JSON);
}

function formatReadableDate(nDateTime) {
    var sFormattedDT, dtEvent;
    evtDT = new Date(nDateTime)

    sFormattedDT = evtDT.getUTCFullYear() + "-" + String(evtDT.getUTCMonth()+1).padStart(2, "0") + "-" + String(evtDT.getUTCDate()).padStart(2,"0") + " " + String(evtDT.getUTCHours()).padStart(2, "0") + ":" + String(evtDT.getUTCMinutes()).padStart(2, "0") + ":00";
    return sFormattedDT;
}

function GetEvents() {
    var Cal = CalendarApp.getCalendarsByName('WW-Gate')[0]; // Get the calendar
    var Now = new Date();
    var Later = new Date();

    Now.setMinutes(Now.getMinutes() - 30) // pull events from 30 minutes in past to ensure overlap for STOP actions
    Later.setDate(Now.getDate() + 14); // Go 2 weeks from now
    var events = Cal.getEvents(Now, Later, {"max": 25}); // Get the events
    var outEvents = new Array();
    var calEvent, relayName, dtStart, dtEnd;

    // print out validation we are using UTC time
    Logger.log("Window is " + Now.getUTCFullYear() +"-"+ (Now.getUTCMonth()+1) +"-"+ Now.getUTCDate() +" "+ Now.getUTCHours() +":"+ Now.getUTCMinutes() 
              + " through " + Later.getUTCFullYear() +"-"+ (Later.getUTCMonth()+1) +"-"+ Later.getUTCDate() +" "+ Later.getUTCHours() +":"+ Later.getUTCMinutes());

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
            "Title": element.getTitle(),
            "Action": relayName + " ON",
            "ID": element.getId() + "ON"
        };
        // Add to output array
        outEvents.push(calEvent);
        
        // Create Off event with only the required fields based upon calendar end time, for 15 minutes for cushion
        dtStart = element.getEndTime();
        dtEnd = element.getEndTime();
        dtEnd.setMinutes(dtEnd.getMinutes() + 15);
        calEvent = {
            "Start": formatReadableDate(dtStart),
            "End": formatReadableDate(dtEnd),
            "Title": element.getTitle(),
            "Action": relayName + " OFF",
            "ID": element.getId() + "OFF"
        };
        // Add to output array
        outEvents.push(calEvent);
        
    });

    // print to application log what the result is, one event per line
    Logger.log("Start | End | Title | Action | ID");
    outEvents.forEach(element => {
      Logger.log(element["Start"] + " | " + element["End"] + " | " + element["Title"] + " | " + element["Action"] + " | " + element["ID"]);
    });

    return outEvents;
}
