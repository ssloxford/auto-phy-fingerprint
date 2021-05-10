import sys
from pySDRBurstfile import *
import zmq
import time
import logging
import argparse
import json

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s|%(message)s', level=logging.INFO)

ap = argparse.ArgumentParser(description="Stream a series of bursts from an SDRBurstfile via a ZMQ PUB socket.")
ap.add_argument("input_file", type=str, help="Filename of the .sdrbf file to stream from")
ap.add_argument("bind_addr", type=str, help="Bind address for ZMQ")
ap.add_argument("--rate-limit", type=float, help="Limit messages/second")
ap.add_argument("--loop", action="store_true", help="Repeat file forever")

args = ap.parse_args()

#set up stream
logging.info(f"Setting up ZMQ PUB socket at addr {args.bind_addr}")
zmqcontext = zmq.Context()
socket = zmqcontext.socket(zmq.PUB)
socket.setsockopt(zmq.LINGER, 100)
socket.setsockopt(zmq.SNDHWM, 1024)	#1024 messages ~= 32MiB if burst is 4096 complex samples long
socket.bind(args.bind_addr)

logging.info(f"Socket bound, pausing to allow connections before streaming")
time.sleep(1)

#stream messages
logging.info(f"Streaming messages")
burst_count, data_byte_count, msg_byte_count = 0, 0, 0
lastreport = time.time()

while True:
	#open file
	logging.debug(f"Opening SDRBurstfile at {args.input_file}")
	bfr = SDRBurstFileReader(args.input_file)
	
	for (b, bm) in bfr.read():
		#msg = bm.encode("utf-8") + b"\x00" + b
		#print(f"Sending msg of len {len(msg)}, containing data of length {len(b)} ({len(b)/8} samps.)")
		#socket.send(msg)
		metaj = json.loads(bm)
		metaj["source"] = "burstfile-streamer"
		
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