        
import sys
import os
import time
import json
import threading
import queue
import math
import signal
import ffmpeg
import h5py
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.cm as cm
from matplotlib.collections import LineCollection
from matplotlib.colors import ListedColormap, BoundaryNorm, Normalize
import cmocean
from itertools import compress

from pathlib import Path

from .display_2d import Display


class Figure2D(object):
    DefaultParam = {
        'experiment_type': 'freewalk',
    }

    def __init__(self, file, param=DefaultParam):
        self.param = param
        self.file = file
        f = h5py.File(file, 'r')
        self.times = list(f['time'])
        self.posx = list(f['posx'])
        self.posy = list(f['posy'])
        self.headings = list(f['heading'])
        params = json.loads(f.attrs['jsonparam'])
        self.stim_x = list(f['stim_x'])
        self.stim_y = list(f['stim_y'])
        self.pulse_on = list(f['pulse_on'])
        self.stim_heading = list(f['stim_heading'])

        if not self.param['experiment_type'] == 'freewalk':
            self.pulse_on = list(f['pulse_on'])

        self.param = params

        self.display = Display(params)

    def plot_2d(self):

        #plot path
        if self.param['experiment_type'] == 'freewalk':
            self.display.pos_line.set_xdata(self.posx)
            self.display.pos_line.set_ydata(self.posy)
        else:
            self.display.pos_line.set_visible(True)
            # Create a set of line segments so that we can color them individually
            # This creates the points as a N x 1 x 2 array so that we can stack points
            # together easily to get the segments. The segments array for line collection
            # needs to be (numlines) x (points per line) x 2 (for x and y)
            points = np.array([self.posx, self.posy]).T.reshape(-1, 1, 2)
            segments = np.concatenate([points[:-1], points[1:]], axis=1)
            axs = self.display.ax



            self.display.pos_line.set_xdata(self.posx)
            self.display.pos_line.set_ydata(self.posy)

            on_points = np.squeeze(points[np.array(self.pulse_on, dtype=bool)])
            plt.plot(on_points[:, 0], on_points[:, 1], 'r.')
            # Use a boundary norm instead
            #colormap_two = ListedColormap(['k', 'r'])
            #norm = BoundaryNorm([-0.5, 0.5, 1.5], colormap_two.N)
            #lc = LineCollection(segments, cmap=colormap_two, norm=norm)
            #lc.set_array(np.array(self.pulse_on[:-1]))
            #lc.set_linewidth(2)
            #line = axs.add_collection(lc)


        positions = np.transpose([self.posx, self.posy])
        self.display.pos_arrow.set_offsets(positions[::300])
        u_list = [math.cos(math.radians(head)) for head in self.headings[::300]]
        v_list = [math.sin(math.radians(head)) for head in self.headings[::300]]
        colors = np.arctan2(v_list, u_list)
        norm = Normalize()
        norm.autoscale(colors)
        colormap = cmocean.cm.phase

        self.display.pos_arrow.set_UVC(u_list, v_list) #, colors/2*np.pi + 1
        #self.display.pos_arrow.set_cmap(colormap)

        # hide arrow
        self.display.pos_arrow.set_visible(True)


        # plot start and end (maybe introduce text)

        start_text = plt.text(self.posx[0], self.posy[0], 'START', horizontalalignment='center',
                              verticalalignment='center', color='g')
        end_text = plt.text(self.posx[-1], self.posy[-1], 'END', horizontalalignment='center',
                              verticalalignment='center', color='b')


        #plot stim
        if self.param['experiment_type'] == 'freewalk':
            self.display.set_stim_enabled(False)
        else:
            self.display.set_stim_enabled(True)
            self.stim_x_display = np.unique([num for num in self.stim_x if num != 0])[0]
            self.stim_y_display = np.unique([num for num in self.stim_y if num != 0])[0]
            self.stim_heading_display = np.unique([num for num in self.stim_heading if num != 0])[0]

        self.display.set_stim_type(self.param['experiment_type'])
        self.display.stim_on = False

        self.display.fig.show()

        self.display.text.set_text(self.param['experiment_type'])
        # adjust range
        #plt.axis('normal')
        self.display.ax.set_aspect('equal', 'box')
        rangex = max(self.posx) - min(self.posx)
        rangey = max(self.posy) - min(self.posy)
        extra = 50
        if rangex > rangey:
            self.display.ax.set_xlim(min(self.posx) - extra, max(self.posx) + extra)
            y_avg = (min(self.posy) + max(self.posy)) / 2
            self.display.ax.set_ylim(y_avg - rangex * 0.5 - extra, y_avg + rangex * 0.5 + extra)
        else:
            self.display.ax.set_ylim(min(self.posy) - extra, max(self.posy) + extra)
            x_avg = (min(self.posx) + max(self.posx)) / 2
            self.display.ax.set_xlim(x_avg - rangey * 0.5 - extra, x_avg + rangey * 0.5 + extra)

        self.display.fig.tight_layout()
        filename = os.path.splitext(self.file)

        plt.savefig(filename[0]+'.png')
        plt.savefig(filename[0] + '.pdf')
        plt.close()


    def movie_2d(self):

        intrange = np.arange(0, len(self.posx), 1)

        Writer = animation.writers['ffmpeg']
        writer = Writer(fps=150, metadata=dict(artist='Me'), bitrate=1800)

        ani = animation.FuncAnimation(
            self.display.fig, self.animate, init_func=None, frames=intrange, fargs=(self.posx, self.posy))

        filename = os.path.splitext(self.file)
        ani.save(filename[0] + '.mp4', fps=150)

    def init(self):
        return self.display

    def animate(self, i, posx, posy):
        # plot path
        self.display.pos_line.set_xdata(posx[0:i + 1])
        self.display.pos_line.set_ydata(posy[0:i + 1])
        self.display.pos_dot.set_xdata(posx[i])
        self.display.pos_dot.set_ydata(posy[i])
        self.xlim = posx[i] - 10, posx[i] + 10
        self.ylim = posy[i] - 10, posy[i] + 10
        self.display.ax.set_xlim(*self.xlim)
        self.display.ax.set_ylim(*self.ylim)
        # plot stim
        if self.param['experiment_type'] == 'freewalk':
            self.display.set_stim_enabled(False)
            self.display.text.set_text('')
        else:
            self.display.set_stim_enabled(True)
            self.display.set_stim_on(self.pulse_on[i])

        self.display.set_stim_type(self.param['experiment_type'])
        self.display.set_stim_center(self.stim_x, self.stim_y)
        self.display.draw_stim()

        return self.display