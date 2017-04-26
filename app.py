from flask import Flask, render_template, redirect, request, url_for
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import re
import math

dbPath = 'db.sqlite3'

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
app.config["SECRET_KEY"] = "secret"

@app.route("/")
def index():
    """Serves up the home page."""
    if not current_user.is_authenticated:
        #render home page without computing information to pass to it since the anonymous user won't be able to that info
        return render_template("index.html")
    else:
        #get rows of mission data to display on home page for authenticated user
        previousMissionRows = DBgetRealTimeMissionInfo("previous")
        currentMissionsRows = DBgetRealTimeMissionInfo("current")
        nextMissionRows = DBgetRealTimeMissionInfo("next")

        #give the results some nicely formatted headers instead of displaying the internal DB attribute names
        previousMissionHeaders=("Rocket", "Fuel Burned", "Fuel Remaining", "Launch Facility", "Landing Time", "Crew Members")
        currentMissionHeaders=("Rocket", "Fuel Burned", "Fuel Remaining", "Launch Facility", "Elapsed Mission Time", "Remaining Mission Time", "Crew Members")
        nextMissionHeaders=("Rocket", "Fuel Required", "Fuel To Spare", "Launch Facility", "Launch Time", "Countdown To Launch", "Crew Members")

        #render home page and pass it all the information it needs to construct the page
        return render_template("index.html", pHeaders=previousMissionHeaders, pRows=previousMissionRows, cHeaders=currentMissionHeaders, cRows=currentMissionsRows, nHeaders=nextMissionHeaders, nRows=nextMissionRows)

@app.route("/missions", methods=["GET", "POST"])
@login_required
def showMissions():
    """Serves up the missions page"""
    #open database connection
    conn = sqlite3.connect(dbPath)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    closestFacility = ""
    
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
        if request.form["action"] == 'Add Mission':
            #in this case we know the add new mission form was submitted so add mission to database
            missionValues = (request.form["rid"], request.form["fid"], request.form["launchTime"], request.form["landTime"])
            c.execute("INSERT INTO Mission (rid, fid, launchTime, landTime) VALUES (?, ?, ?, ?)", missionValues)
            #make a list of pairs of the mission id we just created with each crew member's id
            astroValues = zip((c.lastrowid,) * len(request.form.getlist("crewMembers")), request.form.getlist("crewMembers"))
            #add row in crew table for each one of these pairs
            c.executemany("INSERT INTO Crew (mid, aid) VALUES (?, ?)", astroValues)
        elif request.form["action"] == 'Use Nearest Facility':
            # find nearest base
            baseLat  = request.form["latitude"]
            baseLong = request.form["longitude"]
            baseFloatLat  = getFloatFromLatlong( baseLat )
            baseFloatLong = getFloatFromLatlong( baseLong )
            closestDistance = float("inf")
            for record in c.execute("SELECT fid, lat, long FROM LaunchFacility"):
                currentFloatLat  = getFloatFromLatlong( record['lat'] )
                currentFloatLong = getFloatFromLatlong( record['long'] )
                latdiff  = baseFloatLat  - currentFloatLat
                longdiff = baseFloatLong - currentFloatLong
                currentDistance = math.sqrt( latdiff*latdiff + longdiff*longdiff )
                if currentDistance < closestDistance:
                    closestDistance = currentDistance
                    closestFacility = record['fid']

    #Done handling http POST request. In either a GET or a POST, we now need to gather the data to render the page
    
    #queries that populate html table of missions to be rendered
    #note that || in SQLite means concatenation
    c.execute("SELECT M.mid, M.mid IN (SELECT M1.mid FROM Mission M1 WHERE strftime('%s', M1.launchTime) < strftime('%s', datetime('now'))) AS cannotDelete, R.rname, F.name, M.launchTime, M.landTime, group_concat(A.firstName || ' ' || A.lastName, '<br/>') AS anames FROM Mission M, Rockets R, LaunchFacility F, Crew C, Astronauts A WHERE M.rid = R.rid AND M.fid = F.fid AND M.mid = C.mid AND C.aid = A.aid GROUP BY C.mid ORDER BY M.launchTime DESC;")
    results = c.fetchall()

    #queries that populate rockets, facilities, and astronauts for the 'add new mission' form
    c.execute("SELECT rid, rname || ' (Capacity: ' || cast(crewCapacity as text) || ')' FROM Rockets")
    rockets = c.fetchall()
    c.execute("SELECT fid, name FROM LaunchFacility")
    facilities = c.fetchall()
    c.execute("SELECT aid, firstName || ' ' || lastName FROM Astronauts")
    astronauts = c.fetchall()

    #Query that finds if any astronaut is scheduled for overlapping missions
    c.execute("SELECT A.aid, 1, A.firstName, A.lastName, group_concat(M1.mid || ' and ' || M2.mid) as overlappingMissions FROM Astronauts A, Mission M1, Mission M2, Crew C1, Crew C2 WHERE C1.aid = A.aid AND C2.aid = A.aid AND C1.mid = M1.mid AND C2.mid = M2.mid AND M1.mid <> M2.mid AND strftime('%s', M1.launchTime) < strftime('%s', M2.launchTime) AND strftime('%s', M1.landTime) > strftime('%s', M2.landTime);")
    overlap = c.fetchall()

    #close database connection
    conn.commit()
    conn.close()
    
    #each list within the following list represents a form element we want to render and contains (form element name, type, label to display for it, and extra values if needed like to send list of astronauts to select multiple type)
    formInputs = [['rid', 'select', 'Rocket', rockets], ['fid', 'select', 'Launch Facility', facilities], ['crewMembers', 'selectmultiple', 'Crew Members', astronauts], ['launchTime', 'datetime', 'Launch Time', ["from",]], ['landTime', 'datetime', 'Land Time', ["to",]]]

    return render_template("missions.html", headers=("Rocket","Facility","Time of Launch", "Time of Landing", "Crew Members"), rows=results, inputs=formInputs, headersOverlap=("Firstname", "Lastname", "Overlapping Missions"), rowsOverlap=overlap, closestFacility=closestFacility)

