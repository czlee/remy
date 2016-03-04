#!/usr/bin/python2
import datautils
import argparse
from collections import Counter

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("inputfile", type=str,
    help="Input file (data file)")
parser.add_argument("--start-time", type=float, default=0,
    help="Start plotting from this time")
parser.add_argument("-n", type=int, default=5,
    help="Number of whiskers to print for each sender in each run")
args = parser.parse_args()

data = datautils.read_data_file(args.inputfile)

def print_most_used_whiskers(run_data, whiskers, sender_id):
    points = [point for point in run_data.point if point.seconds >= args.start_time]
    counter = Counter()
    for point in points:
        whisker = datautils.find_whisker(whiskers, point.sender_data[sender_id].memory)
        counter[str(whisker)] += 1 # whiskers aren't hashable, strings are

    for whisker, freq in counter.most_common(args.n):
        print("Used {} times:".format(freq))
        print(whisker)

for i, run_data in enumerate(data.run_data):
    for j in range(run_data.config.num_senders):
        print("=== Run {}, sender {} ===".format(i, j))
        print_most_used_whiskers(run_data, data.whiskers, j)