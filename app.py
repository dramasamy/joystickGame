#!/usr/bin/env python
from threading import Lock
import yaml
from flask import Flask
from flask import render_template
from flask import session
from flask import request
from flask import url_for
from flask import escape
from flask import redirect
from flask_socketio import SocketIO
from flask_socketio import emit
from flask_socketio import join_room
from flask_socketio import leave_room
from flask_socketio import close_room
from flask_socketio import rooms
from flask_socketio import disconnect
from flask_login import LoginManager
from flask_login import login_required
from flask_login import UserMixin
from flask_login import login_user
from flask_login import logout_user
from flask_login import current_user
import paho.mqtt.client as mqtt
import redis
import time 
import random
from datetime import timedelta
from influxdb import InfluxDBClient

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = 'threading'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
app.config['TESTING'] = False

socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()

login_manager = LoginManager()
login_manager.init_app(app)

db = redis.Redis(host='localhost')

# seconds
key_validity = 60 

# User session timeout - minute
session_timeout = 1


class User(UserMixin):
    def __init__(self , username , password , id , active=True):
        self.id = id
        self.username = username
        self.password = password
        self.active = active

    def get_id(self):
        return self.id

    def is_active(self):
        return self.active

    def get_auth_token(self):
        return make_secure_token(self.username , key='secret_key')

    def set_username(self, uname):
        self.username = uname 

    def set_password(self, passwd):
        self.password = passwd 

class UsersRepository:

    def __init__(self):
        self.users = dict()
        self.users_id_dict = dict()
        self.identifier = 0

        self.users['admin'] = User('admin' , 'admin' , 1 , active=True)
        self.users_id_dict[1] = User('admin' , 'admin' , 1 , active=True)
    
    def save_user(self , user):
        self.users_id_dict.setdefault(user.id , user)
        self.users.setdefault(user.username , user)
    
    def get_user(self , username):
        return self.users.get(username)
    
    def get_user_by_id(self , userid):
        return self.users_id_dict.get(userid)
    
    def next_index(self):
        self.identifier +=1
        return self.identifier

    def create_user(self, uname, passwd):
        uid = random.randint(1111,9999)
        self.users[uname] = User(uname , passwd , uid , active=True)
        self.users_id_dict[uid] = User(uname , passwd , uid , active=True)


users_repository = UsersRepository()

def on_connect(client, userdata, flags, rc):
    print 'Connected with result code ' + str(rc)

client = mqtt.Client(client_id="tedxClient1", clean_session=False, userdata=None,protocol=4, transport="tcp")
client.on_connect = on_connect
client.connect("test.mosquitto.org", 1883, 60)


def background_thread():
    """Example of how to send server generated events to clients."""
    r = redis.Redis(host='localhost')
    if r.get('signup') == None:
        r.set('signup', 0)
    r.set('activated', 'False')
    r.set('access_code', random.randint(1111,9999))
    socketio.emit('newnumber', {'number': r.get('access_code')}, namespace='/test')
    client = InfluxDBClient('localhost', 8086, 'root', 'root', 'rover')
    while True:
        print 'state of client activation ' + str(r.get('activated'))
        if r.get('activated') == 'False':
            json_body = [
                {
                    "measurement": "access_code",
                    "tags": {
                        "host": "rover1",
                        "region": "npv"
                    },
                    "time": 1234567890000000,
                    "fields": {
                        "countdown": "IDLE",
                        "rover_state": "IDLE",
                        "user_name": "No Active User",
                        "access_code": r.get('access_code'),
                        "battery_level": 80,
                        "client": "http://127.0.0.1:5000"
                    }
                }
            ]
            client.write_points(json_body)
            print 'NotActivated - sleep 2'
            time.sleep(2)
        elif r.get('activated') == 'True':

            json_body = [
                {
                    "measurement": "access_code",
                    "tags": {
                        "host": "rover1",
                        "region": "npv"
                    },
                    "time": 1234567890000000,
                    "fields": {
                        "countdown": str(r.pttl('activated')/1000),
                        "rover_state": "ACTIVE",
                        "user_name": db.get('ctrl_user'),
                        "access_code": "XXXX",
                        "battery_level": 80,
                        "client": "http://127.0.0.1:5000",
                        "signup": int(r.get('signup'))
                    }
                }
            ]
            client.write_points(json_body)
            socketio.emit('newnumber', {'number': 'Rover Connected', 'countdown' : str(r.pttl('activated')/1000), 'user' : db.get('ctrl_user')}, namespace='/test')
            print 'Activated - Connected - sleep 2'
            time.sleep(1)
        elif r.get('activated') == None:
            r.set('access_code', random.randint(1111,9999))
            print 'Expired - Emit - sleep 2'
            socketio.emit('newnumber', {'number': r.get('access_code')}, namespace='/test')
            json_body = [
                {
                    "measurement": "access_code",
                    "tags": {
                        "host": "rover1",
                        "region": "npv"
                    },
                    "time": 1234567890000000,
                    "fields": {
                        "countdown": "IDLE",
                        "rover_state": "IDLE",
                        "user_name": "No Active User",
                        "access_code": r.get('access_code'),
                        "battery_level": 80,
                        "client": "http://127.0.0.1:5000"
                    }
                }
            ]
            client.write_points(json_body)
            r.set('activated', 'False')
            time.sleep(2)
        else:
            print 'No Match - Error'
            time.sleep(2)


