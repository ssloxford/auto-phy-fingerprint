import sys
import os
import time
import numpy as np
import zmq
import logging
import json
import argparse
import h5py
import signal
import uuid

###########################

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s|%(message)s', level=logging.INFO)

ap = argparse.ArgumentParser(description="Replay an HDF5 file of bursts.")
ap.add_argument("send_bind_addr", type=str, help="Address to bind and publish from as ZMQ PUB")
ap.add_argument("dataset_filename", type=str, help="Filename for HDF5 file")
ap.add_argument("topic", type=str, default="ADS-B", help="Topic to publish to")
args = ap.parse_args()

logging.info(f"Opening HDF5 file at {args.dataset_filename}")
inf = h5py.File(args.dataset_filename, "r")

context = zmq.Context()

logging.info(f"Setting up ZMQ PUB socket at {args.send_bind_addr}")
outsocket = context.socket(zmq.PUB)
outsocket.setsockopt(zmq.SNDHWM, 1024)	#1024 messages ~= 32MiB if burst is 4096 complex samples long
outsocket.bind(args.send_bind_addr)

logging.info(f"Publishing on topic \"{args.topic}\"")

dataset_names = list(inf)
if "inds" not in dataset_names or "outds" not in dataset_names:
    logging.error("Missing expected dataset(s) 'inds' &/or 'outds', exiting")
    exit(1)

record_count = len(inf["inds"])

for ds in dataset_names:
    print((ds, len(inf[ds])))


logging.info(f"Pausing for 5 seconds, to allow downstream ZMQ connections to establish")
time.sleep(5)

logging.info(f"Commencing replay")
for bursti in range(record_count):

    burst_twochan = inf["inds"][bursti,:]
    burst = burst_twochan.reshape((burst_twochan.shape[0]*2,)).view(np.complex64)

    #burst = burst_real.astype(np.complex64) +
    #identifier = inf["outds"][bursti]
    msg = inf["meta_datahex"][bursti].tobytes().decode("utf-8")
    if "meta_uuid" in inf:
        msguuid = inf["meta_uuid"][bursti].tobytes().decode("utf-8")
    else:
        msguuid = str(uuid.uuid4())
    if "meta_msgtime" in inf:
        msgtime = float(inf["meta_msgtime"][bursti][0])
    else:
        msgtime = 0
    if "meta_raw" in inf:
        msg_rawmeta = inf["meta_raw"][bursti]
    else:
        msg_rawmeta = None
    if "meta_byteindex" in inf:
        msg_byteindex = str(inf["meta_byteindex"][bursti][0])
    else:
        msg_byteindex = None

    #iterate over other dataset_names
    #build a message
    #send it downstream
    #wait for rate limiting


    logging.debug("Annotating verification and passing message downstream")
    topic = args.topic.encode("utf-8")
    jmeta = { "decode.msg": msg, "uuid": msguuid, "msgtime": msgtime, "trueid": inf["outds"][bursti][0].tobytes().decode("utf-8"), "byteindex": msg_byteindex, "rawmeta": msg_rawmeta }
    newmeta = json.dumps(jmeta).encode("utf-8")
    outdata = burst			#pass on the original, not our masked copy
    outsocket.send_multipart([topic, newmeta, outdata])

    bursti += 1

    #time.sleep(0.1)
    time.sleep(0.05)
    #time.sleep(0.02)

    if bursti % 10 == 0:
        logging.info(f"Replayed {bursti} bursts")
        #time.sleep(0.5)

time.sleep(5)

inf.close()
