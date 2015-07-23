# all the imports
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
from contextlib import closing
import dill
import pandas as pd
import numpy as np
import datetime
import urllib2
from bs4 import BeautifulSoup

global rm,gm
rm = dill.load( open( "mta_redmodel2.p", "rb" ) )
gm = dill.load( open( "mta_greenmodel2.p", "rb" ) )

# configuration
DATABASE = '/tmp/flaskr.db'
DEBUG = False
SECRET_KEY = 'flaskrtest'
USERNAME = 'admin'
PASSWORD = 'admin'

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

@app.route('/')
def show_entries():

    red = ['Chambers St', '14 St', '34 St - Penn Station', 'Times Sq - 42 St', '72 St', '96 St']
    green = ['Brooklyn Bridge - City Hall', '14 St - Union Sq', 'Grand Central - 42 St', '59 St', '86 St', '125 St']

    return render_template('index.html', red=red, green=green)

@app.route('/model')
def model():
    return render_template('model.html')

@app.route('/add', methods=['POST'])
def add_entry():
    if request.method == 'POST':
        url = 'http://web.mta.info/status/serviceStatus.txt'
        raw_page = urllib2.urlopen(url).read()

        soup = BeautifulSoup(raw_page)
        lines = soup.find('subway').select('line')
        start = request.form['start']
        stop = request.form['stop']
        t = datetime.datetime.now()
        day = t.weekday()
        hour = t.hour
        
        red = ['Chambers St', '14 St', '34 St - Penn Station', 'Times Sq - 42 St', '72 St', '96 St']
        green = ['Brooklyn Bridge - City Hall', '14 St - Union Sq', 'Grand Central - 42 St', '59 St', '86 St', '125 St']
        
        if start in red and stop in red:
            l = [1,2,3]
            stops = red
            model = rm
            stat  = '123'
        
        elif start in green and stop in green:
            l = [6,5,4]
            stops = green
            model = gm
            stat = '456'
        else:
            flash("Are you sure you are on the right line?")
            return redirect(url_for('show_entries'))
        
        cstart = stops.index(start)
        cstop = stops.index(stop)
        
        if start == stop:
            flash("Are you sure you are going somewhere?")
            return redirect(url_for('show_entries'))

        for x in lines:
            if x.find('name').text == stat:
                status = x.find('status').text
                if status == 'PLANNED WORK':
                    flash( "Check the status! There's planned work!" )
                    return redirect(url_for('show_entries'))
                elif status == 'SERVICE CHANGE':
                    flash( "Check the status! There's a service change!" )
                    return redirect(url_for('show_entries'))
                elif status == 'DELAYS':
                    flash( "Take what you can get, there's a delay right now." )
                    return redirect(url_for('show_entries'))
                else:


                    local = model.predict([l[0],cstart,cstop,day,hour])
                    exp1 = model.predict([l[1],cstart,cstop,day,hour])
                    exp2 = model.predict([l[2],cstart,cstop,day,hour])
                    
                    answer = round(float(local - min( exp1, exp2) ), 1)
                    if exp1 > exp2:
                        fast = "   The fastest train is the "+str(l[1])+" train."
                    else:
                        fast = "   The fastest train is the "+str(l[2])+" train."
                    
                    intro = "From "+start+" to "+stop+":\n"
                    wait = " Take the local unless the next express train is less than "+ str(answer) + " minutes away.\n"
                    # time = " ("+ str((datetime.datetime.now() - t).total_seconds()) + " seconds to process)"
                    message = intro+wait+fast#+time
                    flash( message )
                    return redirect(url_for('show_entries'))
    else:
        flash('nothing happend')
        return redirect(url_for('show_entries'))


if __name__ == '__main__':
    app.run(host='0.0.0.0')