#!/usr/bin/python2
"""Reads and plots the data in a simulation log protocol buffer file.
This script requires Python 2, because protobufs doesn't really work for Python 3 yet."""

import argparse
import os
import sys
from textwrap import wrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from senderrunner_runner import SenderRunnerRunner
from matplotlib.patches import Circle
from matplotlib.animation import FuncAnimation
import utils
import datautils

DEFAULT_PLOTS_DIR = "log-plots"
LAST_PLOTS_SYMLINK = "last-plots"

def pretty(name):
    return name.split('.')[-1].capitalize().replace("_", " ")

class BaseFigureGenerator(object):
    """Abstract base class to generate figures.
    BasePlotGenerator and BaseAnimationGenerator both derive from this class."""

    title = None
    xlabel = None
    ylabel = None
    figfilename = None
    plotsdir = '.'
    plot_kwargs = {}
    file_extension = None
    start_time = 0
    end_time = None

    def __init__(self, **kwargs):
        self._plotsdir = kwargs.pop('plotsdir', self.plotsdir)
        self._start_time = kwargs.pop('start_time', self.start_time)
        self._end_time = kwargs.pop('end_time', self.end_time)
        super(BaseFigureGenerator, self).__init__(**kwargs)

    def get_figfilename(self):
        name = os.path.join(self._plotsdir, self.figfilename)
        if not name.endswith("." + self.file_extension):
            name += "." + self.file_extension
        return name

    def generate(self, run_data):
        raise NotImplementedError("Subclasses must implement generate()")

    def _print_generating_line(self):
        print("Generating {}...".format(self.get_figfilename()))


class BasePlotGenerator(BaseFigureGenerator):
    """Abstract base class to generate plots."""

    legend_location = 'best'
    file_extension = 'png'

    def iter_plot_data(self, run_data):
        """Iterates through data to be plotted. The default implementation just
        gives the single element `self.get_plot_data(run_data)`. Subclasses
        that need to plot more than one series should override this method.
        Each iteration should yield a 3-tuple (x, y, label)."""
        yield self.get_plot_data(run_data) + (None,)

    def get_plot_data(self, run_data):
        """Either this or `iter_plot_data()` be impelemented by subclasses.
        Returns a tuple of two elements (x, y) each being a list of data points.
        The two lists must have the same length."""
        raise NotImplementedError("Subclasses must implement either get_plot_data() or iter_plot_data()")

    def generate(self, run_data, whiskers=None):
        """Generates the figure for `run_data`, which should be a
        SimulationRunData instance."""
        self._print_generating_line()
        self.whiskers = whiskers
        self.fig = plt.figure()
        self.generate_plot(run_data)
        self.fig.savefig(self.get_figfilename(), format='png', bbox_inches='tight')
        plt.close(self.fig)

    def generate_plot(self, run_data):
        """Generates the plot for `run_data`, which should be a
        SimulationRunData instance."""

        self.ax = self.fig.add_subplot(111)

        for x, y, label in self.iter_plot_data(run_data):
            self.ax.plot(x, y, label=label, **self.plot_kwargs)

        self.ax.set_title(self.title)
        self.ax.set_xlabel(self.xlabel)
        self.ax.set_ylabel(self.ylabel)
        if hasattr(self, 'get_xlim'):
            self.ax.set_xlim(self.get_xlim(run_data))
        if hasattr(self, 'get_ylim'):
            self.ax.set_ylim(self.get_ylim(run_data))
        if len(self.ax.lines) > 1:
            self.ax.legend(loc=self.legend_location)


