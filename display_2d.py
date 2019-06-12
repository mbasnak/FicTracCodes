import numpy
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.patches as patches
import matplotlib.transforms as transforms
import math

PLT_REQUIRES_PAUSE = matplotlib.__version__ < '1.5.1'
PLT_PAUSE = 0.0001


class Display(object):

    default_param = {
        'display_xlim': (-20, 20), # relative to fly
        'display_ylim': (-20, 20),
        'fly_color': 'k',
        }

    def __init__(self, param=default_param):

        # set main parameters
        self.fly_color = param['fly_color']
        self.xlim_init = param['display_xlim']
        self.ylim_init = param['display_ylim']
        # some additional plotting parameters
        self.margin = 2.0

        # start plot!
        plt.ion()
        self.fig = plt.figure()
        self.ax = plt.subplot(111)

        # prep all stim items possible, keeping them hidden
        self.pos_line, = plt.plot([0, 1], [0, 1], self.fly_color)
        self.pos_arrow = plt.quiver(0, 0, 1, 0, cmap=cm.get_cmap('Blues', 20))
        self.text = plt.text(.8, .9,'stim off', horizontalalignment='center', verticalalignment='center', transform = self.ax.transAxes)
        plt.axis('equal')
        plt.grid('on')
        plt.xlabel('x pos')
        plt.ylabel('y pos')
        plt.title("FicTrac 2D")
        self.reset()

        self.fig.canvas.flush_events()
        if PLT_REQUIRES_PAUSE:
            plt.pause(PLT_PAUSE)

    def update(self, data):
        self.set_xylim(data)
        self.fig.canvas.flush_events()
        if PLT_REQUIRES_PAUSE:
            plt.pause(PLT_PAUSE)

    def draw_path(self, data):
        self.pos_line.set_xdata(data.posx_list)
        self.pos_line.set_ydata(data.posy_list)
        new_position = numpy.array([data.posx, data.posy])
        self.pos_arrow.set_offsets(new_position)
        self.pos_arrow.set_UVC(math.cos(math.radians(data.heading)), math.sin(math.radians(data.heading)))
        if self.stim_on:
            self.pos_arrow.set_color(self.stim_color)
        else:
            self.pos_arrow.set_color(self.fly_color)

    def set_xylim(self, data):
        self.xlim = data.posx + self.xlim_init[0], data.posx + self.xlim_init[1]
        self.ylim = data.posy + self.ylim_init[0], data.posy + self.ylim_init[1]
        self.ax.set_xlim(*self.xlim)
        self.ax.set_ylim(*self.ylim)

    
    def reset(self):
        self.xlim = self.xlim_init
        self.ylim = self.ylim_init
        self.pos_line.set_xdata([])
        self.pos_line.set_ydata([])
        self.pos_arrow.set_offsets(numpy.array([0, 0]))
        self.pos_arrow.set_UVC(1, 0)
        self.ax.set_xlim(*self.xlim)
        self.ax.set_ylim(*self.ylim)
        self.fig.canvas.flush_events()
        if PLT_REQUIRES_PAUSE:
            plt.pause(PLT_PAUSE)