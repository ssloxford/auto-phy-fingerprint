import logging
import zmq
import json
import queue
import threading
import uuid

class ZmqRep:
	def __init__(self, bind_addr):
		self.bind_addr = bind_addr

		self.context = zmq.Context()
		self.outsocket = self.context.socket(zmq.REP)
		self.outsocket.bind(bind_addr)

		self.maxsendqueue = 1
		self.sendqueue = queue.Queue(self.maxsendqueue)

		self.receiver_ready = dict()

		self.senderthread_shouldexit = False
		self.senderthread = threading.Thread(target=self._sendloop)
		self.senderthread.start()

	def publish(self, topic, meta, data):
		self.sendqueue.put((topic, meta, data))

	def _sendloop(self):
		while not self.senderthread_shouldexit:
			clientid = self.outsocket.recv()
			self.receiver_ready[clientid] = True

			if all(self.receiver_ready.values()):
				(topic, meta, data) = self.sendqueue.get()
				for rcv in self.receiver_ready:
					self.outsocket.send_multipart([topic, meta, data])
					self.receiver_ready[rcv] = False

	def __del__(self):
		self.outsocket.close()

class ZmqReq:
	def __init__(self, connect_addr):
		self.requestor_id = str(uuid.uuid4())
		self.connect_addr = connect_addr

		self.context = zmq.Context()
		#logging.info(f"Setting up ZMQ SUB socket connecting to {connect_addr}")
		self.insocket = self.context.socket(zmq.REQ)
		self.insocket.connect(connect_addr)

	def subscribe(self, topic):
		logging.error("No subscribing in this socket type")

	def poll(self, timeout):
		return 1			#TODO: eek

	def recv(self):
		self.insocket.send(self.requestor_id.encode("utf-8"))
		(topic, meta, data) = self.insocket.recv_multipart()
		logging.debug(f"Received message of len {len(topic) + len(meta) + len(data)} bytes")
		meta = json.loads(meta)
		return (topic, meta, data)

	def __del__(self):
		self.insocket.close()

class ZmqPub:
	def __init__(self, bind_addr):
		self.bind_addr = bind_addr

		self.context = zmq.Context()
		logging.info(f"Setting up ZMQ PUB socket at {bind_addr}")
		self.outsocket = self.context.socket(zmq.PUB)
		self.outsocket.setsockopt(zmq.SNDHWM, 1024)  # 1024 messages ~= 32MiB if burst is 4096 complex samples long
		# outsocket.setsockopt(zmq.SNDBUF, 1024*1024)		#based on default max buffer allowed in Ubuntu 20.04
		self.outsocket.bind(bind_addr)

	def publish(self, topic, meta, data):
		if not isinstance(meta, (bytes, bytearray)):
			meta = json.dumps(meta).encode("utf-8")
		self.outsocket.send_multipart([topic, meta, data])
		logging.debug(f"Sent message of len {len(topic) + len(meta) + len(data)} bytes")

	def __del__(self):
		self.outsocket.close()

class ZmqSub:
	def __init__(self, connect_addr):
		self.connect_addr = connect_addr

		self.context = zmq.Context()
		logging.info(f"Setting up ZMQ SUB socket connecting to {connect_addr}")
		self.insocket = self.context.socket(zmq.SUB)
		self.insocket.connect(connect_addr)

	def subscribe(self, topic):
		self.insocket.subscribe(topic)

	def poll(self, timeout):
		return self.insocket.poll(timeout)

	def recv(self):
		(topic, meta, data) = self.insocket.recv_multipart()
		logging.debug(f"Received message of len {len(topic) + len(meta) + len(data)} bytes")
		meta = json.loads(meta)
		return (topic, meta, data)

	def __del__(self):
		self.insocket.close()