class BaseAnimationGenerator(BaseFigureGenerator):
    """Abstract base class to generate timed animations."""

    interval = 1
    history = 20
    file_extension = 'mp4'
    dpi = 200

    plot_kwargs = {'linestyle': 'solid', 'linewidth': 0.25, 'color': (0.75, 0.75, 0.75),
            'marker': '.', 'markersize': 12.0, 'markerfacecolor': 'blue', 'markeredgecolor': 'blue'}

    def __init__(self, **kwargs):
        self._interval = kwargs.pop('interval', self.interval)
        super(BaseAnimationGenerator, self).__init__(**kwargs)

    def animate(self, i):
        """Draws frame `i`. This function is passed to FuncAnimation; see
        the matplotlib animations documentation for details."""
        raise NotImplementedError("Subclasses must implement animate()")

    def generate(self, run_data):
        self._print_generating_line()
        self.fig = plt.figure()
        self.initial(run_data)
        anim = FuncAnimation(self._fig, self.animate, frames=len(self._times),
            interval=self._interval)
        anim.save(self.get_figfilename(), dpi=self.dpi)
        plt.close(self.fig)

    def initial(self, run_data):
        """Initializes the animation. This function is passed to FuncAnimation;
        see the matplotlib animations documentation for details."""
        raise NotImplementedError("Subclasses must implement initial()")


class BaseSingleAnimationGenerator(BaseAnimationGenerator):

    def animate(self, i):
        sys.stdout.write("Up to frame {:d} of {:d}...\r".format(i, len(self._times)))
        sys.stdout.flush()
        if i < self.history:
            self._line.set_data(self._x[:i], self._y[:i])
        else:
            self._line.set_data(self._x[i-self.history:i], self._y[i-self.history:i])
        self._text.set_text('t = {:.2f} ({:d})'.format(self._times[i], i))
        for circle, sending in zip(self._circles, self._sending[i]):
            circle.set_facecolor('g' if sending else 'r')

    def initial(self, run_data):
        self._times = self.get_times(run_data)
        self._sending = self.get_sending(run_data)
        self._x, self._y = self.get_plot_data(run_data)
        xmax = max(self._x)
        ymax = max(self._y)

        self.ax = self.fig.add_subplot(111)
        self.ax.set_title(self.title)
        self.ax.set_xlabel(self.xlabel)
        self.ax.set_ylabel(self.ylabel)
        self.ax.set_xlim([0, xmax])
        self.ax.set_ylim([0, ymax])

        self._line = self.ax.plot([], [], **self.plot_kwargs)[0]
        self._text = self.ax.text(0.05, 0.95, '', transform=self.ax.transAxes)
        self._circles = []
        for i in range(run_data.config.num_senders):
            circle = Circle((0.05+i*0.05, 0.90), radius=0.02, facecolor='k', transform=self.ax.transAxes)
            self.ax.add_artist(circle)
            self._circles.append(circle)

    def get_plot_data(self, run_data):
        """Must be impelemented by subclasses. Returns a tuple of two elements
        (x, y) each being a list of data points. The two lists must have the
        same length."""
        raise NotImplementedError("Subclasses must implement get_plot_data()")


