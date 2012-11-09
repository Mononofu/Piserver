from functools import wraps
import commands
import sqlite3
import time
from flask import Flask, render_template, redirect, Response, request
from contextlib import closing
from remote import Remote

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
    """This function is called to check if a username /
    password combination is valid.
    """
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

@app.route("/")
@requires_auth
def hello():
    return render_template('index.html', 
        nas_up = commands.getstatusoutput("fping -c1 -t50 192.168.1.120")[0] == 0)

@app.route("/wake/nas")
@requires_auth
def wake_nas():
    return commands.getoutput("wakeonlan 00:25:22:3B:B1:DA")

@app.route("/ping/<host>")
def receive_ping(host):
    db = connect_db()
    db.execute('insert into pings (hostname, timestamp) values (?, ?)', 
        [host, time.time()])
    db.commit()
    db.close()
    return "ping successful"

@app.route("/list_pings")
@requires_auth
def list_pings():
    db = connect_db()
    cur = db.execute('select hostname, timestamp from pings order by timestamp')
    pings = [dict(host=row[0], time=row[1]) for row in cur.fetchall()]
    db.close()
    return str(pings)    

@app.route("/receiver")
@requires_auth
def receiver():
    with Remote() as r:
        return render_template('receiver.html',
            receiver_on = r.is_on(),
            volume = r.get_volume(),
            device = r.get_device())

@app.route("/receiver/vol/<lvl>")
@requires_auth
def receiver_set_vol(lvl):
    with Remote() as r:
        r.volume(int(lvl))
    time.sleep(0.2)
    return redirect('/receiver')

@app.route("/receiver/<cmd>")
@requires_auth
def receiver_on(cmd):
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

@app.route("/cam")
@requires_auth
def cam():
    return render_template('cam.html')

@app.route("/cam/now.jpeg")
@requires_auth
def cam_now():
    #commands.getstatusoutput("fswebcam --save cam.jpg -S 20")
    f = open("/media/ramdisk/cam.jpg", "rb")
    content = f.read()
    f.close()
    return Response(content, mimetype="image/jpeg")

if __name__ == "__main__":
    app.run(host='0.0.0.0')
