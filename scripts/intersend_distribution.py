#!/usr/bin/python2
import datautils
import argparse
import matplotlib.pyplot as plt
from itertools import izip

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("inputfile", type=str,
    help="Input file (data file)")
parser.add_argument("--bins", type=int, default=100,
    help="Number of bins in histogram")
args = parser.parse_args()

data = datautils.read_data_file(args.inputfile)

def plot_intersend_distribution(run_data, actions, sender_id):
    run = datautils.RunData(run_data, actions=actions)
    intersend_times, intersends = run.get_time_data(sender_id, "actual_intersend")
    lambda_times, lambdas = run.get_time_data(sender_id, "lambda")
    lambda_points = izip(lambda_times, lambdas)
    tl_curr, l_curr = lambda_points.next()
    tl_next, l_next = lambda_points.next()
    data = []
    for ti, i in izip(intersend_times, intersends):
        while tl_next <= ti:
            tl_curr, l_curr = tl_next, l_next
            tl_next, l_next = lambda_points.next()
        assert(tl_curr <= ti and ti < tl_next)
        print("{} <= {} < {}, {} * {} = {} [next: {}]".format(tl_curr, ti, tl_next, i, l_curr, i*l_curr, l_next))
        data.append(i * l_curr)
    if len(data) == 0:
        return
    plt.hist(data, bins=args.bins, range=[0,40])
    plt.xlabel("Intersend * lambda")
    plt.ylabel("Number of packets")
    plt.show()

for i, run_data in enumerate(data.run_data):
    for j in range(run_data.config.num_senders):
        plot_intersend_distribution(run_data, data.fins, j)