class BaseGridAnimationGenerator(BaseAnimationGenerator):
    """Abstract base class to generate grid animations.

    Subclasses must implement get_plot_data(), which must return a tuple of
    lists. The animation will then draw one plot for each pair of lists.
    """

    ticklabelsize = 5
    axislabelsize = 8
    timetextsize = 9
    wrapwidth = 10
    plot_kwargs = {'linestyle': 'solid', 'linewidth': 0.25, 'color': (0.75, 0.75, 0.75),
            'marker': '.', 'markersize': 4.0, 'markerfacecolor': 'blue', 'markeredgecolor': 'blue'}

    def animate(self, index):
        sys.stdout.write("Up to frame {:d} of {:d}...\r".format(index, len(self._times)))
        sys.stdout.flush()
        nvars = self._nvars
        for i in range(nvars):
            y = self._data[i]
            for j in range(nvars):
                x = self._data[j]
                if index < self.history:
                    self._lines[i*nvars+j].set_data(x[:index], y[:index])
                else:
                    self._lines[i*nvars+j].set_data(x[index-self.history:index],
                            y[index-self.history:index])
        self._text.set_text('t = {:.2f} ({:d})'.format(self._times[index], index))
        for circle, sending in zip(self._circles, self._sending[index]):
            circle.set_facecolor('g' if sending else 'r')

    def initial(self, run_data):
        self._times = run_data.get_times()
        self._sending = run_data.get_sending()
        self._data = self.get_plot_data(run_data)
        nvars = self._nvars = len(self._data)
        maxes = [max(d) for d in self._data]

        self._lines = [] # will be a 2D list of axes, indexed by (row, col)
        self._text = self.fig.text(0.05, 0.95, '', size=self.timetextsize)
        self._circles = []
        for i in range(run_data.num_senders):
            circle = Circle((0.05+i*0.05, 0.92), radius=0.02, facecolor='k', transform=self.fig.transFigure)
            self.fig.patches.append(circle)
            self._circles.append(circle)

        for i in range(nvars):
            for j in range(nvars):
                ax = self.fig.add_subplot(nvars, nvars, i*nvars+j+1)
                line = ax.plot([], [], **self.plot_kwargs)[0]
                self._lines.append(line)

                ax.set_xlim([0, maxes[j]])
                ax.set_ylim([0, maxes[i]])

                # x tick labels apply to last row only
                if i == nvars-1:
                    for label in ax.get_xticklabels():
                        label.set_size(self.ticklabelsize)
                        label.set_rotation('vertical')
                else:
                    ax.set_xticklabels([])
                if i == 0:
                    xlabeltext = '\n'.join(wrap(self.titles[j], self.wrapwidth))
                    ax.set_xlabel(xlabeltext, fontsize=self.axislabelsize)
                    ax.get_xaxis().set_label_position('top')

                # y tick labels apply to first column only
                if j == 0:
                    for label in ax.get_yticklabels():
                        label.set_size(self.ticklabelsize)
                    ylabeltext = '\n'.join(wrap(self.titles[i], self.wrapwidth))
                    ax.set_ylabel(ylabeltext, fontsize=self.axislabelsize)
                else:
                    ax.set_yticklabels([])

    def get_plot_data(self, run_data):
        """Must be impelemented by subclasses. Returns a tuple of lists, each
        being a list of data points. The lists must all have the same length.
        The animation will plot one plot for each pair of lists."""
        raise NotImplementedError("Subclasses must implement get_plot_data()")


class TimePlotMixin(object):
    """Provides functions for plots where the x-axis is time."""

    xlabel = "Time (s)"
    overlay_whiskers = False

    def __init__(self, **kwargs):
        self._overlay_whiskers = kwargs.pop('overlay_whiskers', self.overlay_whiskers)
        super(TimePlotMixin, self).__init__(**kwargs)

    def get_xlim(self, run_data):
        x = run_data.get_times()
        return [min(x), max(x)]

    def plot_whisker_change_times(self, ax, run_data, index):
        """Adds dots for whisker changes times on the axes `ax`."""
        times = run_data.get_whisker_change_times(index)
        for time in times:
            ax.axvline(time, color=(0.5, 0.5, 0.5))

    def plot_whisker_bounds(self, ax, run_data, index, attrname):
        lower, upper = run_data.get_whisker_bounds(index, attrname)
        t_start = run_data.get_whisker_change_times(index)
        t_end = t_start[1:] + [run_data.get_times()[-1]]
        ymin, ymax = ax.get_ylim()
        for t1, t2, l, u in zip(t_start, t_end, lower, upper):
            ax.fill([t1, t1, t2, t2], [ymin, l, l, ymin], color=(0.75, 0.75, 0.75))
            ax.fill([t1, t1, t2, t2], [u, ymax, ymax, u], color=(0.75, 0.75, 0.75))


