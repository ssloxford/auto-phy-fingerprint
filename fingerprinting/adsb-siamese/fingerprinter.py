import logging
import argparse
import os
import numpy as np
import zmq
import json
import time

def maskDataset(inds, osf, maskname):
	if maskname is None or maskname == "NONE":
		return inds						#nothing
	elif maskname == "HEADERONLY":
		return inds[:,:32*osf,:]				#aggressive masking, 32 samples is only the beginning of the header, no icao, no data, no crc
		#inds[:,32*osf:,:] = 0.0
		return inds
	elif maskname == "NOICAO":
		inds[:,32*osf:80*osf,:] = 0.0			#masking out icao
		return inds
	elif maskname == "INVERSE-ICAOONLY":
		inds[:,:32*osf,:] = 0.0			#inverse icao masking -- leaving *only* the icao
		inds[:,80*osf:,:] = 0.0			#inverse icao masking -- leaving *only* the icao
		return inds
	elif maskname == "NOICAOORLATLON":
		inds[:,32*osf:80*osf,:] = 0.0			#masking out icao
		inds[:,124*osf:192*osf,:] = 0.0			#masking out latlon
		return inds
	else:
		raise ValueError("Unknown mask name")

#########################################

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s|%(message)s', level=logging.INFO)

ap = argparse.ArgumentParser(description="Handle a stream of bursts, perform verification on each one via a specified model and annotate them with the result for downstream.")
ap.add_argument("recv_connect_addr", type=str, help="Connect address of upstream ZMQ PUB")
ap.add_argument("send_bind_addr", type=str, help="Bind address for ZMQ PUB")
ap.add_argument("model_file", type=str, help="Filename from which to load the model")
args = ap.parse_args()


#get the model ready
logging.info("Loading Tensorflow")

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '1' #0 = all messages are logged (default behavior), 1 = INFO messages are not printed, 2 = INFO and WARNING messages are not printed, 3 = INFO, WARNING, and ERROR messages are not printed
import tensorflow as tf
from tensorflow.keras import layers, models

#limit gpu usage
gpus = tf.config.list_physical_devices('GPU')
if gpus:
	try:
		# Currently, memory growth needs to be the same across GPUs
		logging.info("Setting GPU memory policy to 'grow as needed'")
		for gpu in gpus:
			tf.config.experimental.set_memory_growth(gpu, True)
		logical_gpus = tf.config.experimental.list_logical_devices('GPU')
		logging.info(len(gpus), "Physical GPUs,", len(logical_gpus), "Logical GPUs")
	except RuntimeError as e:
		# Memory growth must be set before GPUs have been initialized
		logging.error(e)



logging.info("Loading verification model")
model = models.load_model(args.model_file)

#extract the fingerprint generating model
logging.info("Extracting fingerprinting model")
fingerprint_model = models.Model(inputs=model.layers[2].input, outputs=model.layers[2].output)


logging.info("Initialising ZMQ")
context = zmq.Context()

logging.info(f"Setting up ZMQ SUB socket connecting to {args.recv_connect_addr}")
insocket = context.socket(zmq.SUB)
insocket.connect(args.recv_connect_addr) 
insocket.subscribe("ADS-B")

logging.info(f"Setting up ZMQ PUB socket at {args.send_bind_addr}")
outsocket = context.socket(zmq.PUB)
outsocket.setsockopt(zmq.SNDHWM, 1024)	#1024 messages ~= 32MiB if burst is 4096 complex samples long
outsocket.bind(args.send_bind_addr)


#config for input rate
oversampling_factor = 10			#i.e. 10x normal size (in this case, for ADS-B, 20 Msps instead of Nyquist rate of 2 Msps)
waveform_len = 2400
feature_count = 2

#keep track of aircraft we've seen and their last fingerprint(s)
known_aircraft = {}
results = { True: 0, False: 0}
result_logs = {}

logging.info("Commencing verification loop")
msg_count = 0
while True:
	(topic, meta, burst) = (None, None, None)		#be on the safe side and break quickly if no new message received in some weird way, don't continue with old values
	if insocket.poll(10) != 0: # check if there is a message on the socket
		(topic, meta, burst) = insocket.recv_multipart()
		logging.debug(f"Received message of len {len(topic) + len(meta) + len(burst)} bytes")
	else:
		time.sleep(0.05) # wait 100ms and try again
		continue
		
	logging.debug("Extracting ICAO")
	jmeta = json.loads(meta)
	claimedicao = jmeta["decode.msg"][2:8]						#TODO: this should probably be provided by the demod, as it's so easy to get there

	logging.debug("Masking identifier(s)")
	msg_c = np.frombuffer(burst, dtype=np.complex64)
	msg = np.empty(shape=(waveform_len, feature_count), dtype=np.float32)
	msg[:,0] = np.real(msg_c)
	msg[:,1] = np.imag(msg_c)
	msg[32*oversampling_factor:80*oversampling_factor,:] = 0.0			#masking out icao
	
	logging.debug("Tracking/verifying message")
	verif_status = None
	#if we have no previous fingerprint, then just save
	if claimedicao not in known_aircraft:
		known_aircraft[claimedicao] = msg									#TODO: this is a core issue -- there's no fingerprint being tracked per se, just an old message -- because the siamese network expects that -- we would need a modified network to accept a fingerprint on one branch
		logging.debug(f"New aircraft: {claimedicao}")
		result_logs[claimedicao] = []
		verif_status = "NEW"
	else:	#otherwise check the fingerprint
		compare_result = model.predict([msg.reshape(1, waveform_len, feature_count), known_aircraft[claimedicao].reshape(1, waveform_len, feature_count)])
		match = compare_result.flatten()[0]>0.5
		logging.debug("Message for {} matches: {}".format(claimedicao, match))
		verif_status = str(match)
		results[match] += 1
		result_logs[claimedicao].append(match)
		#if match:
		#	known_aircraft[claimedicao] = msg
	
	logging.debug("Annotating verification and passing message downstream")
	topic = b"ADS-B"
	jmeta["verify.status"] = verif_status
	newmeta = json.dumps(jmeta).encode("utf-8")
	outdata = burst			#pass on the original, not our masked copy
	outsocket.send_multipart([topic, newmeta, outdata])
	
	if msg_count % 100 == 0:
		logging.info(f"Verification stats: {results}")
	msg_count += 1