def getFloatFromLatlong( latlongString ):
    matchLatlong  = re.match('(\d+\.\d+)_([NSEW])', latlongString)
    return float( matchLatlong.group(1) ) * \
                  (-1.0 if re.match('[SW]', matchLatlong.group(2)) else 1.0)
    
@app.route("/launch_facilities", methods=["GET", "POST"])
@login_required
def showFacilities():
    """Serves up the launch facilities page. See the similar showMissions function for more comments"""
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
    """Serves up the rockets page. See the similar showMissions function for more comments"""
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
    
    c.execute("SELECT R.rid, 1, R.rname, A.firstName, A.lastName, SUM((strftime('%s', m.landTime) - strftime('%s', m.launchTime))/3600.0) as timeHours FROM Rockets R, Astronauts A, Mission M, Crew C WHERE A.aid=C.aid AND C.mid=M.mid AND R.rid=M.rid GROUP BY R.rname, A.firstName HAVING timeHours > (SELECT SUM((strftime('%s', m1.landTime) - strftime('%s', m1.launchTime))/3600.0) FROM Rockets R1, Astronauts A1, Mission M1, Crew C1 WHERE A1.aid=C1.aid AND C1.mid=M1.mid AND R1.rid=M1.rid AND A.aid <> A1.aid AND R1.rid = R.rid);")
    experiencedAstros = c.fetchall()

    formInputs = [['rname', 'text', 'Rocket Name', []], ['thrust', 'number', 'Thrust', []], ['vendor', 'text', 'Vendor', []], ['fuelTankSize', 'number', 'Fuel Tank Size', []], ['fuelBurnRate', 'number', 'Fuel Burn Rate', []], ['crewCapacity', 'number', 'Crew Capacity', []]]

    conn.commit()
    conn.close()
    
    return render_template("rockets.html", headers=("Rocket Name","Thrust","Vendor","Fuel Tank Size","Fuel Burn Rate", "Crew Capacity"), rows=results, inputs=formInputs, headersAstro=("Rocket Name", "First Name", "Last Name", "Hours Flown"), rowsAstro=experiencedAstros)
   