class BaseTimePlotGenerator(TimePlotMixin, BasePlotGenerator):
    """Abstract base class to generate plots where the x-axis is time."""

    def __init__(self, senders=None, **kwargs):
        self.senders = senders

        super(BaseTimePlotGenerator, self).__init__(**kwargs)

        if self.senders is not None:
            if len(self.senders) == 1:
                self.title += ": sender {}".format(self.senders[0])
                self.figfilename += "_sender_{}".format(self.senders[0])
            else:
                self.title += ": senders {}".format(", ".join([str(x) for x in self.senders]))
                self.figfilename += "_senders_{}".format("_".join([str(x) for x in self.senders]))

    def _senders(self, run_data):
        return self.senders if self.senders is not None else range(run_data.num_senders)

    def get_values(self, run_data, index):
        raise NotImplementedError("Subclasses must implement get_values()")

    def iter_plot_data(self, run_data):
        x = run_data.get_times()
        for i in self._senders(run_data):
            y = self.get_values(run_data, i)
            label = "sender {:d}".format(i)
            yield x, y, label

    def generate_plot(self, run_data):
        super(BaseTimePlotGenerator, self).generate_plot(run_data)
        if self._overlay_whiskers and self.senders is not None and len(self.senders) == 1:
            sender = self.senders[0]
            self.plot_whisker_change_times(self.ax, run_data, sender)


class RawDataTimePlotGenerator(BaseTimePlotGenerator):
    """Generates plots where the x-axis is time and the y-axis is taken directly
    from raw data."""

    def __init__(self, attrname, unit=None, **kwargs):
        self.attrname = attrname
        self.figfilename = attrname

        pretty_name = pretty(attrname)
        self.ylabel = pretty_name
        if unit:
            self.ylabel += " ({})".format(unit)
        self.title = pretty_name

        super(RawDataTimePlotGenerator, self).__init__(**kwargs)

    def get_values(self, run_data, index):
        return run_data.get_raw_data(index, self.attrname)

    def generate_plot(self, run_data):
        super(RawDataTimePlotGenerator, self).generate_plot(run_data)
        if self._overlay_whiskers and self.senders is not None and len(self.senders) == 1:
            sender = self.senders[0]
            if self.attrname.startswith("memory."):
                ylim = self.ax.get_ylim()
                attrname = self.attrname[7:]
                self.plot_whisker_bounds(self.ax, run_data, sender, attrname)
                self.ax.set_ylim(ylim)


class DifferenceQuotientTimePlotGenerator(BaseTimePlotGenerator):
    """Generates plots where the x-axis is time and the y-axis is of the form:
        y[i] = (b[i] - b[i-1]) / (a[i] - a[i-1])
    where a and b are both raw data."""

    def __init__(self, numerator, denominator, title, unit=None, **kwargs):
        self.numerator_attrname = numerator
        self.denominator_attrname = denominator
        self.figfilename = title.replace(" ", "_")
        self.title = title.capitalize()
        self.ylabel = title.capitalize()
        if unit:
            self.ylabel += " ({})".format(unit)

        super(DifferenceQuotientTimePlotGenerator, self).__init__(**kwargs)

    def get_values(self, run_data, index):
        numerator_values = run_data.get_raw_data(index, self.numerator_attrname)
        denominator_values = run_data.get_raw_data(index, self.denominator_attrname)
        data = [0.0]
        for i in xrange(1, len(numerator_values)):
            n = numerator_values[i] - numerator_values[i-1]
            d = denominator_values[i] - denominator_values[i-1]
            if n == 0 and d == 0:
                data.append(data[-1])
            elif d == 0:
                data.append(0.0)
            else:
                data.append(n/d)
        return data


class DifferenceTimePlotGenerator(BaseTimePlotGenerator):
    """Generates plots where the x-axis is time and the y-axis is the difference
    between the current time and the previous time, skipped if the difference is
    zero."""

    plot_kwargs = {'linestyle': 'None', 'marker': 'x'}

    def __init__(self, attrname, title, unit=None, **kwargs):
        self.attrname = attrname
        self.figfilename = title.replace(" ", "_")
        self.title = title.capitalize()
        self.ylabel = title.capitalize()
        if unit:
            self.ylabel += " ({})".format(unit)

        super(DifferenceTimePlotGenerator, self).__init__(**kwargs)

    def iter_plot_data(self, run_data):
        for i in self._senders(run_data):
            x, y = self.get_values(run_data, i)
            label = "sender {:d}".format(i)
            yield x, y, label

    def get_values(self, run_data, index):
        t_raw = run_data.get_times()
        y_raw = run_data.get_raw_data(index, self.attrname)
        t = []
        y = []
        for i in xrange(1, len(t_raw)):
            d = y_raw[i] - y_raw[i-1]
            if d != 0:
                if t_raw[i] == t_raw[i-1]:
                    y[-1] += d
                else:
                    t.append(t_raw[i])
                    y.append(d)
        return t, y



