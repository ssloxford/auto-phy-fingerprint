import logging
import zmq
import time
import json

import threading
import queue
import numpy as np

formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s|%(message)s')
log = logging.getLogger("streamsink.py")
log.setLevel(logging.INFO)

qs = set()


#TODO: deregister queues when sessions close
def register():
	log.info("Registering new update queue")
	q = queue.Queue(1000)
	qs.add(q)
	return q

def deregister(q):
	log.info("Deregistering update queue")
	qs.remove(q)

def streamFromZMQ(addr, topic=""):
	context = zmq.Context()

	log.info(f"Setting up ZMQ SUB socket connecting to {addr}")
	insocket = context.socket(zmq.SUB)
	insocket.connect(addr)

	log.info(f"Subscribing to ZMQ topic \"{topic}\"")
	insocket.subscribe(topic)

	message_parts = []

	while True:
		if insocket.poll(10) != 0: # check if there is a message on the socket
			(_, meta, _) = insocket.recv_multipart()
			log.debug(meta)

			jmeta = json.loads(meta.decode("utf-8"))
			msg = jmeta["decode.msg"]
			byteindex = int(jmeta["byteindex"])
			verif_status = jmeta["verify.status"] if "verify.status" in jmeta else "None"
			verif_scores = jmeta["verify.scores"] if "verify.scores" in jmeta else "None"

			#display the last full message
			if byteindex == 0 and len(message_parts) > 0:
				fullmsg = "".join([x[0] for x in message_parts])
				verif_count = sum([1 if x[1] == "True" else 0 for x in message_parts])
				verif_total = len(message_parts)
				verif_score_sums = {v:0 for v in message_parts[0][2]}
				for v in verif_score_sums:
					verif_score_sums[v] = sum([x[2][v] for x in message_parts]) / len(message_parts)
				fullmsgtime = message_parts[0][3]

				#score_pos = (0,1,2,3,4,5)
				#scores = (verif_score_sums["cb3e26ee7effb979268abc35cac8b180"], verif_score_sums["f8bde97d87baad9bff11969eceab4e80"], verif_score_sums["257eb55c4ce227e861a04fb0758d7cf9"], verif_score_sums["3793fa4f2676024c81c9feb01830d39a"], verif_score_sums["06dd95400f3923740cf63a64f8108307"], verif_score_sums["c76f1bfd4b34e8750f984e1e68096ff7"])
				fulldetails = (fullmsg, verif_count, verif_total, fullmsgtime, sorted(verif_score_sums.items()))

				for q in qs:
					try:
						#q.put(newdetails, block=False)
						q.put(fulldetails, block=False)
					except queue.Full:
						log.warning("Full queue, discarding oldest update")
						q.get(block=False)
						#q.put(newdetails, block=False)  					# TODO: this could just throw an error again
						q.put(fulldetails, block=False)						#TODO: this could just throw an error again

				message_parts = []

			#then add the new message part/byte
			import ast
			newdetails = (msg, verif_status, ast.literal_eval(verif_scores), time.time())
			message_parts.append(newdetails)

		else:
			time.sleep(0.25) # wait 500ms and try again
			continue