@app.route("/astronauts", methods=["GET", "POST"])
@login_required
def showAstronauts():
    """Serves up the astronauts page. See the similar showMissions function for more comments"""
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

    #Query to find which rocket each astronaut has flown on
    c.execute("SELECT A.aid, 1, A.firstName, A.lastName, group_concat(DISTINCT R.rname) as Rockets FROM Astronauts A, Crew C, Mission M, Rockets R WHERE A.aid = C.aid AND C.mid = M.mid AND R.rid = M.rid GROUP BY A.firstName, A.lastName ORDER BY COUNT(DISTINCT R.rname) DESC;")
    astroHistory = c.fetchall()
    
    formInputs = [['firstName', 'text', 'First Name', []], ['lastName', 'text', 'Last Name', []], ['dob', 'date', 'Date of Birth', []]]
    
    conn.commit()
    conn.close()
    
    return render_template("astronauts.html", headers=("First Name","Last Name","Date of Birth","Hours Flown"), rows=results, inputs=formInputs, historyHeader=("Firstname", "Lastname", "Rockets Flown On"), historyRows=astroHistory)

@app.route("/astronauts/<aid>")
@login_required
def showAstronautInfo(aid):
    """Serves up the astronaut info page."""
    #open DB
    conn = sqlite3.connect(dbPath)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
   
    #this is just to pass the astronaut's name to display in the page title
    c.execute("SELECT firstName, lastName, dob FROM Astronauts WHERE aid = ?", (aid,))
    results = c.fetchone()

    conn.commit()
    conn.close()

    #render page passing name and also the dictionary of interesting astronaut information returned by DBgetAstronautStatsDictionary()
    return render_template("astronaut_info.html", first=results["firstName"], last=results["lastName"], info=DBgetAstronautStatsDictionary(aid))

@app.route("/users")
@login_required
def showUsers():
    """Serves up the website user list page."""
    conn = sqlite3.connect(dbPath)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT U.uid, 0 AS cannotDelete, U.username, U.firstName, U.lastName, P.pname, U.lastLoginTime FROM Users U, Permissions P WHERE U.pid = P.pid;")
    results = c.fetchall()
    
    conn.commit()
    conn.close()

    return render_template("users.html", headers=("Username","First Name","Last Name", "Permission Level", "Last Login Time"), rows=results)

@app.route("/login", methods=["GET", "POST"])
def showLogin():
    """Serves up the login page."""
    #if the logged in user somehow tries to access this page, redirect
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    userNotFound=""
    wrongPassword=""
    if request.method == "POST":
        #user has submitted their login information, get the DB record matching the username provided, if it exists
        userRecord = DBgetUser(request.form["username"])
        if userRecord:
            #if user with the provided username exists in DB, create User object for that user
            #note that the true parameter tells constructor the password we're giving it is already hashed, since it came from DB
            user = User(userRecord["username"], userRecord["password"], True)
            #check password
            if user.check_password(request.form["password"]):
                #set User object permission based on permission for this user found in database
                # user.permission = userRecord["pid"]
                user.authenticated = True
                #login user to flask_login session
                login_user(user)
                current_user.permission = userRecord["pid"]
                print(current_user.permission)
                #record a login event for this user in the DB, which updates their last login time
                DBloginUser(user.id)
                #user is now logged in, redirect to home page
                return redirect(url_for("index"))
            else:
                wrongPassword="Pasword is incorrect"
        else:
            userNotFound="User doesn't exist"

    #this information will be used by the Jinja to render login form
    formInputs = [['username', 'text', 'Username', []], ['password', 'password', 'Password', []]]
    return render_template("login.html", inputs=formInputs, userNotFound=userNotFound, wrongPassword=wrongPassword)
       
