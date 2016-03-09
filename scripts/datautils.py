import sys
import os
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "protobufs"))
    import simulationresults_pb2
except ImportError as e:
    if "google.protobuf" in str(e):
        print("This script requires google.protobuf. Run: sudo apt-get install python-protobuf")
    else:
        print("Run 'make' in the directory one level above this one before using this script.")
    exit(1)

def read_data_file(logfilename):
    logfile = open(logfilename, 'rb')
    data = simulationresults_pb2.SimulationsData()
    data.ParseFromString(logfile.read())
    logfile.close()
    return data

def contains_memory(memoryrange, memory):
    """Returns True if the given `memory` is in `memoryrange`, False if not."""
    for field, value in memoryrange.lower.ListFields():
        if getattr(memory, field.name) < value:
            return False
    for field, value in memoryrange.upper.ListFields():
        if getattr(memory, field.name) > value:
            return False
    return True

def find_whisker(tree, memory):
    """Returns the whisker in the whisker tree for the given memory."""
    while tree.children:
        for child in tree.children:
            if contains_memory(child.domain, memory):
                tree = child
                break # then continue in while loop
        else:
            raise RuntimeError("Couldn't find whisker for {!r}".format(point.memory))
    assert tree.HasField("leaf"), "WhiskerTree has neither leaf nor children"
    assert contains_memory(tree.leaf.domain, memory)
    return tree.leaf

