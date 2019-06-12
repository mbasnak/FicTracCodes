from __future__ import print_function
from datetime import datetime, timedelta
import asyncio
import redis
import json
import time
import math
import numpy as np
from Phidget22.Devices.VoltageOutput import VoltageOutput
import Phidget22.PhidgetException
import Phidget22.Phidget
import random


class FicTracAout90deg(object):
    """
            Output fly heading, posx, posy into 0 to 10 V



        """

    DefaultParam = {
        'rate_to_volt_const': 50,
        'aout_channel_yaw': 0,
        'aout_channel_x': 1,
        'aout_channel_yaw_gain': 2,
        'aout_channel_y': 3,
        'aout_max_volt': 10.0,
        'aout_min_volt': 0.0,
        'aout_max_volt_vel': 10.0,
        'aout_min_volt_vel': -10.0,
        'lowpass_cutoff': 0.5,
    }

    def __init__(self, param=DefaultParam):

        self.param = param
        self.time_start = time.time()
        self.heading_rate_calc = AngleRateCalc(self.time_start, 0.0)
        self.rate_lowpass = LowpassFilter(0.0, cutoff_freq=self.param['lowpass_cutoff'])


        # Beginning values (to keep track of accumulated heading)
        self.accum_heading = 0
        self.accum_x = 0
        self.accum_y = 0

        # Setup redis subscriber
        self.redis_client = redis.StrictRedis()
        self.pubsub = self.redis_client.pubsub()
        self.pubsub.subscribe('fictrac')

        # Setup analog output YAW
        self.aout_yaw = VoltageOutput()
        self.aout_yaw.setChannel(self.param['aout_channel_yaw'])
        self.aout_yaw.openWaitForAttachment(5000)
        self.aout_yaw.setVoltage(0.0)

        # Setup analog output X
        self.aout_x = VoltageOutput()
        self.aout_x.setChannel(self.param['aout_channel_x'])
        self.aout_x.openWaitForAttachment(5000)
        self.aout_x.setVoltage(0.0)

        # Setup analog output YAW_GAIN
        self.aout_yaw_gain = VoltageOutput()
        self.aout_yaw_gain.setChannel(self.param['aout_channel_yaw_gain'])
        self.aout_yaw_gain.openWaitForAttachment(5000)
        self.aout_yaw_gain.setVoltage(0.0)


        # Setup analog output Y
        self.aout_y = VoltageOutput()
        self.aout_y.setChannel(self.param['aout_channel_y'])
        self.aout_y.openWaitForAttachment(5000)
        self.aout_y.setVoltage(0.0)

        self.jump = random.randint(1, 2)
        if self.jump == 1:
            self.Jump = 90
        else:
            self.Jump = -90

        self.print = True;

    def run(self, gain_yaw = 1):
        """
        Loop forever listening for new messages on "fictrac" channel and output an
        analog voltage proportional to heading rate for each new message
        """

        end_time = datetime.now() + timedelta(seconds=10)
        while datetime.now() < end_time:
       # while True:
        #counter = 0
        #while counter < 200:

            for item in self.pubsub.listen():

                #counter += 1

                # New message from fictrac - convert from json to python dictionary
                message = item['data']
                try:
                    data = json.loads(message)
                except TypeError:
                    continue

                # Take action based on message type

                if data['type'] == 'reset':
                    # This is a reset message which indicates that FicTrac has been restarted
                    self.time_start = time.time()
                    self.heading_rate_calc.reset(self.time_start)
                    #self.aout.setVoltage(0.0)
                else:
                    # This is a Data message  - get heading value
                    time_curr = time.time()
                    heading = data['heading']
                    intx = data['intx']
                    inty = data['inty']
                    velx = data['velx']
                    vely = data['vely']
                    velheading = data['deltaheading']
                    self.accum_heading += velheading
                    self.accum_x += velx
                    self.accum_y += vely
                    time_elapsed = time_curr - self.time_start


                    # Convert heading to output with gain
                    heading_gain_adjusted = self.accum_heading % (360/gain_yaw)
                    # Shift 90 or -90 deg from current location
                    heading_gain_shifted = (heading_gain_adjusted + self.Jump) % 360 #shift the heading signal by 90 or -90 deg

                    # Set analog output voltage YAW
                    output_voltage_yaw = (heading)*(self.param['aout_max_volt']-self.param['aout_min_volt'])/360
                    output_voltage_yaw = clamp(output_voltage_yaw, self.param['aout_min_volt'], self.param['aout_max_volt'])
                    self.aout_yaw.setVoltage(10-output_voltage_yaw)

                    # Set analog output voltage X
                    wrapped_intx = (intx % (2 * np.pi))
                    output_voltage_x = wrapped_intx * (self.param['aout_max_volt'] - self.param['aout_min_volt']) / (2 * np.pi)
                    output_voltage_x = clamp(output_voltage_x, self.param['aout_min_volt'],
                                               self.param['aout_max_volt'])
                    self.aout_x.setVoltage(output_voltage_x)

                    # Set analog output voltage YAW_GAIN
                    output_voltage_yaw_gain = heading_gain_shifted * (
                                self.param['aout_max_volt'] - self.param['aout_min_volt']) / (360/gain_yaw)
                    output_voltage_yaw_gain = clamp(output_voltage_yaw_gain, self.param['aout_min_volt'],
                                               self.param['aout_max_volt'])
                    self.aout_yaw_gain.setVoltage(10-output_voltage_yaw_gain)


                    # Set analog output voltage Y
                    wrapped_inty = inty % (2 * np.pi)
                    output_voltage_y = wrapped_inty * (self.param['aout_max_volt'] - self.param['aout_min_volt']) / (
                                2 * np.pi)
                    output_voltage_y = clamp(output_voltage_y, self.param['aout_min_volt'],
                                             self.param['aout_max_volt'])
                    self.aout_y.setVoltage(output_voltage_y)



                    # Display status message
                    if self.print:
                        print('frame:  {0}'.format(data['frame']))
                        print('time:   {0:1.3f}'.format(time_elapsed))
                        print('yaw:   {0:1.3f}'.format(heading))
                        print('volt:   {0:1.3f}'.format(output_voltage_yaw))
                        print('int x:   {0:1.3f}'.format(wrapped_intx))
                        print('volt:   {0:1.3f}'.format(output_voltage_x))
                        print('yaw gain adjusted:   {0:1.3f}'.format(heading_gain_adjusted))
                        print('yaw gain shifted:   {0:1.3f}'.format(heading_gain_shifted))
                        print('volt:   {0:1.3f}'.format(output_voltage_yaw_gain))
                        print('int y:   {0:1.3f}'.format(wrapped_inty))
                        print('volt:   {0:1.3f}'.format(output_voltage_y))
                        print('velheading:   {0:1.3f}'.format(velheading))
                        print('Jump:   {0:1.3f}'.format(self.Jump))
                        #print('Counter:   {0:1.3f}'.format(counter))

                       # if datetime.now() == end_time:
                        #       self.pubsub.unsubscribe()

                    #await asyncio.sleep(10)