@app.route("/signup", methods=["GET", "POST"])
def showSignup():
    """Serves up the signup page."""
    #a logged in user shouldn't see the signup page, redirect to home page
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    UserNameAlreadyExists = ""
    if request.method == "POST":
        #user has submitted signup form, check if the username they entered is already taken
        if DBgetUser(request.form["username"]):
            UserNameAlreadyExists = "Username already exists, try again"
        else:
            #the user should not be able to get to this point if logged in, but log out just in case
            logout_user()
            #creates user object, the false parameter indicates password being passed in is unhashed
            user = User(request.form["username"], request.form["password"], False)
            # user.permission = request.form["permission"]
            user.authenticated = True
            #login user to flask_login session
            login_user(user)
            #add user record to DB
            DBaddUser(request.form["firstName"], request.form["lastName"], request.form["username"], user.pw_hash, user.permission)
            #record a login event with DB which updates user's last login time
            DBloginUser(request.form["username"])
            return redirect(url_for("index"))

    #information that Jinja will use to generate the login form when rendering the page
    conn = sqlite3.connect(dbPath)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT pid, pname FROM Permissions WHERE pid <> 1")
    permissions = c.fetchall()
    conn.commit()
    conn.close()
    formInputs = [['firstName', 'text', 'First Name', []], ['lastName', 'text', 'Last Name', []], ['username', 'text', 'Username', []], ['password', 'password', 'Password', []], ['permission', 'radio', 'Permission Level', permissions]]
    return render_template("signup.html", inputs=formInputs, UserNameAlreadyExists=UserNameAlreadyExists)

@app.route("/logout")
def showLogout():
    """Serves up the logout page."""
    #logged out user shouldn't be able to see this page, redirect
    if not current_user.is_authenticated:
        return redirect(url_for("index"))
    #logout of flask_login session
    logout_user()
    return render_template("logout.html")

class User(UserMixin):
    """My user class which inherits from UserMixin provided by flask_login"""
    def __init__(self, username, password, isPasswordHashedAlready):
        """Creates a User object with the provided username and password.
        Bool isPasswordHashedAlready indicates if the provided password needs to be hashed and salted
        (as in when the user is registering) or not (as in if we are loading user information from database
        where password is already hashed and salted)."""

        self.id = username
        if isPasswordHashedAlready:
            self.pw_hash = password
        else:
            self.set_password(password)
        #by default the minimum permission a registered user can have is 2 (read only)
        self.permission = 2

    def set_password(self, password):
        self.pw_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.pw_hash, password)

@login_manager.user_loader
def load_user(username):
    """Required by flask_login to return a User object given a username"""
    userRecord = DBgetUser(username)

    if userRecord:
        user = User(userRecord["username"], userRecord["password"], True)
        user.permission = userRecord["pid"]

        return user

    return None

def DBgetUser(username):
    """Given a username, return SQL row of that user from DB if it exists"""
    conn = sqlite3.connect(dbPath)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * from Users WHERE username = ?", (username,))
    userRecord = c.fetchone()

    conn.close()

    return userRecord

def DBaddUser(firstname, lastname, username, password, permission):
    """Adds user record to DB"""
    conn = sqlite3.connect(dbPath)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("INSERT INTO Users (firstName, lastName, username, password, pid, regTime) VALUES (?, ?, ?, ?, ?, datetime('now'))", (firstname, lastname, username, password, permission))
    conn.commit()
    conn.close()

def DBloginUser(username):
    """Updates last login time in the DB for the user with the provided username"""
    conn = sqlite3.connect(dbPath)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("UPDATE Users SET lastLoginTime = datetime('now') WHERE username = ?", (username,))
    conn.commit()
    conn.close()

