import sys
from pySDRBurstfile import *
import zmq
import time
import logging
import argparse
import json
import uuid
import glob
import re

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s|%(message)s', level=logging.INFO)

ap = argparse.ArgumentParser(description="Stream a series of bursts from an SDRBurstfile via a ZMQ PUB socket.")
ap.add_argument("input_file", type=str, help="Filename of the .sdrbf file to stream from")
ap.add_argument("bind_addr", type=str, help="Bind address for ZMQ")
ap.add_argument("--rate-limit", type=float, help="Limit messages/second")
ap.add_argument("--loop", action="store_true", help="Repeat file forever")
ap.add_argument("--glob", action="store_true", help="Expand filename as glob and use all matching files?")

args = ap.parse_args()

#set up stream
logging.info(f"Setting up ZMQ PUB socket at addr {args.bind_addr}")
zmqcontext = zmq.Context()
socket = zmqcontext.socket(zmq.PUB)
socket.setsockopt(zmq.LINGER, 100)
socket.setsockopt(zmq.SNDHWM, 1024)	#1024 messages ~= 32MiB if burst is 4096 complex samples long
socket.bind(args.bind_addr)

logging.info(f"Socket bound, pausing to allow connections before streaming")
time.sleep(5)

#stream messages
logging.info(f"Streaming messages")
burst_count, data_byte_count, msg_byte_count = 0, 0, 0
lastreport = time.time()

while True:
	if not args.glob:
		files = [ args.input_file ]
	else:
		files = glob.glob(args.input_file)

	for file in files:
		#open file
		#logging.debug(f"Opening SDRBurstfile at {args.input_file}")
		#bfr = SDRBurstFileReader(args.input_file)

		logging.info(f"Opening SDRBurstfile at {file}")
		bfr = SDRBurstFileReader(file)

		for (b, bm) in bfr.read():
			#msg = bm.encode("utf-8") + b"\x00" + b
			#print(f"Sending msg of len {len(msg)}, containing data of length {len(b)} ({len(b)/8} samps.)")
			#socket.send(msg)
			metaj = json.loads(bm)
			metaj["source"] = "burstfile-streamer"
			metaj["uuid"] = str(uuid.uuid4())

			#capture_start = int(file[22:32])
			capture_start = int(re.match("adsb_.*20000000.0_(\d{10})\.sdrbf", file).groups()[0])
			samprate = 20e6
			msgtime = (int(metaj["start"]) / samprate) + capture_start
			metaj["msgtime"] = msgtime

			topic = b"ADS-B"
			meta = json.dumps(metaj).encode("utf-8")
			socket.send_multipart([topic, meta, b])

			burst_count += 1
			data_byte_count += len(b)
			msg_byte_count += len(topic) + len(meta) + len(b)

			if time.time() - lastreport > 5:
				logging.info(f"Streamed {burst_count} bursts ({data_byte_count} data bytes, {msg_byte_count} msg bytes)")
				lastreport = time.time()

			if args.rate_limit is not None:
				time.sleep(1/args.rate_limit)
		bfr.close()

	if not args.loop:
		break

socket.close()
