function changeEnd()
{
    document.getElementById("to").min = document.getElementById("from").value;
}

function refreshElapsed(startTime, element)
{
    // get total seconds elapsed
    var secs = Math.round((new Date().getTime() / 1000) - startTime);
    // update view
    $(element).text(daysComponent(secs) + " days, " + hoursComponent(secs) + " hours, " + minutesComponent(secs) + " minutes, " + secondsComponent(secs) + " seconds");

    setTimeout(function(){refreshElapsed(startTime, element)}, 1000);
}

function refreshCountdown(endTime, element)
{
    // get total seconds remaining
    var secs = Math.round(endTime - (new Date().getTime() / 1000));
    if (secs <= 0)
    {
        // delay by one second otherwise it might reload the page slightly too early for the database time
        setTimeout(function(){location.reload(true)}, 1000);
    }
    // update view
    $(element).text(daysComponent(secs) + " days, " + hoursComponent(secs) + " hours, " + minutesComponent(secs) + " minutes, " + secondsComponent(secs) + " seconds");

    setTimeout(function(){refreshCountdown(endTime, element)}, 1000);
}

function refreshFuelBurned(startTime, rate, element)
{
    // get total hours elapsed
    var hours = (Math.round((new Date().getTime() / 1000) - startTime) / 3600.0);
    // update view with fuel burned by multiplying hours elapsed times fuel burn rate
    $(element).text((hours * rate).toFixed(1));

    setTimeout(function(){refreshFuelBurned(startTime, rate, element)}, 1000);
}

function refreshFuelRemaining(startTime, rate, capacity, element)
{
    // get total hours elapsed
    var hours = (Math.round((new Date().getTime() / 1000) - startTime) / 3600.0);
    // update view with remaining fuel, could be negative if the rocket ran out of fuel!
    $(element).text((capacity - (hours * rate)).toFixed(1));

    setTimeout(function(){refreshFuelRemaining(startTime, rate, capacity, element)}, 1000);
}

function daysComponent(seconds)
{
    return Math.floor(seconds / 86400);
}

function hoursComponent(seconds)
{
    return Math.floor((seconds % 86400) / 3600);
}

function minutesComponent(seconds)
{
    return Math.floor(((seconds % 86400) % 3600) / 60);
}

function secondsComponent(seconds)
{
    return Math.floor(((seconds % 86400) % 3600) % 60);
}