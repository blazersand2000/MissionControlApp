from flask import Flask, render_template, redirect, request, url_for
import sqlite3

dbPath = 'db.sqlite3'

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/missions", methods=["GET", "POST"])
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
    c.execute("SELECT M.mid, 0 AS cannotDelete, R.rname, F.name, M.launchTime, M.landTime, group_concat(A.firstName || ' ' || A.lastName, '<br/>') AS anames FROM Mission M, Rockets R, LaunchFacility F, Crew C, Astronauts A WHERE M.rid = R.rid AND M.fid = F.fid AND M.mid = C.mid AND C.aid = A.aid GROUP BY C.mid;")
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
       
if __name__ == "__main__":
    app.run()
        
