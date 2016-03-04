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

    def get_raw_data(self, sender, attrname):
        """Retrieves the attribute specified by `attrname` from each data point,
        for the sender with index `sender`, and returns it in a list."""
        attrnames = attrname.split('.')
        if attrnames[0] == "whisker": # special case
            return self.get_whisker_data(sender, attrnames[1])

        result = [getattr(point.sender_data[sender], attrnames[0]) for point in self.pb.point
                if self._in_range(point)]
        for attr in attrnames[1:]:
            result = [getattr(point, attr) for point in result]
        return result

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

    def get_whisker_data(self, sender, attrname):
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
