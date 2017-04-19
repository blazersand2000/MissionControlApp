from flask import Flask, render_template, redirect, request, url_for
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
import sqlite3

dbPath = 'db.sqlite3'

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
app.config["SECRET_KEY"] = "secret"

@app.route("/")
def index():
    if not current_user.is_authenticated:
        return render_template("index.html")
    else:
        previousMissionRows = DBgetRealTimeMissionInfo("previous")
        currentMissionsRows = DBgetRealTimeMissionInfo("current")
        nextMissionRows = DBgetRealTimeMissionInfo("next")

        previousMissionHeaders=("Rocket", "Fuel Burned", "Fuel Remaining", "Launch Facility", "Landing Time", "Crew Members")
        currentMissionHeaders=("Rocket", "Fuel Burned", "Fuel Remaining", "Launch Facility", "Elapsed Mission Time", "Crew Members")
        nextMissionHeaders=("Rocket", "Fuel Required", "Fuel To Spare", "Launch Facility", "Launch Time", "Crew Members")

        return render_template("index.html", pHeaders=previousMissionHeaders, pRows=previousMissionRows, cHeaders=currentMissionHeaders, cRows=currentMissionsRows, nHeaders=nextMissionHeaders, nRows=nextMissionRows)

@app.route("/missions", methods=["GET", "POST"])
@login_required
def showMissions():
    #open database connection
    conn = sqlite3.connect(dbPath)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    if request.method == "POST":
        #determine which form was sent
        for key in request.form:
            if key.startswith('delete.'):
                #we know the form to delete a row was submitted and the name of the delete button is "delete.<id>"
                id = key.split('.')[1]
                #delete mission from database, commit results, and reload the page
                c.execute("DELETE FROM Mission WHERE mid = ?", (id,))
                c.execute("DELETE FROM Crew WHERE mid = ?", (id,))
                conn.commit()
                return redirect(url_for("showMissions"))
        if request.form["launchTime"]:
            #in this case we know the add new mission form was submitted, add mission to database
            missionValues = (request.form["rid"], request.form["fid"], request.form["launchTime"], request.form["landTime"])
            c.execute("INSERT INTO Mission (rid, fid, launchTime, landTime) VALUES (?, ?, ?, ?)", missionValues)
            #make a list of pairs of the mission id we just created with each crew member's id
            astroValues = zip((c.lastrowid,) * len(request.form.getlist("crewMembers")), request.form.getlist("crewMembers"))
            #add row in crew table for each one of these pairs
            c.executemany("INSERT INTO Crew (mid, aid) VALUES (?, ?)", astroValues)

    #Done handling http POST request. In either a GET or a POST, we now need to gather the data to render the page
    
    #queries that populate html table of missions to be rendered
    #note that || in SQLite means concatenation
    c.execute("SELECT M.mid, M.mid IN (SELECT M1.mid FROM Mission M1 WHERE M1.launchTime < datetime('now')) AS cannotDelete, R.rname, F.name, M.launchTime, M.landTime, group_concat(A.firstName || ' ' || A.lastName, '<br/>') AS anames FROM Mission M, Rockets R, LaunchFacility F, Crew C, Astronauts A WHERE M.rid = R.rid AND M.fid = F.fid AND M.mid = C.mid AND C.aid = A.aid GROUP BY C.mid;")
    results = c.fetchall()

    #queries that populate rockets, facilities, and astronauts for the 'add new mission' form
    c.execute("SELECT rid, rname || ' (Capacity: ' || cast(crewCapacity as text) || ')' FROM Rockets")
    rockets = c.fetchall()
    c.execute("SELECT fid, name FROM LaunchFacility")
    facilities = c.fetchall()
    c.execute("SELECT aid, firstName || ' ' || lastName FROM Astronauts")
    astronauts = c.fetchall()
    
    #close database connection
    conn.commit()
    conn.close()
    
    #each list within the following list represents a form element we want to render and contains (form element name, type, label to display for it, and extra values if needed like to send list of astronauts to select multiple type)
    formInputs = [['rid', 'select', 'Rocket', rockets], ['fid', 'select', 'Launch Facility', facilities], ['crewMembers', 'selectmultiple', 'Crew Members', astronauts], ['launchTime', 'datetime', 'Launch Time', ["from",]], ['landTime', 'datetime', 'Land Time', ["to",]]]

    return render_template("missions.html", headers=("Rocket","Facility","Time of Launch", "Time of Landing", "Crew Members"), rows=results, inputs=formInputs)
    
