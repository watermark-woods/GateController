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
    var outevents = new Array();
    Logger.log(Now.getTime())
    events.forEach(element => {
        // Create Event with only the required fields
        calevent = {
            "End": element.getEndTime().getTime(),
            "Start": element.getStartTime().getTime(),
            "Title": element.getTitle(),
            "ID": element.getId()
        };
        // Add to output array
        outevents.push(calevent);
    });
    return outevents;
}