@app.route('/joystick')
@login_required
def joystick():
    return render_template('joystick.html', async_mode=socketio.async_mode)

@app.route('/admin')
@login_required
def admin():
    return render_template('admin.html', async_mode=socketio.async_mode)

@app.route('/joy')
def joy():
    return render_template('joy.html', async_mode=socketio.async_mode)

@app.route('/404')
def not_found():
    return render_template('404.html', async_mode=socketio.async_mode)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    db.set('activated', 'False', ex=1)
    return redirect(url_for('login'))


@app.route('/rover')
@login_required
def rover():
    return render_template('robo.html', async_mode=socketio.async_mode)

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if current_user.is_authenticated:
        return redirect(url_for('joystick'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print 'form username ' + username
        print 'form password ' + password
        if username != 'admin':
            users_repository.create_user(username, db.get('access_code'))
            print db.get('access_code')
        registeredUser = users_repository.get_user(username)
        if registeredUser != None and registeredUser.username == 'admin':
            if registeredUser != None and registeredUser.password == password:
                print 'Users '+ str(users_repository.users) 
                print 'Register user %s , password %s' % (registeredUser.username, registeredUser.password) 
                print('Admin Logged in..')
                login_user(registeredUser)
                return redirect(url_for('admin'))
            else:
                error = 'Invalid admin password'
        else:
            # session.permanent = True
            # app.permanent_session_lifetime = timedelta(minutes=session_timeout)
            print 'form username ' + username
            print 'form password ' + password
            if registeredUser != None and registeredUser.password == password :
                print 'Users '+ str(users_repository.users) 
                print 'Register user %s , password %s' % (registeredUser.username, registeredUser.password)
                print('Controller Logged in..')
                login_user(registeredUser)
                db.set('ctrl_user', username)
                db.set('access_code', 'Rover Activated')
                db.set('activated', 'True', ex=key_validity)
                new_user_count = int(db.get('signup')) + 1
                db.set('signup', new_user_count)
                socketio.emit('newnumber', {'number': db.get('access_code')}, namespace='/test')
                return redirect(url_for('joystick'))
            else:
                error = 'Invalid Access Code!'
    return render_template('login.html', error=error)

# callback to reload the user object        
@login_manager.user_loader
def load_user(userid):
    print 'Username ' + str(userid)
    return users_repository.get_user_by_id(userid)

# @app.before_request
# def make_session_permanent():
#     session.permanent = True
#     app.permanent_session_lifetime = timedelta(minutes=1)

# handle login failed
@app.errorhandler(401)
def page_not_found(e):
    return redirect(url_for('login'))

@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for('not_found'))

@socketio.on('my_event', namespace='/test')
def test_message(message):
    print message['data']
    session['receive_count'] = session.get('receive_count', 0) + 1
    client.publish('/test/dinesh/kumar', payload=str(message), qos=0, retain=False)
    socketio.emit('my_response', {'data': message['data']} , namespace='/test')
    #emit('my_response', {'data': message['data'], 'count': session['receive_count']})

@socketio.on('my_broadcast_event', namespace='/test')
def test_broadcast_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']},
         broadcast=True)


@socketio.on('join', namespace='/test')
def join(message):
    join_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})


@socketio.on('leave', namespace='/test')
def leave(message):
    leave_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})


@socketio.on('close_room', namespace='/test')
def close(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response', {'data': 'Room ' + message['room'] + ' is closing.',
                         'count': session['receive_count']},
         room=message['room'])
    close_room(message['room'])


@socketio.on('my_room_event', namespace='/test')
def send_room_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']},
         room=message['room'])


@socketio.on('disconnect_request', namespace='/test')
def disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    disconnect()


@socketio.on('my_ping', namespace='/test')
def ping_pong():
    emit('my_pong')


@socketio.on('connect', namespace='/test')
def test_connect():
    print 'Joystic connected - app'
    emit('my_response', {'data': 'Connected', 'count': 0})
    print 'Admin connected - app'
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread)
    socketio.emit('newnumber', {'number': db.get('access_code')}, namespace='/test')

@socketio.on('newnumber', namespace='/test')
def admin_connect():
    print 'Admin connected - app2'
    socketio.emit('newnumber', {'number': db.get('access_code')}, namespace='/test')


@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected', request.sid)


if __name__ == '__main__':
    socketio.run(app, debug=False)
