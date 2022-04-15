import logging
import argparse
import os
import numpy as np
import zmq
import json
import time

import adsb_siamese_common as asc

from datetime import datetime
import sqlalchemy as db
from sqlalchemy.ext.declarative import declarative_base
import pickle

Base = declarative_base()

class dbFingerprintMessage(Base):
	__tablename__ = "fingerprintmsgs"
	#id = db.Column(db.Integer, primary_key=True)
	#icao = db.Column(db.String, index=True)
	icao = db.Column(db.String, index=True, primary_key=True)
	fp_msg = db.Column(db.LargeBinary)
	msguuid = db.Column(db.String)
	savetime_coarse = db.Column(db.Float)
	savetime_coarse_dt = db.Column(db.DateTime)

class FingerprintDB:
	def __init__(self, session):
		self.session = session

	def __contains__(self, key):
		return self.session.query(dbFingerprintMessage).filter(dbFingerprintMessage.icao == key).first() is not None

	def __getitem__(self, key):
		found = self.session.query(dbFingerprintMessage).filter(dbFingerprintMessage.icao == key).one()
		return pickle.loads(found.fp_msg)

	def __setitem__(self, key, value):
		savetime = time.time()

		fpm = dbFingerprintMessage()
		fpm.icao = key
		fpm.fp_msg = pickle.dumps(value)
		fpm.msguuid = jmeta["uuid"]
		fpm.savetime_coarse = savetime
		fpm.savetime_coarse_dt = datetime.fromtimestamp(savetime)#.isoformat(sep=" ")

		self.session.add(fpm)
		self.session.commit()

#########################################

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s|%(message)s', level=logging.INFO)

ap = argparse.ArgumentParser(description="Handle a stream of bursts, perform verification on each one via a specified model and annotate them with the result for downstream.")
ap.add_argument("recv_connect_addr", type=str, help="Connect address of upstream ZMQ PUB")
ap.add_argument("send_bind_addr", type=str, help="Bind address for ZMQ PUB")
ap.add_argument("model_file", type=str, help="Filename from which to load the model")
ap.add_argument("database_filename", type=str, help="Filename for SQLite3 file in which to store fingerprints")
args = ap.parse_args()


#get the model ready
logging.info("Loading Tensorflow")

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '1' #0 = all messages are logged (default behavior), 1 = INFO messages are not printed, 2 = INFO and WARNING messages are not printed, 3 = INFO, WARNING, and ERROR messages are not printed
import tensorflow as tf
from tensorflow.keras import layers, models

#limit gpu usage
asc.tf_tweak_limit_gpu_memory_usage()


logging.info("Loading verification model")
model = models.load_model(args.model_file)

#extract the fingerprint generating model
logging.info("Extracting fingerprinting model")
fingerprint_model = models.Model(inputs=model.layers[2].input, outputs=model.layers[2].output)

logging.info(f"Creating/opening SQLite3 fingerprints file at {args.database_filename}")
engine = db.create_engine(f"sqlite:///{args.database_filename}")
connection = engine.connect()
Base.metadata.create_all(engine)

logging.info(f"Creating database session")
Session = db.orm.sessionmaker(bind=engine)
session = Session()

logging.info("Initialising ZMQ")
context = zmq.Context()

logging.info(f"Setting up ZMQ SUB socket connecting to {args.recv_connect_addr}")
insocket = context.socket(zmq.SUB)
insocket.connect(args.recv_connect_addr)
insocket.subscribe("ADS-B")

logging.info(f"Setting up ZMQ PUB socket at {args.send_bind_addr}")
outsocket = context.socket(zmq.PUB)
outsocket.setsockopt(zmq.SNDHWM, 1024)	#1024 messages ~= 32MiB if burst is 4096 complex samples long
#outsocket.setsockopt(zmq.SNDBUF, 1024*1024)		#based on default max buffer allowed in Ubuntu 20.04
outsocket.bind(args.send_bind_addr)


#config for input rate
oversampling_factor = 10			#i.e. 10x normal size (in this case, for ADS-B, 20 Msps instead of Nyquist rate of 2 Msps)
waveform_len = 2400
feature_count = 2

#keep track of aircraft we've seen and their last fingerprint(s)
#known_aircraft = {}
db_known_aircraft = FingerprintDB(session)
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

	#get metadata
	jmeta = json.loads(meta)

	msguuid = jmeta["uuid"]
	logging.debug(f"Message UUID: {msguuid}")

	claimedicao = jmeta["decode.msg"][2:8]						#TODO: this should probably be provided by the demod, as it's so easy to get there
	logging.debug(f"Extracted ICAO: {claimedicao}")

	logging.debug("Masking identifier(s)")
	msg_c = np.frombuffer(burst, dtype=np.complex64)
	msg = np.empty(shape=(waveform_len, feature_count), dtype=np.float32)
	msg[:,0] = np.real(msg_c)
	msg[:,1] = np.imag(msg_c)
	#msg[32*oversampling_factor:80*oversampling_factor,:] = 0.0			#masking out icao	#TODO: use the standard masking routine
	msg = asc.maskDataset(msg, oversampling_factor, "NOICAO")

	logging.debug("Tracking/verifying message")
	verif_status = None
	#if we have no previous fingerprint, then just save
	#if claimedicao not in known_aircraft:
	if claimedicao not in db_known_aircraft:
		#known_aircraft[claimedicao] = msg									#TODO: this is a core issue -- there's no fingerprint being tracked per se, just an old message -- because the siamese network expects that -- we would need a modified network to accept a fingerprint on one branch
		db_known_aircraft[claimedicao] = msg							##TODO: just writing the fingerprints out to test it, for now
		logging.debug(f"New aircraft: {claimedicao}")
		result_logs[claimedicao] = []
		verif_status = "NEW"
	else:	#otherwise check the fingerprint
		#compare_result = model.predict([msg.reshape(1, waveform_len, feature_count), known_aircraft[claimedicao].reshape(1, waveform_len, feature_count)])
		compare_result = model.predict([msg.reshape(1, waveform_len, feature_count), db_known_aircraft[claimedicao].reshape(1, waveform_len, feature_count)])
		match = compare_result.flatten()[0]>0.5
		logging.debug("Message for {} matches: {}".format(claimedicao, match))
		verif_status = str(match)
		results[match] += 1
		if claimedicao not in result_logs:
			result_logs[claimedicao] = []
		result_logs[claimedicao].append(match)
		#if match:
		#	known_aircraft[claimedicao] = msg

	logging.debug("Annotating verification and passing message downstream")
	topic = b"ADS-B"
	jmeta["verify.status"] = verif_status
	newmeta = json.dumps(jmeta).encode("utf-8")
	outdata = burst			#pass on the original, not our masked copy
	outsocket.send_multipart([topic, newmeta, outdata])

	logging.debug(f"Sent message of len {len(topic) + len(newmeta) + len(outdata)} bytes")

	if msg_count % 100 == 0:
		logging.info(f"Verification stats: {results}")
	msg_count += 1
