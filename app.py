from flask import Flask, render_template, redirect, request, url_for
import sqlite3

#conn = sqlite3.connect('db.sqlite3')
#conn.row_factory = sqlite3.Row
#c = conn.cursor()

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/missions")
def showMissions():
    conn = sqlite3.connect('db.sqlite3')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM Mission")
    results = c.fetchall()

    return render_template("missions.html", headers=("Mission ID","Rocket ID","Facility ID","Time of Launch"), rows=results)
    
    conn.commit()
    conn.close()

@app.route("/launch_facilities")
def showFacilities():
    conn = sqlite3.connect('db.sqlite3')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM LaunchFacility")
    results = c.fetchall()

    return render_template("facilities.html", headers=("Facility ID","Location"), rows=results)
    
    conn.commit()
    conn.close()

@app.route("/rockets")
def showRockets():
    conn = sqlite3.connect('db.sqlite3')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM Rockets")
    results = c.fetchall()

    return render_template("rockets.html", headers=("Rocket ID","Thrust","Vendor","Fuel Tank Size","Fuel Burn Rate"), rows=results)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    app.run()
        
# conn.commit()
# conn.close()