class TwoScalesTimePlotGenerator(TimePlotMixin, BasePlotGenerator):
    """Class to generate plots with two y-axis scales."""
    # TODO Separate two-scales plot functionality from time retrieval of
    # data.

    legend_location = 'best'
    file_extension = 'png'

    color1 = 'b'
    color2 = 'r'

    def __init__(self, spec1, spec2, **kwargs):
        self.figfilename = "{attr1}_{index1:d}__{attr2}_{index2:d}".format(
            attr1=spec1[0], index1=spec1[1], attr2=spec2[0], index2=spec2[1])
        self.title1 = pretty(spec1[0]) + " " + str(spec1[1])
        self.title2 = pretty(spec2[0]) + " " + str(spec2[1])
        self.spec1 = spec1
        self.spec2 = spec2

        super(TwoScalesTimePlotGenerator, self).__init__(**kwargs)

    def generate_plot(self, run_data):
        """Generates the plot for `run_data`, which should be a
        SimulationRunData instance."""

        ax1 = self.fig.add_subplot(111)
        t = run_data.get_times()
        y1 = run_data.get_raw_data(self.spec1[1], self.spec1[0])
        y2 = run_data.get_raw_data(self.spec2[1], self.spec2[0])

        ax1.plot(t, y1, color=self.color1)
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel(self.title1, color=self.color1)
        for tl in ax1.get_yticklabels():
            tl.set_color(self.color1)
        ax1.set_xlim([min(t), max(t)])

        ax2 = ax1.twinx()
        ax2.plot(t, y2, color=self.color2)
        ax2.set_ylabel(self.title2, color=self.color2)
        for tl in ax2.get_yticklabels():
            tl.set_color(self.color2)
        ax2.set_xlim([min(t), max(t)])

        if self._overlay_whiskers:
            self.plot_whisker_change_times(ax1, run_data, self.spec1[1])


class BaseParametricPlotGenerator(BasePlotGenerator):

    plot_kwargs = {'linestyle': 'solid', 'linewidth': 0.25, 'color': (0.75, 0.75, 0.75),
            'marker': '.', 'markersize': 5.0, 'markerfacecolor': 'blue', 'markeredgecolor': 'blue'}


class SenderVersusSenderMixin(object):
    """Provides methods to show the correlation between two senders."""

    def __init__(self, attrname, sender_indices, unit=None, **kwargs):
        self.attrname = attrname
        self.figfilename = "{}_sender{:d}_vs_sender{:d}".format(attrname, sender_indices[0], sender_indices[1])

        pretty_name = pretty(attrname)
        axis_label = pretty_name
        if unit:
            axis_label += " ({})".format(unit)
        self.xlabel = axis_label + " of sender {:d}".format(sender_indices[0])
        self.ylabel = axis_label + " of sender {:d}".format(sender_indices[1])
        self.title = pretty_name + ": sender {:d} vs sender {:d}".format(*sender_indices)
        self.indices = sender_indices

        super(SenderVersusSenderMixin, self).__init__(**kwargs)

    def get_plot_data(self, run_data):
        x = run_data.get_raw_data(self.indices[0], self.attrname)
        y = run_data.get_raw_data(self.indices[1], self.attrname)
        return x, y