class RunData(object):
    """Provides functions for extracting data from a SimulationRunData protobuf."""

    RAW_ATTRIBUTES = [
        "average_throughput",
        "average_delay",
        "sending_duration",
        "packets_received",
        "packets_sent",
        "packets_in_flight",
        "total_delay",
        "window_size",
        "intersend_time",
        "sending",
    ]

    MEMORY_ATTRIBUTES = [
        "rec_send_ewma",
        "rec_rec_ewma",
        "rtt_ratio",
        "slow_rec_rec_ewma",
    ]

    WHISKER_ATTRIBUTES = [
        "window_increment",
        "window_multiple",
        "intersend",
    ]

    DIFFERENCE_QUOTIENT_ATTRIBUTES = {
        "throughput": ("packets_received", "sending_duration"),
        "delay": ("total_delay", "packets_received"),
    }

    DIFFERENCE_ATTRIBUTES = {
        "receive_times": ("packets_received",),
        "send_times": ("packets_sent",),
    }

    INTEREVENT_ATTRIBUTES = {
        "actual_interreceive": ("packets_received", 1000),
        "actual_intersend": ("packets_sent", 1000),
    }

    def __init__(self, pb, start_time=0, end_time=None, whiskers=None):
        """`pb` is a protobuf for a SimulationRunData.
        `whiskers` is a Whiskers object."""
        self.pb = pb
        self.whiskers = whiskers
        self.start_time = start_time
        self.end_time = end_time

    def _in_range(self, point):
        return point.seconds >= self.start_time and (self.end_time is None or point.seconds <= self.end_time)

    @property
    def num_senders(self):
        return self.pb.config.num_senders

    def get_times(self):
        """Returns a list of times, each time being a data point in the run
        represented by this instance."""
        return [point.seconds for point in self.pb.point if self._in_range(point)]

    def get_sending(self):
        """Returns a list of tuples of booleans, each tuple being for a point in
        time. The times correspond to those returned by `self.get_times()`, each
        element of the tuple representing one sender. For example, `[(True,
        False), (False, False)]` means there are two senders, the first of which
        was on at the beginning.
        """
        return [tuple(data.sending for data in point.sender_data) for point in self.pb.point
                if self._in_range(point)]

    def get_data(self, sender, name):
        if name in self.RAW_ATTRIBUTES:
            return self._get_raw_data(sender, name)
        elif name in self.MEMORY_ATTRIBUTES:
            return self._get_memory_data(sender, name)
        elif name in self.WHISKER_ATTRIBUTES:
            return self._get_whisker_data(sender, name)
        elif name in self.DIFFERENCE_QUOTIENT_ATTRIBUTES:
            return self._get_difference_quotient_data(sender, *self.DIFFERENCE_QUOTIENT_ATTRIBUTES[name])
        else:
            raise ValueError("Unknown attribute for get_data(): " + repr(name))

    def get_time_data(self, sender, name):
        """Retrieves the property specified by `name` from each data point,
        for the sender with index `sender`, and returns it in a list."""
        if name in self.RAW_ATTRIBUTES:
            return self.get_times(), self._get_raw_data(sender, name)
        elif name in self.MEMORY_ATTRIBUTES:
            return self.get_times(), self._get_memory_data(sender, name)
        elif name in self.WHISKER_ATTRIBUTES:
            return self.get_times(), self._get_whisker_data(sender, name)
        elif name in self.DIFFERENCE_QUOTIENT_ATTRIBUTES:
            return self.get_times(), self._get_difference_quotient_data(sender, *self.DIFFERENCE_QUOTIENT_ATTRIBUTES[name])
        elif name in self.DIFFERENCE_ATTRIBUTES:
            return self._get_difference_data(sender, *self.DIFFERENCE_ATTRIBUTES[name])
        elif name in self.INTEREVENT_ATTRIBUTES:
            return self._get_interevent_data(sender, *self.INTEREVENT_ATTRIBUTES[name])
        else:
            raise ValueError("Unknown attribute for get_time_data(): " + repr(name))

    def _get_raw_data(self, sender, attrname):
        """Retrieves the attribute specified by `attrname` from each data point,
        for the sender with index `sender`, and returns it in a list."""
        return [getattr(point.sender_data[sender], attrname)
                for point in self.pb.point if self._in_range(point)]

    def _get_memory_data(self, sender, attrname):
        """Retrieves the attribute of memory specified by `attrname` from each
        data point, for the sender with index `sender`, and returns it in a
        list."""
        return [getattr(point.sender_data[sender].memory, attrname)
                for point in self.pb.point if self._in_range(point)]

    def _get_whisker_data(self, sender, attrname):
        """Returns a list, each element being the attribute of the whisker
        specified by `attrname` for the whisker that would be active at each a
        point in time. The times correspond to those returned by
        `self.get_times()`.
        """
        # This is a little hacky, it should be refactored into a proper
        # structure for Memory and MemoryRange if it needs to be touched again.
        assert self.whiskers is not None, "RunData needs a whiskers object for this function"
        data = []
        for point in filter(self._in_range, self.pb.point):
            whisker = find_whisker(self.whiskers, point.sender_data[sender].memory)
            value = getattr(whisker, attrname)
            data.append(value)
        return data

    def _get_difference_quotient_data(self, sender, numerator, denominator):
        """Returns data of the form:
            y[i] = (b[i] - b[i-1]) / (a[i] - a[i-1])
        where a and b are both raw data."""
        numerator_values = self._get_raw_data(sender, numerator)
        denominator_values = self._get_raw_data(sender, denominator)
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

    def _get_difference_data(self, sender, attrname):
        """Returns data of the form:
            y(t[n]) = x(t[n]) - x(t[n-1])
        where x is raw data, and t[] are the times that x changes."""
        t_raw = self.get_times()
        y_raw = self._get_raw_data(sender, attrname)
        t = []
        y = []
        for i in xrange(1, len(t_raw)):
            d = y_raw[i] - y_raw[i-1]
            if d != 0:
                if t_raw[i] == t_raw[i-1] and len(y) > 0:
                    y[-1] += d
                else:
                    t.append(t_raw[i])
                    y.append(d)
        return t, y

    def _get_interevent_data(self, sender, attrname, multiplier=1):
        """Returns data of the form:
            y(t[n]) = t[n] - t[n-1]
        where t[] are the times that the raw data changes."""
        t_raw = self.get_times()
        y_raw = self._get_raw_data(sender, attrname)
        t = []
        y = []
        t_last = None
        for i in xrange(1, len(t_raw)):
            d = y_raw[i] - y_raw[i-1]
            if d != 0:
                if t_last is not None:
                    t.append(t_raw[i])
                    y.append((t_raw[i] - t_last) * multiplier)
                t_last = t_raw[i]
        return t, y


    def get_whisker_bounds(self, sender, attrname):
        """Returns two lists. The first list is the lower bound of the domain of
        the whisker that would be active at each point in time. The second list
        is the upper bound. The time for each element in the list (i.e., for
        each tuple) corresponds to that in the list returned by
        `self.get_whisker_change_times()`. This can be used to track when
        signals reach the boundary of the whisker.
        """
        assert self.whiskers is not None, "RunData needs a whiskers object for this function"
        lower = []
        upper = []
        last_whisker = None
        for point in filter(self._in_range, self.pb.point):
            whisker = find_whisker(self.whiskers, point.sender_data[sender].memory)
            if whisker == last_whisker:
                continue
            lower.append(getattr(whisker.domain.lower, attrname))
            upper.append(getattr(whisker.domain.upper, attrname))
            last_whisker = whisker
        return lower, upper

    def get_whisker_change_times(self, sender):
        """Returns a list of times where the whisker changes."""
        assert self.whiskers is not None, "RunData needs a whiskers object for this function"
        times = []
        last_whisker = None
        for point in filter(self._in_range, self.pb.point):
            whisker = find_whisker(self.whiskers, point.sender_data[sender].memory)
            if whisker != last_whisker:
                times.append(point.seconds)
            last_whisker = whisker
        return times
