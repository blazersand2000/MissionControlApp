function changeEnd() {
    document.getElementById("to").min = document.getElementById("from").value;
}

function refreshDashboard() {
    $("#dynamic").load("../templates/dashboard.html", function() {
        alert("Hello! I am an alert box!!");
        setTimeout(refreshDashboard, 1000);
    });
}