class SingleSenderParametricMixin(object):
    """Provides methods to show the correlation between two variables (for one sender)."""

    def __init__(self, attrnames, sender_index, units=None, **kwargs):
        self.attrnames = attrnames
        self.figfilename = "{}_vs_{}_sender{:d}".format(attrnames[0], attrnames[1], sender_index)

        pretty_names = [pretty(attrname) for attrname in attrnames]
        axis_labels = pretty_names
        if units:
            axis_labels = [label + " ({})".format(unit) for label, unit in zip(axis_labels, units)]
        self.xlabel = axis_labels[0]
        self.ylabel = axis_labels[1]
        self.title = "{} vs {} for sender {:d}".format(pretty_names[0], pretty_names[1], sender_index)
        self.index = sender_index

        super(SingleSenderParametricMixin, self).__init__(**kwargs)

    def get_plot_data(self, run_data):
        x = run_data.get_raw_data(self.index, self.attrnames[0])
        y = run_data.get_raw_data(self.index, self.attrnames[1])
        return x, y


class SenderVersusSenderPlotGenerator(SenderVersusSenderMixin, BaseParametricPlotGenerator):
    """Generates plots that show the correlation between two senders."""
    pass


class SenderVersusSenderAnimationGenerator(SenderVersusSenderMixin, BaseSingleAnimationGenerator):
    """Generates animations that show the progress of two senders with time."""
    pass


class SingleSenderParametricPlotGenerator(SingleSenderParametricMixin, BaseParametricPlotGenerator):
    """Generates plots that show the correlation between two variables."""
    pass


class SingleSenderParametricAnimationGenerator(SingleSenderParametricMixin, BaseSingleAnimationGenerator):
    """Generates animations that show the progress of two variables with time."""
    pass


class MultiVariableParametricGridAnimationGenerator(BaseGridAnimationGenerator):

    def __init__(self, *specs, **kwargs):
        self.figfilename = kwargs.pop("figfilename", "multi")
        self.titles = [pretty(attrname) + " " + str(sender_index) for attrname, sender_index in specs]
        self.specs = specs
        super(MultiVariableParametricGridAnimationGenerator, self).__init__(**kwargs)

    def get_plot_data(self, run_data):
        return [run_data.get_raw_data(index, attrname) for attrname, index in self.specs]


def make_plots_dir(dirname, argvalue):
    if argvalue.endswith(".data"):
        basename = argvalue[:-5]
    else:
        basename = argvalue
    return utils.make_output_dir(dirname, DEFAULT_PLOTS_DIR, basename, LAST_PLOTS_SYMLINK)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("inputfile", type=str,
    help="Input file (data file or RemyCC)")
senderrunner_group = parser.add_argument_group("sender-runner arguments", "Only used when --remycc is used")
senderrunner_group.add_argument("-s", "--nsenders", type=int, default=2,
    help="Number of senders")
senderrunner_group.add_argument("-p", "--link-ppt", type=float, default=3.1622776601683795,
    help="Link speed (packets per millisecond)")
senderrunner_group.add_argument("-t", "--delay", type=float, default=150.0,
    help="Delay (milliseconds)")
senderrunner_group.add_argument("-q", "--mean-on", type=float, default=1000.0,
    help="Mean on duration (milliseconds)")
senderrunner_group.add_argument("-w", "--mean-off", type=float, default=1000.0,
    help="Mean off duration (milliseconds)")
senderrunner_group.add_argument("-b", "--buffer-size", type=str, default="inf",
    help="Buffer size, a number or 'inf' for infinite buffers")
senderrunner_group.add_argument("-i", "--interval", type=float, default=0.1,
    help="Logging interval (seconds)")
senderrunner_group.add_argument("-T", "--sim-time", type=float, default=100,
    help="Simulation time to run for (seconds)")
parser.add_argument("-O", "--plots-dir", type=str, default=None,
    help="Directory to place output files in.")
parser.add_argument("--plots-only", action="store_true", default=False,
    help="Only generate plots, not animations")
parser.add_argument("--animations-only", action="store_true", default=False,
    help="Only generate animations, not plots")
parser.add_argument("--start-time", type=float, default=0,
    help="Start plotting from this time")
