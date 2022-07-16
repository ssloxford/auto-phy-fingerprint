import logging
import argparse
import os
import numpy as np
import zmq
import json
import time

import common.tf_tweak as tf_tweak
import common.dataset as dataset
import common.constants as constants
from common.mq_utils import ZmqSub, ZmqPub

from common.fingerprinting import *

#########################################

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s|%(message)s', level=logging.INFO)

ap = argparse.ArgumentParser(description="Handle a stream of bursts, perform verification on each one via a specified model and annotate them with the result for downstream.")
ap.add_argument("recv_connect_addr", type=str, help="Connect address of upstream ZMQ PUB")
ap.add_argument("send_bind_addr", type=str, help="Bind address for ZMQ PUB")
ap.add_argument("model_file", type=str, help="Filename from which to load the model")
ap.add_argument("database_filename", type=str, help="Filename for SQLite3 file in which to store fingerprints")
ap.add_argument("fingerprint_method", type=str, help="Name of fingerprinting method to use")
ap.add_argument("--fingerprinter_n", type=int, default=10, help="Number of entries to consider with fingerprinter")
#parser.add_argument("--oversampling_factor", type=int, default=10, help="Oversampling factor used when creating the dataset")

#TODO: topic to subscribe to
#TODO: MQ choice
args = ap.parse_args()

assert args.fingerprint_method in fingerprinter_types

#get the model ready
logging.info("Loading Tensorflow")

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '1' #0 = all messages are logged (default behavior), 1 = INFO messages are not printed, 2 = INFO and WARNING messages are not printed, 3 = INFO, WARNING, and ERROR messages are not printed
import tensorflow as tf
from tensorflow.keras import layers, models

tf_tweak.limit_gpu_memory_usage()		#limit use of gpu memory
tf_tweak.disable_eager_execution()		#disable eager execution mode

logging.info("Loading verification model")
model = models.load_model(args.model_file)

#extract the fingerprint generating model
logging.info("Extracting fingerprinting model")
fingerprint_model = models.Model(inputs=model.layers[2].input, outputs=model.layers[2].output)

# logging.info(f"Creating/opening SQLite3 fingerprints file at {args.database_filename}")
# engine = db.create_engine(f"sqlite:///{args.database_filename}")
# connection = engine.connect()
# Base.metadata.create_all(engine)
#
# logging.info(f"Creating database session")
# Session = db.orm.sessionmaker(bind=engine)
# session = Session()

logging.info("Initialising ZMQ")
insocket = ZmqSub(args.recv_connect_addr)
insocket.subscribe("RS-485")
outsocket = ZmqPub(args.send_bind_addr)


#config for input rate
oversampling_factor = 275			#i.e. 10x normal size (in this case, for ADS-B, 20 Msps instead of Nyquist rate of 2 Msps)
waveform_len = 2750
feature_count = 2

logging.info(f"Creating {args.fingerprint_method} fingerprinter backed by DB at {args.database_filename}")
#fingerprintdb = FingerprintDB(session)
fingerprinter = fingerprinter_types[args.fingerprint_method](model, args.database_filename, args.fingerprinter_n)

#keep track of aircraft we've seen and their last fingerprint(s)
#known_aircraft = {}
#db_known_aircraft = FingerprintDB(session)
results = { True: 0, False: 0}
newcount = 0
result_logs = {}

logging.info("Commencing verification loop")
msg_count = 0

while True:
	(topic, meta, burst) = (None, None, None)		#be on the safe side and break quickly if no new message received in some weird way, don't continue with old values
	if insocket.poll(10) != 0: # check if there is a message on the socket
		(topic, meta, burst) = insocket.recv()
	else:
		time.sleep(0.05) # wait 100ms and try again
		continue

	msguuid = meta["uuid"]
	logging.debug(f"Message UUID: {msguuid}")

	trueid = meta["trueid"]
	byteindex = meta["byteindex"]

	if byteindex == 0:
		msg_scores = {}

	#claimedicao = meta["decode.msg"][2:8]						#TODO: this should probably be provided by the demod, as it's so easy to get there
	#logging.debug(f"Extracted ICAO: {claimedicao}")
	#
	#logging.debug("Masking identifier(s)")
	msg_c = np.frombuffer(burst, dtype=np.complex64)
	msg = np.empty(shape=(waveform_len, feature_count), dtype=np.float32)
	msg[:,0] = np.real(msg_c)
	msg[:,1] = np.imag(msg_c)
	#msg = dataset.maskDataset(msg.reshape(1, waveform_len, feature_count), oversampling_factor, "NOICAO").reshape(waveform_len, feature_count)

	logging.debug("Testing message")
	similarities = fingerprinter.fingerprint_msg(msg)
	pick = ""
	pickscore = 0
	for s in similarities:

		#print(f"{s} : {similarities[s]}")
		if similarities[s] > pickscore:
			pickscore = similarities[s]
			pick = s
	#print(f"Pick: {pick} vs. True: {trueid} --> {pick == trueid}")

	match = pick == trueid

	# match = fingerprinter.fingerprint_msg(msg, claimedicao)

	if pick not in result_logs:
		result_logs[pick] = []
		#newcount += 1
	if match is not None:
		results[match] += 1
	result_logs[pick].append(match)

	if match is not None:
		verif_status = str(match)
	else:
		verif_status = None

	logging.debug("Annotating verification and passing message downstream")
	topic = b"RS-485"
	meta["verify.status"] = verif_status
	meta["verify.scores"] = str(similarities)
	#newmeta = json.dumps(jmeta).encode("utf-8")
	outdata = burst			#pass on the original, not our masked copy
	#outsocket.send_multipart([topic, newmeta, outdata])
	outsocket.publish(topic, meta, outdata)

	if msg_count % 100 == 0:
		logging.info(f"Verification stats: {results} + {newcount} new")
		#logging.info(f"{result_logs}")
	msg_count += 1
