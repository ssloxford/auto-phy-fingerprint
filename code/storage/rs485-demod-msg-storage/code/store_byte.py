import sys
import os
import time
import numpy as np
import zmq
import logging
import json
import argparse
import h5py



###########################

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s|%(message)s', level=logging.INFO)

ap = argparse.ArgumentParser(description="Listen to a stream of bursts and record them in an HDF5 file.")
ap.add_argument("recv_connect_addr", type=str, help="Connect address of upstream ZMQ PUB")
ap.add_argument("dataset_filename", type=str, help="Filename for HDF5 file")
ap.add_argument("topic", type=str, help="Topic to subscribe to")
args = ap.parse_args()


logging.info(f"Creating HDF5 file at {args.dataset_filename}")
outf = h5py.File(args.dataset_filename, "a")

context = zmq.Context()

logging.info(f"Setting up ZMQ SUB socket connecting to {args.recv_connect_addr}")
insocket = context.socket(zmq.SUB)
insocket.connect(args.recv_connect_addr) 
#insocket.setsockopt(zmq.SUBSCRIBE, b'') # subscribe to topic of all (needed or else it won't work)

insocket.subscribe(args.topic)
logging.info(f"Subscribed to topic \"{args.topic}\"")

if not "inds" in outf and "outds" not in outf and "meta_datahex" not in outf:
	outf.create_dataset("inds", shape=(1, 2750, 2), maxshape=(None, 2750, 2), dtype=np.float32)
	outf.create_dataset("outds", shape=(1, 1), maxshape=(None, 1), dtype="S32")
	outf.create_dataset("meta_datahex", shape=(1, 1), maxshape=(None, 1), dtype="S2")			#2 characters as each byte is 2 hex chars
	outf.create_dataset("meta_byteindex", shape=(1, 1), maxshape=(None, 1), dtype=int)
	outf.create_dataset("meta_storetime", shape=(1, 1), maxshape=(None, 1), dtype=np.float64)	#needs to be float64 or it'll truncate the storage time (to 128s resolution)
	outf.create_dataset("meta_raw", shape=(1, 1), maxshape=(None, 1), dtype=str)				#write the whole json metadata there
	bursti = 0
else:
	bursti = outf["inds"].shape[0]

#TODO: when I have a new enough version of libhdf5, move to swmr mode to allow copies of the file to be taken while streaming to it (and for crash protection)
#outf.swmr_mode = True
	
while True:
	if insocket.poll(10) != 0: # check if there is a message on the socket
		(topic, meta, dA, dB) = insocket.recv_multipart()
		logging.debug(f"Received message of len {len(topic) + len(meta) + len(dA) + len(dB)} bytes")
	else:
		time.sleep(0.05) # wait 50ms and try again
		continue

	jmeta = json.loads(meta)

	logging.debug((meta, len(dA)+len(dB)))
	
	burstA = np.frombuffer(dA, dtype=np.float32)
	burstB = np.frombuffer(dB, dtype=np.float32)
	if outf["inds"].shape[0] == bursti:									#TODO: resizing by one each time is probably horribly un-performant
		outf["inds"].resize(bursti+1, axis=0)
		outf["outds"].resize(bursti+1, axis=0)
		outf["meta_datahex"].resize(bursti+1, axis=0)
		outf["meta_byteindex"].resize(bursti+1, axis=0)
		outf["meta_storetime"].resize(bursti+1, axis=0)
		outf["meta_raw"].resize(bursti+1, axis=0)

	outf["inds"][bursti,:,0] = burstA
	outf["inds"][bursti,:,1] = burstB
	outf["outds"][bursti,:] = np.string_(jmeta["tx"])
	outf["meta_datahex"][bursti,:] = np.string_(jmeta["decode.msgbyte"])
	outf["meta_byteindex"][bursti,:] = int(jmeta["decode.bytenum"])
	outf["meta_storetime"][bursti,:] = time.time()
	outf["meta_raw"][bursti,:] = meta.decode("utf-8")

	bursti += 1
	
	if bursti % 100 == 0:
		logging.info(f"Stored {bursti} bursts (with meta)")