parser.add_argument("--whiskers-overlay", action="store_true", default=False,
    help="Overlay information about whiskers")
args = parser.parse_args()

# First, try reading it as a data file
data = datautils.read_data_file(args.inputfile)

# If there's nothing in it, it was probably a RemyCC
if not data.run_data:
    parameter_keys = ["nsenders", "link_ppt", "delay", "mean_on", "mean_off", "buffer_size", "interval", "sim_time"]
    parameters = {key: getattr(args, key) for key in parameter_keys}
    datafile = args.inputfile + ".data"
    outfile = args.inputfile + ".out"
    print("Running sender-runner to produce " + datafile)
    runner = SenderRunnerRunner(**parameters)
    runner.run(args.inputfile, datafile=datafile, outfile=outfile)
    data = datautils.read_data_file(datafile)

plotsdir = make_plots_dir(args.plots_dir, args.inputfile)
BaseFigureGenerator.plotsdir = plotsdir
BaseFigureGenerator.start_time = args.start_time
utils.log_arguments(plotsdir, args)

BaseAnimationGenerator.interval = data.settings.log_interval_ticks
TimePlotMixin.overlay_whiskers = args.whiskers_overlay

generators = []

if not args.animations_only:
    generators.extend([
        RawDataTimePlotGenerator("average_throughput"),
        RawDataTimePlotGenerator("average_delay", "ms"),
        RawDataTimePlotGenerator("sending_duration", "ms"),
        RawDataTimePlotGenerator("packets_received", senders=(0,)),
        RawDataTimePlotGenerator("packets_sent", senders=(0,)),
        RawDataTimePlotGenerator("packets_received", senders=(1,)),
        RawDataTimePlotGenerator("packets_sent", senders=(1,)),
        RawDataTimePlotGenerator("total_delay", "ms"),
        RawDataTimePlotGenerator("window_size"),
        RawDataTimePlotGenerator("intersend_time", "ms"),
        RawDataTimePlotGenerator("memory.rec_send_ewma", "ms", senders=(0,)),
        RawDataTimePlotGenerator("memory.rec_rec_ewma", "ms", senders=(0,)),
        RawDataTimePlotGenerator("memory.rtt_ratio", "ms", senders=(0,)),
        RawDataTimePlotGenerator("memory.slow_rec_rec_ewma", "ms", senders=(0,)),
        RawDataTimePlotGenerator("memory.rec_send_ewma", "ms", senders=(1,)),
        RawDataTimePlotGenerator("memory.rec_rec_ewma", "ms", senders=(1,)),
        RawDataTimePlotGenerator("memory.rtt_ratio", "ms", senders=(1,)),
        RawDataTimePlotGenerator("memory.slow_rec_rec_ewma", "ms", senders=(1,)),
        RawDataTimePlotGenerator("sending"),
        RawDataTimePlotGenerator("whisker.window_increment"),
        RawDataTimePlotGenerator("whisker.window_multiple"),
        RawDataTimePlotGenerator("whisker.intersend"),
        DifferenceQuotientTimePlotGenerator("packets_received", "sending_duration", "throughput"),
        DifferenceQuotientTimePlotGenerator("total_delay", "packets_received", "delay"),
        DifferenceTimePlotGenerator("packets_received", "receive times", senders=(0,)),
        DifferenceTimePlotGenerator("packets_sent", "send times", senders=(0,)),
        DifferenceTimePlotGenerator("packets_received", "receive times", senders=(1,)),
        DifferenceTimePlotGenerator("packets_sent", "send times", senders=(1,)),
        SenderVersusSenderPlotGenerator("window_size", (0, 1)),
        SenderVersusSenderPlotGenerator("intersend_time", (0, 1)),
        SenderVersusSenderPlotGenerator("memory.rec_send_ewma", (0, 1)),
        SenderVersusSenderPlotGenerator("memory.rec_rec_ewma", (0, 1)),
        SenderVersusSenderPlotGenerator("memory.rtt_ratio", (0, 1)),
        SenderVersusSenderPlotGenerator("memory.slow_rec_rec_ewma", (0, 1)),
        SingleSenderParametricPlotGenerator(("window_size", "intersend_time"), 0),
        SingleSenderParametricPlotGenerator(("window_size", "intersend_time"), 1),
        SingleSenderParametricPlotGenerator(("memory.rec_send_ewma", "memory.rec_rec_ewma"), 0),
        SingleSenderParametricPlotGenerator(("memory.rec_send_ewma", "memory.rec_rec_ewma"), 1),
        TwoScalesTimePlotGenerator(("memory.rec_send_ewma", 0), ("memory.rec_rec_ewma", 0)),
        TwoScalesTimePlotGenerator(("memory.rec_send_ewma", 0), ("memory.rtt_ratio", 0)),
        TwoScalesTimePlotGenerator(("memory.rec_rec_ewma", 0), ("memory.slow_rec_rec_ewma", 0)),
        TwoScalesTimePlotGenerator(("memory.rtt_ratio", 0), ("whisker.intersend", 0)),
        TwoScalesTimePlotGenerator(("memory.rtt_ratio", 0), ("window_size", 0)),
        TwoScalesTimePlotGenerator(("memory.rec_rec_ewma", 0), ("whisker.window_multiple", 0)),
        TwoScalesTimePlotGenerator(("memory.rec_send_ewma", 0), ("whisker.window_multiple", 0)),
        TwoScalesTimePlotGenerator(("memory.rec_rec_ewma", 0), ("whisker.window_increment", 0)),
        TwoScalesTimePlotGenerator(("memory.rec_send_ewma", 0), ("whisker.window_increment", 0)),
        TwoScalesTimePlotGenerator(("whisker.window_increment", 0), ("whisker.window_multiple", 0)),
        TwoScalesTimePlotGenerator(("whisker.window_increment", 0), ("whisker.intersend", 0)),
        TwoScalesTimePlotGenerator(("whisker.intersend", 0), ("whisker.window_multiple", 0)),
        TwoScalesTimePlotGenerator(("whisker.window_increment", 0), ("window_size", 0)),
        TwoScalesTimePlotGenerator(("whisker.window_multiple", 0), ("window_size", 0)),
        TwoScalesTimePlotGenerator(("window_size", 0), ("intersend_time", 0)),
    ])

