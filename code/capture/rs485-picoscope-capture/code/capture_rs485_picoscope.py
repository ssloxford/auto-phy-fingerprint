import logging
import argparse
import numpy as np
import matplotlib.pyplot as plt
import serial
import time
import os
import zmq
import json
import uuid

from PicoScope5000Wrapper import PicoScope5000
from TTYIdentifier import TTYIdentifier


BAUD_RATE = 115200
NUM_OF_RUNS = 2500

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s|%(message)s', level=logging.INFO)

ap = argparse.ArgumentParser(description="Trigger a series of RS-485 messages from all attached ttyUSB devices, capture the waveforms and publish them to a ZMQ PUB socket.")
ap.add_argument("bind_addr", type=str, help="Bind address for ZMQ")

args = ap.parse_args()

#set up stream
logging.info(f"Setting up ZMQ PUB socket at addr {args.bind_addr}")
zmqcontext = zmq.Context()
socket = zmqcontext.socket(zmq.PUB)
socket.setsockopt(zmq.LINGER, 100)
socket.setsockopt(zmq.SNDHWM, 1024)	#1024 messages ~= 32MiB if burst is 4096 complex samples long
socket.bind(args.bind_addr)

logging.info("Initialising Picoscope")
SCOPE_TIMEBASE = 5	#5 = (32ns/31.25MSPS)
p = PicoScope5000()
p.setTrigger(p.channelb, 2400, 0, 5000)
p.setCaptureSize(500, 2900*12-500)		#2900 samps per byte at 115200 baud * 12 bytes
p.setTimebase(SCOPE_TIMEBASE)
samp_rate = 1.0/(2**(SCOPE_TIMEBASE-1) / 5e8)		#using 12 bit mode so 5e8
print(f"Capturing at {samp_rate} SPS, {samp_rate/1e6} MSPS")

logging.info("Identifying RS-485 devices")
tty_identifier = TTYIdentifier()
device_identities = tty_identifier.identify()

serials = { ttyname: serial.Serial(d_id["ttypath"], BAUD_RATE) for (ttyname, d_id) in device_identities.items() }

logging.info("Commencing capture")
for runi in range(NUM_OF_RUNS):
	print(f"Capture run {runi}")
	
	msg = os.urandom(12)
	
	for (tty, device_id) in device_identities.items():
		p.runBlockCapture()

		logging.debug("Sending message on {tty}")
		ser = serials[tty]
		ser.write(msg)

		logging.debug("Awaiting trigger")
		p.awaitCaptureComplete()	
		logging.debug("Retrieving data for both channels")
		(dA, dB) = p.retrieveCaptureData([p.channela, p.channelb])
		dA = np.array(dA).astype(np.float32)
		dB = np.array(dB).astype(np.float32)

		##plt.subplot(2, 1, 1)
		##plt.plot(dA)
		##plt.plot(dB)
		##plt.ylim((-5000, 5000))
		##plt.subplot(2, 1, 2)
		#plt.plot(dB - dA)
		##plt.plot(dA - dB)
		#plt.ylim((-5000, 5000))
		##plt.show(block=False)
		##plt.pause(0.2)
		##plt.pause(1.0)
		##plt.show()
		##plt.clf()
		
		metaj = dict()
		metaj["source"] = "capture-rs485-picoscope"
		metaj["tx"] = device_id["deviceid"]
		metaj["msg"] = msg.hex()
		metaj["rxtime"] = str(time.time())
		metaj["uuid"] = str(uuid.uuid4())
		
		topic = b"RS-485"
		meta = json.dumps(metaj).encode("utf-8")
		socket.send_multipart([topic, meta, dA, dB])

		#time.sleep(0.01)		#seems fine for pcie SSD
		time.sleep(0.1)			#delayed a bit for usb HDD on congested USB bus

	#plt.show()
	##plt.savefig(f"{runi}.png")
	##plt.clf()

p.stopScope()
p.close()

for (tty, s) in serials.items():
	s.close()
	
socket.close()