# Utilities
# ---------------------------------------------------------------------------------------
class AngleRateCalc(object):
    """
    Angular rate calculator
    """

    def __init__(self, t, value_init=0.0):
        self.value_init = value_init
        self.reset(t)

    def reset(self, t):
        self.rate = 0.0
        self.save_prev_state(t, self.value_init)

    def save_prev_state(self, t, value):
        self.time_prev = t
        self.value_prev = value

    def update(self, t, value):
        # Calculate rate
        dt = t - self.time_prev
        self.rate = angle_dist(self.value_prev, value) / dt
        self.save_prev_state(t, value)
        return self.rate


class LowpassFilter(object):
    """
    Simple first order lowpass filter
    """

    def __init__(self, t, cutoff_freq=1.0, value_init=0.0):
        self.value_init = value_init
        self.cutoff_freq = cutoff_freq
        self.reset(t)

    def reset(self, t):
        self.time_prev = t
        self.value_filt = self.value_init

    def get_alpha(self, dt):
        tmp = 2.0 * math.pi * self.cutoff_freq * dt
        alpha = tmp / (tmp + 1.0)
        return alpha

    def update(self, t, value):
        dt = t - self.time_prev
        self.time_prev = t
        alpha = self.get_alpha(dt)
        self.value_filt = (1.0 - alpha) * self.value_filt + alpha * value
        return self.value_filt


def clamp(x, min_val, max_val):
    """
    Clamp value between min_val and max_val
    """
    return max(min(x, max_val), min_val)


def angle_dist(angle0, angle1, angle_type='deg'):
    """
    Calculate distance between two angles - always smallest value.
    """
    # Get max angle value based on angle type 'deg' or 'rad'
    if angle_type == 'deg':
        max_angle = 360.0
    elif angle_type == 'rad':
        max_angle = 2.0 * math.pi
    else:
        raise ValueError('unknown angle type')
    # Compute shortest distance between angles
    value = (angle1 % max_angle) - (angle0 % max_angle)
    if value > 0.5 * max_angle:
        value = value - max_angle
    if value < -0.5 * max_angle:
        value = max_angle + value
    return value