if not args.plots_only:
    generators.extend([
        SenderVersusSenderAnimationGenerator("window_size", (0, 1)),
        SenderVersusSenderAnimationGenerator("intersend_time", (0, 1)),
        SenderVersusSenderAnimationGenerator("memory.rec_send_ewma", (0, 1)),
        SenderVersusSenderAnimationGenerator("memory.rec_rec_ewma", (0, 1)),
        SenderVersusSenderAnimationGenerator("memory.rtt_ratio", (0, 1)),
        SenderVersusSenderAnimationGenerator("memory.slow_rec_rec_ewma", (0, 1)),
        SingleSenderParametricAnimationGenerator(("window_size", "intersend_time"), 0),
        SingleSenderParametricAnimationGenerator(("window_size", "intersend_time"), 1),
        SingleSenderParametricAnimationGenerator(("memory.rec_send_ewma", "memory.rec_rec_ewma"), 0),
        SingleSenderParametricAnimationGenerator(("memory.rec_send_ewma", "memory.rec_rec_ewma"), 1),
        MultiVariableParametricGridAnimationGenerator(
            ("memory.rec_send_ewma", 0),
            ("memory.rec_send_ewma", 1),
            ("memory.rec_rec_ewma", 0),
            ("memory.rec_rec_ewma", 1),
            ("memory.rtt_ratio", 0),
            ("memory.rtt_ratio", 1),
            ("memory.slow_rec_rec_ewma", 0),
            ("memory.slow_rec_rec_ewma", 1),
        )
    ])

for run_data in data.run_data:
    for generator in generators:
        generator.generate(datautils.RunData(run_data, start_time=args.start_time, whiskers=data.whiskers))
