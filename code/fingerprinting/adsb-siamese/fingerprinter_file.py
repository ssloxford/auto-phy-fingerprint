import logging
import argparse

import sqlalchemy as db

import common.tf_tweak as tf_tweak
import common.dataset as dataset
import common.constants as constants
from common.fingerprinting import fingerprinter_types, FirstMsgFingerprinter, BestOfNFingerprinter, CentroidFingerprinter

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '1' #0 = all messages are logged (default behavior), 1 = INFO messages are not printed, 2 = INFO and WARNING messages are not printed, 3 = INFO, WARNING, and ERROR messages are not printed
from tensorflow.keras import models

from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

#########################################

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s|%(message)s', level=logging.INFO)

parser = argparse.ArgumentParser(description="Process a file of bursts, perform verification on each one via a specified model and annotate them with the result.")
parser.add_argument("input_file", type=str, help="Filename from which to load input bursts for fingerprinting")
parser.add_argument("fingerprint_method", type=str, help="Name of fingerprinting method to use")
parser.add_argument("--oversampling_factor", type=int, default=10, help="Oversampling factor used when creating the dataset")
parser.add_argument("--fingerprinter_n", type=int, default=10, help="Number of entries to consider with fingerprinter")
#ap.add_argument("model_file", type=str, help="Filename from which to load the model")
#ap.add_argument("database_filename", type=str, help="Filename for SQLite3 file in which to store fingerprints")

args = parser.parse_args()
oversampling_factor = args.oversampling_factor
assert args.fingerprint_method in fingerprinter_types

#get the model ready
logging.info("Beginning ML")

tf_tweak.limit_gpu_memory_usage()		#limit use of gpu memory
tf_tweak.disable_eager_execution()		#disable eager execution mode

logging.info("Loading model")
model = models.load_model("models/siamese-hisamp-94percent.h5")

#extract the fingerprint generating model
#model.summary()
#fingerprint_model = models.Model(inputs=model.layers[2].input, outputs=model.layers[2].output)
#fingerprint_model.summary()

# logging.info(f"Creating/opening SQLite3 fingerprints file in memory")
# engine = db.create_engine(f"sqlite://")
# connection = engine.connect()
# Base.metadata.create_all(engine)
#
# logging.info(f"Creating database session")
# Session = db.orm.sessionmaker(bind=engine)
# session = Session()

logging.info("Fingerprinting messages")

h5siamese_filename = args.input_file

(test_in, test_out, case_count, waveform_len, feature_count) = dataset.loadSiameseDatasets(h5siamese_filename, oversampling_factor)

logging.info("Masking identifiers")
test_in = dataset.maskDataset(test_in, oversampling_factor, "NOICAO")

#keep track of aircraft we've seen and their last fingerprint(s)
known_aircraft = {}
results = { True: 0, False: 0 }
result_logs = {}

inmemory_db_url = ""			#so that the url becomes sqlite://, which indicates an in-memory db in sqlalchemy
fingerprinter = fingerprinter_types[args.fingerprint_method](model, inmemory_db_url, args.fingerprinter_n)


#for each message, compare it to the fingerprint
for msgi in range(case_count):
	if msgi % 1000 == 0:
		logging.info((msgi, len(fingerprinter.known_aircraft), results, (results[True] / (results[True]+results[False])) if (results[True]+results[False]) > 0 else "" ))
	(msg, claimedicao) = (test_in[msgi], test_out[msgi].tobytes().decode("utf-8"))

	match = fingerprinter.fingerprint_msg(msg, claimedicao)
	if claimedicao not in result_logs:
		result_logs[claimedicao] = []
	if match is not None:
		results[match] += 1
	result_logs[claimedicao].append(match)

logging.info(results)
