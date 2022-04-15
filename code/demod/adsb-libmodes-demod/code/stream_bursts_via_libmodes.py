import sys
import os
import time
import numpy as np
import zmq
import pylibmodes
import pyModeS as pms
import logging
import json
import argparse

def decimate(z, DECIMATION):
	x = np.zeros(len(z)//DECIMATION, dtype=np.complex64)
	for i in range(DECIMATION):
		x += z[i::DECIMATION][:len(x)]
	x /= DECIMATION
	return x

def to_rtl_uint8(x):
	x = x.view(np.float32)
	x *= 128.0
	x += 127.0
	x = x.astype(np.uint8)
	return x

###########################

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s|%(message)s', level=logging.INFO)

ap = argparse.ArgumentParser(description="Handle a stream of bursts, demodulate them via libmodes and send them downstream.")
ap.add_argument("recv_connect_addr", type=str, help="Connect address of upstream ZMQ PUB")
ap.add_argument("send_bind_addr", type=str, help="Bind address for ZMQ PUB")
args = ap.parse_args()


context = zmq.Context()

logging.info(f"Setting up ZMQ SUB socket connecting to {args.recv_connect_addr}")
insocket = context.socket(zmq.SUB)
insocket.connect(args.recv_connect_addr) 
#insocket.setsockopt(zmq.SUBSCRIBE, b'') # subscribe to topic of all (needed or else it won't work)

#set up subscriptions
insocket.subscribe("ADS-B")			#TODO: this should probably be "MODE-S" or even "1090MHz", as the stream includes many non-ADS-B messages too

logging.info(f"Setting up ZMQ PUB socket at {args.send_bind_addr}")
outsocket = context.socket(zmq.PUB)
outsocket.setsockopt(zmq.SNDHWM, 1024)	#1024 messages ~= 32MiB if burst is 4096 complex samples long
outsocket.bind(args.send_bind_addr)

start = time.time()
burst_i = 0

count_pre, count_phase, count_demod_err, count_good = 0,0,0,0

msgtype_counts = {}
msgtype_successes = {}

while True:
	if insocket.poll(10) != 0: # check if there is a message on the socket
		(topic, bm, b) = insocket.recv_multipart()
		logging.debug(f"Received message of len {len(topic) + len(bm) + len(b)} bytes")
	else:
		time.sleep(0.05) # wait 100ms and try again
		continue

	if len(b) >= 19200:										# 240 * 10x decimation * 8 bytes complex64 (could pad with zeros instead to get short bursts out (e.g. 56-bit ones, which might still be interesting))

		z = np.frombuffer(b, dtype=np.complex64)
		DECIMATION = 10
		x = decimate(z, DECIMATION)

		#x -= np.mean(x)										#remove DC (seemed to decrease successful decoding and can't be bothered to debug)
		x /= np.max(np.abs(x))									#normalise to use the full quantised range

		x = to_rtl_uint8(x)

		#set up decoding
		state = pylibmodes.mode_s_t()
		pylibmodes.mode_s_init(state)

		res = pylibmodes.mode_s_detect_result()

		pylibmodes.mode_s_detectfirst(state, res, x)
		if res.processing_error != 0:
			raise ValueError("Error occurred during processing by libmodes (e.g. burst too short)")

		count_pre, count_phase, count_demod_err, count_good = count_pre + res.preamble_found, count_phase + res.phase_corrected, count_demod_err + res.demod_error_count, count_good + res.good_message

		#if res.preamble_found == 1:
		#	print("err: {}, offset: {}, preamble_found: {}, phase_corrected: {}, demod_error_count: {}, delta_test_result: {}, good_message: {}, msgtype: {}, msglen: {}".format(res.processing_error, res.offset, res.preamble_found, res.phase_corrected, res.demod_error_count, res.delta_test_result, res.good_message, res.msgtype, res.msglen))

		#record success stats
		if res.preamble_found == 1 and res.demod_error_count == 0 and res.delta_test_result == 1:
			msgtype_counts[res.msgtype] = 1 if res.msgtype not in msgtype_counts else msgtype_counts[res.msgtype] + 1
			msgtype_successes[res.msgtype] = res.good_message if res.msgtype not in msgtype_successes else msgtype_successes[res.msgtype] + res.good_message

		#extract relevant subsection of burst to save
		if res.good_message == 1 and res.msgtype == 17:
			sec_start = res.offset * 2										#2 byte-values per sample
			sec_end = res.offset * 2 + (res.msglen * 8 * 2 + 16) * 2		#8 bits in msg, 2 samples per bit, 16 samples of preamble, 2 byte-values per sample
			#print(sec_start, sec_end, sec_end - sec_start)

			orig_start = res.offset * DECIMATION							#original is complex64, so no need to double as there is with data passed into libmodes
			orig_end = orig_start + (res.msglen * 8 * 2 + 16) * DECIMATION

			yz = z[orig_start:orig_end]
			decoded = pylibmodes.get_mm_msg(res.mm.msg).hex()
			meta = json.loads(bm)
			meta["decode.phase_corrected"] = res.phase_corrected
			meta["decode.demod_err_count"] = res.demod_error_count
			meta["decode.crcok"] = res.good_message
			meta["decode.msgtype"] = res.msgtype
			meta["decode.msg"] = decoded
			#TODO: add orig_start and orig_end to metadata so downstream can know 'precisely' when the message arrived in sample counts
			meta = json.dumps(meta)

			topic = b"ADS-B"
			outdata = yz.tobytes()
			#msg = meta.encode("utf-8") + b"\x00" + outdata
			logging.debug(f"Sending msg of len {len(topic) + len(meta) + len(outdata)}, containing data of length {len(outdata)} ({len(outdata)/8} samps.)")
			#logging.debug(meta)
			#outsocket.send(msg)
			outsocket.send_multipart([topic, meta.encode("utf-8"), outdata])


		#do a check whether there are any other messages
		rest_of_burst = x[res.offset*2+(res.msglen*8*2+16):]
		#print(("rest", len(rest_of_burst)))
		if len(rest_of_burst) >= 480:
			res = pylibmodes.mode_s_detect_result()
			if res.good_message == 1:
				x = x[res.offset*2+(res.msglen*8*2+16):]
			else:
				x = x[res.offset*2+2:]
			pylibmodes.mode_s_detectfirst(state, res, x)
			if res.preamble_found == 1:
				logging.warning("Warning: Other preamble(s) found (but discarded) after first in burst {}".format(burst_i))

	burst_i += 1

	if burst_i % 1000 == 0:		
		statusmsg = f"Bursts: {burst_i}, Preambles: {count_pre}, Good CRCs: {count_good}"
		logging.info(statusmsg)
		
		msgtype_total = sum([x[1] for x in msgtype_counts.items()])
		msgtypereports = []
		for mt in msgtype_counts:
			mts = msgtype_successes[mt]
			mtc = msgtype_counts[mt]
			mtcp = mtc / msgtype_total
			if mtcp > 0.1:
				msgtypereports.append(f"(Type={mt},Count={mtc}({100.0*mtcp:.2f}%),Success={mts}({100.0*mts/mtc:.2f}%))")
		msgtypemsg = "Message types (>10% total) = " + ", ".join(msgtypereports)
		logging.info(msgtypemsg)