def DBgetRealTimeMissionInfo(pointInTime):
    """Returns information about the most recent mission, next scheduled mission, or current missions in progress"""
    conn = sqlite3.connect(dbPath)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if pointInTime == "previous":
        #this will select the most recently completed mission
        c.execute("SELECT M.mid, R.rname, round(R.fuelBurnRate*((strftime('%s',M.landTime) - strftime('%s',M.launchTime))/3600.0),1) AS fuelBurned, round(R.fuelTankSize-(R.fuelBurnRate*((strftime('%s',M.landTime) - strftime('%s',M.launchTime))/3600.0)),1) AS fuelRemaining, F.name, M.landTime, group_concat(A.firstName || ' ' || A.lastName, '<br/>') AS anames FROM Mission M, Rockets R, LaunchFacility F, Crew C, Astronauts A WHERE M.rid = R.rid AND M.fid = F.fid AND M.mid = C.mid AND C.aid = A.aid AND strftime('%s',M.landTime) < strftime('%s',datetime('now')) GROUP BY C.mid ORDER BY M.landTime DESC LIMIT 1;")
        result = c.fetchall()
    elif pointInTime == "current":
        #this will select the currently in progress missions
        c.execute("SELECT M.mid, R.rname, R.fuelBurnRate AS fuelBurnRateLive, R.fuelTankSize AS fuelTankSizeLive, F.name, strftime('%s',M.launchTime) AS launchTimeLive, strftime('%s',M.landTime) AS landTimeLive, group_concat(A.firstName || ' ' || A.lastName, '<br/>') AS anames FROM Mission M, Rockets R, LaunchFacility F, Crew C, Astronauts A WHERE M.rid = R.rid AND M.fid = F.fid AND M.mid = C.mid AND C.aid = A.aid AND launchTimeLive <= strftime('%s',datetime('now')) AND landTimeLive > strftime('%s',datetime('now')) GROUP BY C.mid ORDER BY M.launchTime DESC;")
        result = c.fetchall()
    elif pointInTime == "next":
        #this will select the next scheduled mission
        c.execute("SELECT M.mid, R.rname, R.fuelBurnRate*((strftime('%s',M.landTime) - strftime('%s',M.launchTime))/3600.0) AS fuelRequired, R.fuelTankSize-(R.fuelBurnRate*((strftime('%s',M.landTime) - strftime('%s',M.launchTime))/3600.0)) AS fuelToSpare, F.name, M.launchTime, strftime('%s',M.launchTime) AS countdownToLaunchLive, group_concat(A.firstName || ' ' || A.lastName, '<br/>') AS anames FROM Mission M, Rockets R, LaunchFacility F, Crew C, Astronauts A WHERE M.rid = R.rid AND M.fid = F.fid AND M.mid = C.mid AND C.aid = A.aid AND strftime('%s',M.launchTime) > strftime('%s',datetime('now')) GROUP BY C.mid ORDER BY M.landTime ASC LIMIT 1;")
        result = c.fetchall()
    conn.commit()
    conn.close()
    return result

def DBgetAstronautStatsDictionary(aid):
    """Returns a dictionary of interesting astronaut information"""
    conn = sqlite3.connect(dbPath)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    d = {}

    #name and age
    c.execute("SELECT *, cast(strftime('%Y.%m%d', 'now') - strftime('%Y.%m%d', dob) as int) AS age FROM Astronauts WHERE aid = ?;", (aid,))
    result = c.fetchone()
    d["Name"] = result["firstName"] + " " + result["lastName"]
    d["Age"] = result["age"]

    #number of unique crew members flown with
    c.execute("SELECT count(DISTINCT C1.aid) as c FROM Crew C1 WHERE C1.aid <> ? AND C1.mid IN (SELECT C2.mid FROM Crew C2 WHERE C2.aid = ?);", (aid,aid))
    result = c.fetchone()
    d["Number of Unique Crewmates"] = result["c"]

    #years of experience
    c.execute("SELECT strftime('%Y','now') - strftime('%Y',min(M.launchTime)) AS yearsOfExperience FROM Astronauts A, Mission M, Crew C WHERE A.aid = ? AND A.aid = C.aid AND C.mid = M.mid;", (aid,))
    #Taking the max will ensure that if the astronaut is only assigned to missions in future years, their years of experience will not be negative.
    d["Years of Experience"] = max(0, c.fetchone()["yearsOfExperience"])

    #year when they flew the highest number of their overall missions
    c.execute("SELECT strftime('%Y',M1.launchTime) AS year, count(M1.mid) AS numMissions FROM Astronauts A1, Mission M1, Crew C1 WHERE A1.aid = ? AND A1.aid = C1.aid AND C1.mid = M1.mid GROUP BY year ORDER BY numMissions DESC LIMIT 1;", (aid,))
    result = c.fetchone()
    d["Year With Their Highest Number of Missions"] = str(result["year"]) + " (" + str(result["numMissions"]) + " missions flown)"
    
    conn.commit()
    conn.close()
    
    return d

if __name__ == "__main__":
    app.run()
        
