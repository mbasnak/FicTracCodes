from __future__ import print_function # 'print' became a function in Python 3. This __future__ import is to make it always be used as a function, even when running th code in previous Python version
import redis # imports module to interface to the Redis server
import json # JSON stands for JavaScript Object Notation, and it is a lightweight data interchange format. This is how the messages from fictrac are going to be read
import time # this module provides time-related functions
import math # this module provides access to the mathematical functions defined by the C standard
import numpy as np # module for scientific computing (working with arrays and other things involving linear algebra)
from Phidget22.Devices.VoltageOutput import VoltageOutput # I can't find this module in the ones you can download from the pidgets website, but I presume it is used to output a voltage through the channels
import Phidget22.PhidgetException
import Phidget22.Phidget
from datetime import datetime, timedelta
from time import sleep


class BlockAout(object): # we're creating an object called FicTracAout that we will reference later
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
    } # we initialize all of the different parameters that are going to be called when calling the function defined below

    def __init__(self, param=DefaultParam): # this is known as a constructor.
    # it is called when an object is created from the class and it allows to initialize the attributes
    # of the class

    # Next, we list all of the attributes for our object 'FicTracAout'
        self.param = param # we're setting the parameter attribute
        self.time_start = time.time() # we get the current time and set the time_start to be that

        # Beginning values (to keep track of accumulated heading)
        self.accum_heading = 0 # we define the accum_heading and set it to 0
        self.accum_x = 0 # we define the accum_x and set it to 0
        self.accum_y = 0 # we define the accum_y and set it to 0

        # Setup redis subscriber
        self.redis_client = redis.StrictRedis() # this is user to connect to the redis server
        self.pubsub = self.redis_client.pubsub() # this subscribes to channels in the redis server
        self.pubsub.subscribe('fictrac') # this subscribes to the channel 'fictrac' and listens for new messages there

        # Setup analog output YAW
        self.aout_yaw = VoltageOutput() # create a voltage output channel for the phidgets device
        self.aout_yaw.setChannel(self.param['aout_channel_yaw']) # address the channel: indicate phidgets what channel to connect to
        self.aout_yaw.openWaitForAttachment(5000) # open the channel; this tries to match the physical phidget channel to the software
        self.aout_yaw.setVoltage(0.0) # send a voltage command

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


        #Next we define what's known as the 'methods' of our object

    def run(self, gain_yaw = 1, block_time = 10):
        """
        Loop forever listening for new messages on "fictrac" channel and output an
        analog voltage proportional to heading rate for each new message
        """


        while True: # This statements makes the following loop run forever

            for item in self.pubsub.listen():

                #item refers to the data that's being outputed by the fictrac channel caught by the server at any given time.
                # it looks like this:
                #{'type': 'message', 'pattern': None, 'channel': b'fictrac', 'data':
                # b'{"deltaheading":421.411575876916,"frame":2729,"heading":23.9414329813745,"intx":3672.85974846204,"inty":-17093.2855767625,"posx":-177.638739989378,"posy":11.1943596672353,"type":"data","velx":-5.82186481311745,"vely":-10.1414673377749}'}


                # New message from fictrac - convert from json to python dictionary
                message = item['data'] #define the message as the part of the signal received that actually contains data
                try: # the 'try' statement lets you test a block of code for errors
                    data = json.loads(message) #load json message from fictrac into python
                except TypeError: # the escept block lets you handle the error (in this case conitnue if 'data' is not the type you expected)
                    continue

                # Take action based on message type
                if data['type'] == 'reset':
                    # This is a reset message which indicates that FicTrac has been restarted
                    self.time_start = time.time() #if fictrac is restarted, reset the start time

                else:
                    # This is a Data message  - get heading value
                    time_curr = time.time() # get the current time
                    time_elapsed = time_curr - self.time_start # calculate the time elapsed since the start of the acquisition
                    heading = data['heading'] # the heading data
                    intx = data['intx'] # intx
                    inty = data['inty'] # inty
                    velx = data['velx'] # velx
                    vely = data['vely'] # vely
                    velheading = data['deltaheading'] # define velheading as the change in heading
                    self.accum_heading += velheading # obtain the accumulated heading adding the delta heading every frame
                    self.accum_x += velx # obtain the accumulated forward distance adding the change in forward distance every frame
                    self.accum_y += vely # obtain the accumulated side distance adding the change in side distance every frame



                    # Set analog output voltage YAW
                    output_voltage_yaw = (heading)*(self.param['aout_max_volt']-self.param['aout_min_volt'])/360 # multiply the heading by the max voltage difference (10) and divide by the max degrees (360) to constrain the voltage output between 0 and 10 V
                    output_voltage_yaw = clamp(output_voltage_yaw, self.param['aout_min_volt'], self.param['aout_max_volt']) # just in case, clamp the signal between 0 and 10 V using an aux function
                    self.aout_yaw.setVoltage(10-output_voltage_yaw) # since the panels movement is inverted with respect to fictrac's output, I'm sustracting the signal from the previous row from 10 V to have the gain inverted

                    # Set analog output voltage X
                    wrapped_intx = (intx % (2 * np.pi)) # wrap the x signal to 2pi
                    output_voltage_x = wrapped_intx * (self.param['aout_max_volt'] - self.param['aout_min_volt']) / (2 * np.pi) # multiply by the maximum voltage difference and divide by 2pi to wrap it to 10 V
                    output_voltage_x = clamp(output_voltage_x, self.param['aout_min_volt'],
                                               self.param['aout_max_volt']) # clamp the signal between 0 and 10 V
                    self.aout_x.setVoltage(output_voltage_x) # set the output voltage to that value

                    # Set analog output voltage YAW_GAIN
                    heading_gain_adjusted = self.accum_heading % (360/gain_yaw)
                    output_voltage_yaw_gain = heading_gain_adjusted * (
                                self.param['aout_max_volt'] - self.param['aout_min_volt']) / (360/gain_yaw)
                    output_voltage_yaw_gain = clamp(output_voltage_yaw_gain, self.param['aout_min_volt'],
                                               self.param['aout_max_volt'])
                    self.aout_yaw_gain.setVoltage(10-output_voltage_yaw_gain)

                    #for block 2, add gaussian noise to the feedback
                    if round(time_elapsed,0) > block_time and round(time_elapsed) < block_time*2:
                        # add noise
                        noiseUnit = np.random.normal(0, 1, 1)
                        noiseUnit = clamp(noiseUnit,-0.3,0.3)
                        output_voltage_yaw_gain_noisy = (output_voltage_yaw_gain + noiseUnit) % 10 #add noise and wrap to 10 V
                        output_voltage_yaw_gain_noisy = clamp(output_voltage_yaw_gain_noisy, self.param['aout_min_volt'],
                                                self.param['aout_max_volt']) #clamp between 0 and 10 V
                        self.aout_yaw_gain.setVoltage(10-output_voltage_yaw_gain_noisy) #take 10 - V to invert the gain (so that it matches fictrac output and panels)



                    # Set analog output voltage Y
                    wrapped_inty = inty % (2 * np.pi)
                    output_voltage_y = wrapped_inty * (self.param['aout_max_volt'] - self.param['aout_min_volt']) / (
                                2 * np.pi)
                    output_voltage_y = clamp(output_voltage_y, self.param['aout_min_volt'],
                                             self.param['aout_max_volt'])
                    self.aout_y.setVoltage(output_voltage_y)



                    # Display status message
                    #if self.print: # print the relevant variables
                    print('frame:  {0}'.format(data['frame']))
                    print('time:   {0:1.3f}'.format(time_elapsed))
                    print('yaw:   {0:1.3f}'.format(heading))
                    print('volt:   {0:1.3f}'.format(output_voltage_yaw))
                    print('int x:   {0:1.3f}'.format(wrapped_intx))
                    print('volt:   {0:1.3f}'.format(output_voltage_x))
                    print('yaw gain adjusted:   {0:1.3f}'.format(heading_gain_adjusted))
                    print('volt:   {0:1.3f}'.format(output_voltage_yaw_gain))
                    print('int y:   {0:1.3f}'.format(wrapped_inty))
                    print('volt:   {0:1.3f}'.format(output_voltage_y))
                    print('velheading:   {0:1.3f}'.format(velheading))
                    print()






# Utilities
# ---------------------------------------------------------------------------------------
def clamp(x, min_val, max_val):
    """
    Clamp value between min_val and max_val
    """
    return max(min(x, max_val), min_val)