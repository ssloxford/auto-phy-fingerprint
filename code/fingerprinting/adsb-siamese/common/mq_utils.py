import logging
import zmq
import json

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