@app.route("/launch_facilities", methods=["GET", "POST"])
@login_required
def showFacilities():
    conn = sqlite3.connect(dbPath)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    if request.method == "POST":
        for key in request.form:
            if key.startswith('delete.'):
                id = key.split('.')[1]
                c.execute("DELETE FROM LaunchFacility WHERE fid = ?", (id,))
                conn.commit()
                return redirect(url_for("showFacilities"))
        if request.form["numPads"]:
            userValues = (request.form["name"], request.form["numPads"], request.form["location"], request.form["lat"], request.form["long"])
            c.execute("INSERT INTO LaunchFacility (name, numPads, location, lat, long) VALUES (?, ?, ?, ?, ?)", userValues)
    
    c.execute("SELECT fid, fid IN (SELECT fid FROM Mission) AS cannotDelete, name, numPads, location, lat, long FROM LaunchFacility")
    results = c.fetchall()
    
    conn.commit()
    conn.close()
    
    formInputs = [['name', 'text', 'Facility Name', []], ['numPads', 'number', 'Num. Launch Pads', []], ['location', 'text', 'Location', []], ['lat', 'text', 'Latitude', []], ['long', 'text', 'Longitude', []]]
    
    return render_template("facilities.html", headers=("Name","Num. Launch Pads","Location","Latitude","Longitude"), rows=results, inputs=formInputs)
    

@app.route("/rockets", methods=["GET", "POST"])
@login_required
def showRockets():
    conn = sqlite3.connect(dbPath)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    if request.method == "POST":
        for key in request.form:
            if key.startswith('delete.'):
                id = key.split('.')[1]
                c.execute("DELETE FROM Rockets WHERE rid = ?", (id,))
                conn.commit()
                return redirect(url_for("showRockets"))
        if request.form["thrust"]:
            userValues = (request.form["rname"], request.form["thrust"], request.form["vendor"], request.form["fuelTankSize"], request.form["fuelBurnRate"], request.form["crewCapacity"])
            c.execute("INSERT INTO Rockets (rname, thrust, vendor, fuelTankSize, fuelBurnRate, crewCapacity) VALUES (?, ?, ?, ?, ?, ?)", userValues)
   
    c.execute("SELECT rid, rid IN (SELECT rid FROM Mission) AS cannotDelete, rname, thrust, vendor, fuelTankSize, fuelBurnRate, crewCapacity FROM Rockets")
    results = c.fetchall()
    
    formInputs = [['rname', 'text', 'Rocket Name', []], ['thrust', 'number', 'Thrust', []], ['vendor', 'text', 'Vendor', []], ['fuelTankSize', 'number', 'Fuel Tank Size', []], ['fuelBurnRate', 'number', 'Fuel Burn Rate', []], ['crewCapacity', 'number', 'Crew Capacity', []]]
    
    conn.commit()
    conn.close()
    
    return render_template("rockets.html", headers=("Rocket Name","Thrust","Vendor","Fuel Tank Size","Fuel Burn Rate", "Crew Capacity"), rows=results, inputs=formInputs)
       
@app.route("/astronauts", methods=["GET", "POST"])
@login_required
def showAstronauts():
    conn = sqlite3.connect(dbPath)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    if request.method == "POST":
        for key in request.form:
            if key.startswith('delete.'):
                id = key.split('.')[1]
                c.execute("DELETE FROM Astronauts WHERE aid = ?", (id,))
                conn.commit()
                return redirect(url_for("showAstronauts"))
        if request.form["dob"]:
            userValues = (request.form["firstName"], request.form["lastName"], request.form["dob"])
            c.execute("INSERT INTO Astronauts (firstName, lastName, dob) VALUES (?, ?, ?)", userValues)
   
    c.execute("SELECT aid, A.aid IN (SELECT aid FROM Crew) AS cannotDelete, firstName, lastName, dob, (SELECT SUM((strftime('%s',M.landTime) - strftime('%s',M.launchTime))/3600.0) FROM Mission M, Crew C WHERE M.mid = C.mid AND C.aid = A.aid) AS hoursFlown FROM Astronauts A")
    results = c.fetchall()
    
    formInputs = [['firstName', 'text', 'First Name', []], ['lastName', 'text', 'Last Name', []], ['dob', 'date', 'Date of Birth', []]]
    
    conn.commit()
    conn.close()
    
    return render_template("astronauts.html", headers=("First Name","Last Name","Date of Birth","Hours Flown"), rows=results, inputs=formInputs)

@app.route("/login", methods=["GET", "POST"])
def showLogin():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    userNotFound=""
    wrongPassword=""
    if request.method == "POST":
        userRecord = DBgetUser(request.form["username"])
        if userRecord:
            if request.form["password"] == userRecord["password"]:
                user = User(userRecord["username"], userRecord["password"])
                user.authenticated = True
                login_user(user)
                return redirect(url_for("index"))
            else:
                print("wrong password")
                wrongPassword="Pasword is incorrect"
        else:
            print("user not found")
            userNotFound="User doesn't exist"

    formInputs = [['username', 'text', 'Username', []], ['password', 'password', 'Password', []]]
    return render_template("login.html", inputs=formInputs, userNotFound=userNotFound, wrongPassword=wrongPassword)
       
