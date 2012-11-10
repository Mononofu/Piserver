from functools import wraps
import commands
import sqlite3
import time
import serial
from flask import Flask, render_template, redirect, Response, request
from contextlib import closing
from remote import Remote
from flask.ext.classy import FlaskView, route

# configuration
DATABASE = '/home/mononofu/web/web.db'
DEBUG = True
SECRET_KET = 'some kasdj234#@#RASf'
USERNAME = 'mononofu'
PASSWORD = 'alucard'

app = Flask(__name__)
app.config.from_object(__name__)


def connect_db():
    return sqlite3.connect(app.config['DATABASE'])


def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()


def check_auth(username, password):
    return username == USERNAME and password == PASSWORD


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


class OverView(FlaskView):
    @requires_auth
    def index(self):
        return render_template('index.html',
            nas_up=(commands.getstatusoutput("fping -c1 -t50 192.168.1.120")[0] == 0))


class NasView(FlaskView):
    @requires_auth
    def wake(self):
        return commands.getoutput("wakeonlan 00:25:22:3B:B1:DA")


class PingView(FlaskView):
    def get(self, id):
        db = connect_db()
        db.execute('insert into pings (hostname, timestamp) values (?, ?)', 
            [id, time.time()])
        db.commit()
        db.close()
        return "ping successful"

    @requires_auth
    def index(self):
        db = connect_db()
        cur = db.execute('select hostname, timestamp from pings order by timestamp')
        pings = [dict(host=row[0], time=row[1]) for row in cur.fetchall()]
        db.close()
        return str(pings)


class ReceiverView(FlaskView):
    @requires_auth
    def index(self):
        with Remote() as r:
            return render_template('receiver.html',
                receiver_on = r.is_on(),
                volume = r.get_volume(),
                device = r.get_device())

    @route('/vol/<lvl>/')
    @requires_auth
    def vol(self, lvl):
        with Remote() as r:
            r.volume(int(lvl))
        time.sleep(0.2)
        return redirect('/receiver')

    @requires_auth
    def get(self, id):
        cmd = id
        with Remote() as r:
            if cmd == "on": r.on()
            elif cmd == "off": r.off()
            elif cmd == "pc": r.select_pc()
            elif cmd == "tv": r.select_tv()
            elif cmd == "pi": r.select_pi()
            elif cmd == "aux": r.select_aux()
            elif cmd == "tuner": r.select_tuner()
            else: return "unknown command %s" % cmd
        time.sleep(0.2)
        return redirect('/receiver')

class ColorView(FlaskView):
  def index(self):
    return render_template('color.html', color=current_color)

  @route("/reset")
  def reset(self):
    global ser
    ser.close()
    time.sleep(1)
    ser = serial.Serial('/dev/ttyACM0', 9600, timeout=0)
    return redirect('/color')


  def get(self, id):
    global current_color
    current_color = id
    red = id[0:2]
    green = id[4:6]
    blue = id[2:4] 

    msg = chr(int(red, 16)) + chr(int(green, 16)) + chr(int(blue, 16))

    try:
      ser.write(msg.replace('\x80', '\x81') + '\x80')
      ser.flush()
      ser.readlines()
    except:
      return "failed to set color"

    return redirect('/color')


OverView.register(app, route_base='/')
NasView.register(app)
ReceiverView.register(app)
PingView.register(app)
ColorView.register(app)

ser = None
current_color = "f00"

if __name__ == "__main__":
    ser = serial.Serial('/dev/ttyACM0', 9600, timeout=0)
    app.run(host='0.0.0.0')
    ser.close()
