import zmq
import numpy as np
import time
import matplotlib.pyplot as plt
import struct

context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://127.0.0.1:5678") # connect, not bind, the PUB will bind, only 1 can bind
#socket.setsockopt(zmq.SUBSCRIBE, b'') # subscribe to topic of all (needed or else it won't work)

socket.subscribe("ADS-B")

start = time.time()
msgi = 0

while True:
	if socket.poll(10) != 0: # check if there is a message on the socket
		#msg = socket.recv() # grab the message
		#
		#sob = 0
		#for i in range(len(msg)):
		#	if msg[i] == 0:
		#		sob = i
		#		break
		#
		#(meta, data) = msg[:sob], msg[sob+1:]
		#print(f"len: {len(data)} ({len(data)/8} samps.)")
		
		(topic, meta, data) = socket.recv_multipart()
		
		print(f"topic: {topic}, len: {len(data)} ({len(data)/8} samps.), meta: {meta.decode('utf-8')}")
		
		npdata = np.frombuffer(data, dtype=np.complex64, count=-1) # make sure to use correct data type (complex64 or float32); '-1' means read all data in the buffer
		#print(data[0:10])
		#print(msg)
		#plt.plot(np.real(npdata))
		#plt.plot(np.imag(npdata))
		#plt.plot(np.abs(npdata))
		#plt.title(meta.decode("utf-8"))
		#plt.show()
	else:
		time.sleep(0.05) # wait 100ms and try again


