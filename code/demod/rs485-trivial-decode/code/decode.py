#!/usr/bin/python3
# -*- coding: utf-8 -*-

# zmq_SUB_proc.py
# Author: Marc Lichtman

import logging
import argparse
import zmq
import numpy as np
import time
import matplotlib.pyplot as plt
import json
import uuid

class UARTDecoder:
	def decode(self, chA, chB):
		ch = chB - chA
		
		timing = 32e-9
		thresh = 1250		#1.25V
		baud = 115200
		
		times = np.arange(0, len(ch)*timing, timing)
		samps_per_bit = (1/baud) / timing
		#print(f"Expect {samps_per_bit} samps per bit")
		samps_per_bit = int(samps_per_bit)
		#print(f"Rounded to {samps_per_bit} samps per bit")
		
		#find the start, but don't throw away before it (we may need a few samples before the trigger for the first byte)
		start = np.argwhere(ch > thresh)[0][0]
		
		#downsample
		sampling_points = [start]
		avgs = np.zeros((len(ch) - start) // samps_per_bit)
		timing_offset = 0								#use to accomodate clock offset
		for i in range(len(avgs)):
			bs = start + i*samps_per_bit + timing_offset
			be = start + (i+1)*samps_per_bit + timing_offset
			if bs > len(ch):
				break									#we ran over the end due to timing offset advancing
			sampling_points.append(be)
			avgs[i] = np.mean(ch[bs:be])
			
			#update the timing offset to handle bad timekeeping on shitty devices
			win = 50					#size of window in which to search
			diffthresh = 250			#0.25V
			before = ch[be-win:be+win]
			after = ch[be-win-1:be+win-1]
			if len(before) == len(after) and len(before) > 0:				#once we reach the end this stops working, but we also don't care then so skip it
				diffs = np.abs(before - after)
				if np.max(diffs) > diffthresh:
					maxdiffi = np.argmax(diffs)
					#print(maxdiffi)
					timing_offset += (maxdiffi - win)
		
		#threshold
		hardsyms = (avgs > thresh).astype(int)
		
		#read bit values
		bits = []
		state = 0
		statechanges = [0]
		for i in range(len(hardsyms)):
			sym = hardsyms[i]
			if state == 0:						#expect start bit
				if sym != 1:
					#print(f"{i}: Bad start bit")
					pass
				else:
					state = 1
					statechanges.append(state)
			elif state > 0 and state < 9:		#expect data bit
				bits.append(1 - sym)				#high is 0, low is 1 -- so must reverse from symbols to get actual bit values here
				state += 1
				statechanges.append(state)
			elif state == 9:
				if sym != 0:
					#print(f"{i}: Bad stop bit")
					pass
				else:
					state = 0
					statechanges.append(state)
			else:
				raise ValueError(f"{i}: Bad state in decoder")	
			
		bytevals = np.packbits(bits, bitorder="little")	
		bytevalshex = "".join(["{:02x}".format(b) for b in bytevals])
		
		#extract a fixed length section for each byte, centred on its midpoint, irrespective of the actual length of it
		byte_wave_extract_points = []
		for i in range(len(statechanges)):		#statechanges is always same or shorter than sampling_points
			p = sampling_points[i]
			s = statechanges[i]
			if s == 9:
				BYTE_WAVE_EXTRACT_LENGTH = 2750				#how big a window should there be around the midpoint
				BYTE_WAVE_MIDPOINT_OFFSET = -40				#'fudge factor' because we want to catch the early start of the first bit (from idle) and want to avoid the start of the next bit (where it's data dependent)
				byte_wave_true_start = sampling_points[i-9]			#this is the actual rising edge
				byte_wave_true_end = sampling_points[i+1]			#this is the actual falling edge
				byte_wave_midpoint = int( ((byte_wave_true_end - byte_wave_true_start) / 2) + byte_wave_true_start )	#rounding midpoint left
				byte_wave_midpoint += BYTE_WAVE_MIDPOINT_OFFSET 
				#byte_wave_length = byte_wave_true_end - byte_wave_true_start
				byte_wave_extract_start = byte_wave_midpoint - (BYTE_WAVE_EXTRACT_LENGTH//2)
				byte_wave_extract_end = byte_wave_midpoint + (BYTE_WAVE_EXTRACT_LENGTH//2)
				#print(f"Section: {byte_wave_true_start}--{byte_wave_true_end}, midpoint = {byte_wave_midpoint}, length = {byte_wave_true_end-byte_wave_true_start}")
				byte_wave_extract_points.append((byte_wave_extract_start, byte_wave_extract_end))
		
		#print(bits)
		#print(bytevals)
		#print([chr(b) for b in bytevals])
		#print(bytevalshex)
		
		#if bytevalshex != "aaaaaaaaaaaaaaaaaaaaaaaa":
		if False:
			plt.subplot(3,1,1)
			#plt.plot(times, ch)
			plt.plot(ch)
			plt.plot(np.abs(ch[1:]-ch[:-1]))
			for i in range(len(hardsyms)):
				plt.plot([i*samps_per_bit]*2, [0,2000], c="black")
			for i in range(len(sampling_points)):
				plt.plot([sampling_points[i]]*2, [0,2000], c="gray")
			plt.subplot(3,1,2)
			plt.plot(avgs)
			plt.subplot(3,1,3)
			plt.plot(hardsyms)
			plt.show()
			
		return (bytevalshex, byte_wave_extract_points)

	
#################################################################

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s|%(message)s', level=logging.INFO)

ap = argparse.ArgumentParser(description="Receive RS-485 bursts and decode them. Outputs equal-length sections around each byte, along with the decoded values.")
ap.add_argument("conn_addr", type=str, help="Connect address for subscribing ZMQ")
ap.add_argument("bind_addr", type=str, help="Bind address for publishing ZMQ")

args = ap.parse_args()

#set up publish stream
logging.info(f"Setting up ZMQ PUB socket at addr {args.bind_addr}")
zmqcontext = zmq.Context()
out_socket = zmqcontext.socket(zmq.PUB)
out_socket.setsockopt(zmq.LINGER, 100)
out_socket.setsockopt(zmq.SNDHWM, 1024)	#1024 messages ~= 32MiB if burst is 4096 complex samples long
out_socket.bind(args.bind_addr)

#set up listen subscription
logging.info(f"Setting up ZMQ SUB socket to addr {args.conn_addr}")
in_socket = zmqcontext.socket(zmq.SUB)
in_socket.connect(args.conn_addr) # connect, not bind, the PUB will bind, only 1 can bind
in_socket.setsockopt(zmq.SUBSCRIBE, b'') # subscribe to topic of all (needed or else it won't work)

#start = time.time()
#msgi = 0

while True:
	if in_socket.poll(10) != 0: # check if there is a message on the socket
		parts = in_socket.recv_multipart() # grab the message
		
		(topic, jmeta, dA, dB) = parts
		
		chA = np.frombuffer(dA, dtype=np.float32, count=-1) # make sure to use correct data type (complex64 or float32); '-1' means read all data in the buffer
		chB = np.frombuffer(dB, dtype=np.float32, count=-1) # make sure to use correct data type (complex64 or float32); '-1' means read all data in the buffer
		
		meta = json.loads(jmeta)
		realdata = meta["msg"]
		msguuid = meta["uuid"]				#take the uuid and distribute it across all the byte sub-bursts within this one 12-byte burst
		(decodedata, extract_points) = UARTDecoder().decode(chA, chB)
		logging.debug(f"{realdata} vs. {decodedata} -> {realdata == decodedata}")
		
		#sanity check
		if len(decodedata) != len(extract_points) * 2:
			logging.warn(f"Mismatched length between decoded and extraction points. Ignoring. ({len(decodedata)}, {len(extract_points)}, {meta['tx']})")
			continue
		
		#for (s, e) in extract_points:
		#	print((s,e))
		#	plt.plot((chB-chA)[s:e])
		#plt.show()
		
		for seci in range(len(extract_points)):
			(s, e) = extract_points[seci]
			secA = chA[s:e]
			secB = chB[s:e]
			meta["decode.msg"] = decodedata
			meta["decode.bytenum"] = seci
			meta["decode.msgbyte"] = decodedata[seci*2:(seci+1)*2]
			meta["decode.msguuid"] = msguuid						#as one burst has been split, we link them with the same msguuid (the original uuid of the full burst)
			meta["uuid"] = str(uuid.uuid4())						#a new uuid value is given to each new byte, to keep the behaviour that it is globally unique for a burst
			jmeta = json.dumps(meta)
			out_socket.send_multipart((topic, jmeta.encode("utf-8"), secA.tobytes(), secB.tobytes()))
		
	else:
		time.sleep(0.1) # wait 100ms and try again



