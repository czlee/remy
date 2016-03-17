import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "protobufs"))
import dna_pb2
import datautils

treefile = open("poisson-100x.13", 'rb')
tree = dna_pb2.FinTree()
tree.ParseFromString(treefile.read())
treefile.close()

memory = dna_pb2.Memory(rec_send_ewma=0, rec_rec_ewma=0, rtt_ratio=0, slow_rec_rec_ewma=0,
        rtt_diff=0)
parent = None
current = tree
while current.children:
    for child in current.children:
        if datautils.contains_memory(child.domain, memory):
            parent = current
            current = child
            break # then continue in while loop
    else:
        raise RuntimeError("Couldn't find action for {!r}".format(point.memory))
assert current.HasField("leaf"), "Action tree has neither leaf nor children"
assert datautils.contains_memory(current.leaf.domain, memory)

print("Parent, before:")
print parent

action2 = parent.children[1]
parent.leaf.CopyFrom(action2.leaf)
parent.leaf.domain.lower.rtt_diff = 0.0

del parent.children[:]

print("Parent, after:")
print parent

newfile = open("poisson-100x.13-lowfinmod", 'wb')
newfile.write(tree.SerializeToString())
newfile.close()
