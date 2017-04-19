function changeEnd() {
    document.getElementById("to").min = document.getElementById("from").value;
}

function refreshFuelBurned(launchTime, rate, size, element) {
    $(element).load("../templates/dashboard.html", function() {
        alert("Hello! I am an alert box!!");
        setTimeout(refreshFuelBurned, 1000);
    });
}

function refreshElapsed(launchTime, element) {
    // get total seconds elapsed
    var totalSecondsElapsed = Math.round((new Date().getTime() / 1000) - launchTime);
    // get whole days elapsed
    var days = Math.floor(totalSecondsElapsed / 86400);
    // total seconds elapsed is now remaining seconds
    totalSecondsElapsed = totalSecondsElapsed % 86400;
    // get whole hours elapsed
    var hours = Math.floor(totalSecondsElapsed / 3600);
    // total seconds elapsed is now remaining seconds
    totalSecondsElapsed = totalSecondsElapsed % 3600;
    // get whole minutes elapsed
    var minutes = Math.floor(totalSecondsElapsed / 60);
    // total seconds elapsed is now remaining seconds
    totalSecondsElapsed = totalSecondsElapsed % 60;
    // update view
    $(element).text(days + " days, " + hours + " hours, " + minutes + " minutes, " + totalSecondsElapsed + " seconds");

    setTimeout(function(){refreshElapsed(launchTime, element)}, 1000);
}