@app.route("/signup", methods=["GET", "POST"])
def showSignup():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    UserNameAlreadyExists = ""
    if request.method == "POST":
        if DBgetUser(request.form["username"]):
            UserNameAlreadyExists = "Username already exists, try again"
        else:
            logout_user()
            DBaddUser(request.form["firstName"], request.form["lastName"], request.form["username"], request.form["password"])
            DBloginUser(request.form["username"])
            user = User(request.form["username"], request.form["password"])
            user.authenticated = True
            login_user(user)
            return redirect(url_for("index"))

    formInputs = [['firstName', 'text', 'First Name', []], ['lastName', 'text', 'Last Name', []], ['username', 'text', 'Username', []], ['password', 'password', 'Password', []]]
    return render_template("signup.html", inputs=formInputs, UserNameAlreadyExists=UserNameAlreadyExists)

@app.route("/logout")
def showLogout():
    if not current_user.is_authenticated:
        return redirect(url_for("index"))
    logout_user()
    return render_template("logout.html")

class User(UserMixin):

    def __init__(self, username, password):
        self.id = username
        self.password = password

@login_manager.user_loader
def load_user(username):
    userRecord = DBgetUser(username)

    if userRecord:
        return User(userRecord["username"], userRecord["password"])

    return None

def DBgetUser(username):
    conn = sqlite3.connect(dbPath)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * from Users WHERE username = ?", (username,))
    userRecord = c.fetchone()

    conn.close()

    return userRecord

def DBaddUser(firstname, lastname, username, password):
    conn = sqlite3.connect(dbPath)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("INSERT INTO Users (firstName, lastName, username, password, regTime) VALUES (?, ?, ?, ?, datetime('now'))", (firstname, lastname, username, password))
    conn.commit()
    conn.close()

def DBloginUser(username):
    conn = sqlite3.connect(dbPath)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("UPDATE Users SET lastLoginTime = datetime('now') WHERE username = ?", (username,))
    conn.commit()
    conn.close()

def DBgetRealTimeMissionInfo(when):
    conn = sqlite3.connect(dbPath)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if when == "previous":
        #this will select the most recently completed mission
        c.execute("SELECT R.rname, R.fuelBurnRate*((strftime('%s',M.landTime) - strftime('%s',M.launchTime))/3600.0) AS fuelBurned, R.fuelTankSize-(R.fuelBurnRate*((strftime('%s',M.landTime) - strftime('%s',M.launchTime))/3600.0)) AS fuelRemaining, F.name, M.landTime, group_concat(A.firstName || ' ' || A.lastName, '<br/>') AS anames FROM Mission M, Rockets R, LaunchFacility F, Crew C, Astronauts A WHERE M.rid = R.rid AND M.fid = F.fid AND M.mid = C.mid AND C.aid = A.aid AND M.landTime < datetime('now') GROUP BY C.mid ORDER BY M.landTime DESC LIMIT 1;")
        result = c.fetchall()
    elif when == "current":
        #this will select the currently in progress missions
        c.execute("SELECT M.mid, R.rname, R.fuelBurnRate*((strftime('%s',datetime('now')) - strftime('%s',M.launchTime))/3600.0) AS fuelBurnedLive, R.fuelTankSize-(R.fuelBurnRate*((strftime('%s',datetime('now')) - strftime('%s',M.launchTime))/3600.0)) AS fuelRemainingLive, F.name, strftime('%s',M.launchTime) AS launchTimeLive, group_concat(A.firstName || ' ' || A.lastName, '<br/>') AS anames FROM Mission M, Rockets R, LaunchFacility F, Crew C, Astronauts A WHERE M.rid = R.rid AND M.fid = F.fid AND M.mid = C.mid AND C.aid = A.aid AND M.launchTime <= datetime('now') AND M.landTime > datetime('now') GROUP BY C.mid ORDER BY M.launchTime;")
        result = c.fetchall()
    elif when == "next":
        #this will select the next scheduled mission
        c.execute("SELECT R.rname, R.fuelBurnRate*((strftime('%s',M.landTime) - strftime('%s',M.launchTime))/3600.0) AS fuelRequired, R.fuelTankSize-(R.fuelBurnRate*((strftime('%s',M.landTime) - strftime('%s',M.launchTime))/3600.0)) AS fuelToSpare, F.name, M.launchTime, group_concat(A.firstName || ' ' || A.lastName, '<br/>') AS anames FROM Mission M, Rockets R, LaunchFacility F, Crew C, Astronauts A WHERE M.rid = R.rid AND M.fid = F.fid AND M.mid = C.mid AND C.aid = A.aid AND M.launchTime > datetime('now') GROUP BY C.mid ORDER BY M.landTime ASC LIMIT 1;")
        result = c.fetchall()
    conn.commit()
    conn.close()
    return result

if __name__ == "__main__":
    app.run()
        
