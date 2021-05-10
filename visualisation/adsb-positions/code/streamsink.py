import logging
import zmq
import time
import json
import pyModeS as pms
import threading
import queue
from pyproj import Transformer
import numpy as np

formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s|%(message)s')
log = logging.getLogger("streamsink.py")
log.setLevel(logging.INFO)

qs = set()

LAT, LON = 51.753037, -1.258651				#Oxford

tra = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

#TODO: deregister queues when sessions close
def register():
	log.info("Registering new update queue")
	q = queue.Queue(1000)
	qs.add(q)
	return q

def deregister(q):
	log.info("Deregistering update queue")
	qs.remove(q)

def getDefaultPosition():
	return tra.transform(LON, LAT)

def streamFromZMQ(addr, topic=""):
	context = zmq.Context()

	log.info(f"Setting up ZMQ SUB socket connecting to {addr}")
	insocket = context.socket(zmq.SUB)
	insocket.connect(addr)
	
	log.info(f"Subscribing to ZMQ topic \"{topic}\"")
	insocket.subscribe(topic)

	while True:
		if insocket.poll(10) != 0: # check if there is a message on the socket
			(_, meta, _) = insocket.recv_multipart()
			log.debug(meta)

			jmeta = json.loads(meta.decode("utf-8"))
			msg = jmeta["decode.msg"]

			icao = pms.icao(msg)
			verif_status = jmeta["verify.status"] if "verify.status" in jmeta else "None"
			tc = pms.adsb.typecode(msg)
			(lat, lon) = (None, None) if tc < 9 or tc > 18 else pms.adsb.position_with_ref(msg, LAT, LON)

			if (lat, lon) == (None, None):
				continue

			#convert to webmercator
			x, y = tra.transform(lon, lat)

			newdetails = (lat, lon, x, y, icao, verif_status, time.time())

			for q in qs:
				try:
					q.put(newdetails, block=False)
				except queue.Full:
					log.warning("Full queue, discarding oldest update")
					q.get(block=False)
					q.put(newdetails, block=False)						#TODO: this could just throw an error again

		else:
			time.sleep(0.5) # wait 500ms and try again
			continue

