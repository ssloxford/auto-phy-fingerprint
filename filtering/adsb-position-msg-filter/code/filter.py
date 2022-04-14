import logging
import argparse
import os
import numpy as np
import zmq
import json
import time

import pyModeS as pms


#########################################

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s|%(message)s', level=logging.INFO)

ap = argparse.ArgumentParser(description="Handle a stream of bursts, perform verification on each one via a specified model and annotate them with the result for downstream.")
ap.add_argument("recv_connect_addr", type=str, help="Connect address of upstream ZMQ PUB")
ap.add_argument("send_bind_addr", type=str, help="Bind address for ZMQ PUB")
args = ap.parse_args()


logging.info("Initialising ZMQ")
context = zmq.Context()

logging.info(f"Setting up ZMQ SUB socket connecting to {args.recv_connect_addr}")
insocket = context.socket(zmq.SUB)
insocket.connect(args.recv_connect_addr)
insocket.subscribe("ADS-B")

logging.info(f"Setting up ZMQ PUB socket at {args.send_bind_addr}")
outsocket = context.socket(zmq.PUB)
outsocket.setsockopt(zmq.SNDHWM, 1024)	#1024 messages ~= 32MiB if burst is 4096 complex samples long
#outsocket.setsockopt(zmq.SNDBUF, 1024*1024)		#based on default max buffer allowed in Ubuntu 20.04
outsocket.bind(args.send_bind_addr)

logging.info("Commencing filtering")
msg_count = 0
pass_count = 0

while True:
	(topic, meta, burst) = (None, None, None)		#be on the safe side and break quickly if no new message received in some weird way, don't continue with old values
	if insocket.poll(5) != 0: # check if there is a message on the socket
		(topic, meta, burst) = insocket.recv_multipart()
		logging.debug(f"Received message of len {len(topic) + len(meta) + len(burst)} bytes")
	else:
		time.sleep(0.05) # wait 100ms and try again
		continue

	msg_count += 1

	#get metadata
	jmeta = json.loads(meta)

	msguuid = jmeta["uuid"]
	logging.debug(f"Message UUID: {msguuid}")

	msg = jmeta["decode.msg"]
	icao = msg[2:8]										#TODO: this should probably be provided by the demod, as it's so easy to get there
	tc = pms.adsb.typecode(msg)

	#RB: removed filter
	#if tc < 9 or tc > 18:
	#	logging.debug("Message outside of valid filter, discarding")
	#	continue

	topic = b"ADS-B"
	outsocket.send_multipart([topic, meta, burst])

	logging.debug(f"Sent message of len {len(topic) + len(meta) + len(burst)} bytes")

	if msg_count % 100 == 0:
		logging.info(f"Passed {pass_count} messages of total {msg_count}")

	pass_count += 1
