import paho.mqtt.client as mqtt
import Adafruit_PCA9685
import time
import ast

pwm = Adafruit_PCA9685.PCA9685()

# Set frequency to 60hz, good for servos.
pwm.set_pwm_freq(60)

tilt_start = 104 ; # 0 Degree 
tilt_mid = 400 ; # 90 
tilt_end = 521 ; # 180
tilt_val = tilt_mid

tilt_channel = 1 
base_channel = 0

base_start = 104 ; # 0 Degree 
base_mid = 312 ; # 90 
base_end = 521 ; # 180 
base_val = base_mid

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print "Connected with result code " + str(rc)

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("topic/direction")

    pwm.set_pwm(tilt_channel, 0, 312)
    pwm.set_pwm(base_channel, 0, 312)

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global tilt_start
    global tilt_mid
    global tilt_end
    global tilt_val
    global tilt_channel
    global base_channel
    global base_start
    global base_mid
    global base_end
    global base_val
    global pwm

    print msg.payload
    print base_val
    print msg.topic + " " + str(msg.payload)
    msg.payload = ast.literal_eval(msg.payload)
    if msg.payload['data'] == 'E':
        if base_val >= base_start:
            base_val =  base_val - 5 
            pwm.set_pwm(base_channel, 0, base_val)
    elif msg.payload['data'] == 'W':
        if base_val <= base_end:
            base_val =  base_val + 5 
            pwm.set_pwm(base_channel, 0, base_val)
    elif msg.payload['data'] == 'N':
        if tilt_val <= tilt_end:
            tilt_val =  tilt_val + 5 
            pwm.set_pwm(tilt_channel, 0, tilt_val)
    elif msg.payload['data'] == 'S':
        if tilt_val >= tilt_start:
            tilt_val =  tilt_val - 5 
            pwm.set_pwm(tilt_channel, 0, tilt_val)
    elif msg.payload['data'] == 'onMouseUp':
        pwm.set_pwm(tilt_channel, 0, tilt_mid)
        pwm.set_pwm(base_channel, 0, base_mid)
        tilt_val = tilt_mid
        base_val = base_mid

client = mqtt.Client(client_id="nokia_saves_life", clean_session=False, userdata=None,protocol=4, transport="tcp")
client.on_connect = on_connect
client.on_message = on_message
client.connect("192.168.1.100", 1883, 60)

client.loop_forever()













# NOTE: 
# 	if using this program with a servo, be sure to keep the frequency between 40 - 60 and 
# 	the pulse width between 150 - 600. Otherwise, you may strip gears or burnout your servo.
# 	A little math for using a 12 bit PWM controller might help...

# 	If we take 2 to the 12th power, we get 4096. In non-math terms that means our controlling 
# 	device has a resolution, granularity or can separate things down to 4096 separate units. 
# 	Hold that thought for now.

# 	Robotic and RC type servos are nothing more than regular motors with special control 
# 	circuitry accessed by a 3rd pin that responds to a certain type of signal. A 'typical' 
# 	servo requires a continuous signal with a High pulse width of:

# 	.5 msec every 20 msec to position at 0 degrees (fully ccw)
# 	1.5 msec every 20 msec to position at 90 degrees (neutral)
# 	2.5 msec every 20 msec to position at 180 degrees (fully cw)

# 	This has become somewhat of a defacto standard, with most servos requiring something 
# 	close to these signal specifications.

# 	With the above information in mind, whatever program we use needs a couple things 
# 	from us. First it needs a frequency that results in a 20 msec cycle time by using 
# 	the formula 1 / Cycle Time = Frequency. So, 1 divided by .020 results in 50 Hz, 
# 	which is one input needed by our program.

# 	Next lets divide our 20 msec cycle by 4096 units, and we get 4.8 usec per unit.
# 	Now we can divide the pulse widths needed by a typical servo by the resolution of 
# 	our controlling device.

# 	.5 ms / 4.8 usec = 104 the number required by our program to position the servo at 0 degrees
# 	1.5 msec / 4.8 usec = 312 the number required by our program to position the servo at 90 degrees
# 	2.5 msec / 4.8 usec = 521 the number required by our program to position the servo at 180 degrees

# 	This quick test uses Adafruits PWM class from their Adafruit_PWM_Servo_Driver module to 
# 	manually control the position of 2 standard servos. In this case, 104 = full CW and 521 = 
# 	full CCW. 



