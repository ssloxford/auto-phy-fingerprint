import logging
import argparse

import common.tf_tweak as tf_tweak
import common.dataset as dataset
import common.constants as constants
from common.fingerprinting import *

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '1' #0 = all messages are logged (default behavior), 1 = INFO messages are not printed, 2 = INFO and WARNING messages are not printed, 3 = INFO, WARNING, and ERROR messages are not printed
from tensorflow.keras import models

#########################################

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s|%(message)s', level=logging.INFO)

fingerprinter_types = {
	"FIRST": FirstMsgFingerprinter,
	"BESTN": BestOfNFingerprinter,
	"CENTROID": CentroidFingerprinter
}

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
tf_tweak.disable_eager_execution()		#disable eager execution mode			#TODO: super slow because of eager, but centroid needs it for now

logging.info("Loading model")
model = models.load_model("models/siamese-hisamp-94percent.h5")

#extract the fingerprint generating model
#model.summary()
#fingerprint_model = models.Model(inputs=model.layers[2].input, outputs=model.layers[2].output)
#fingerprint_model.summary()

logging.info("Fingerprinting messages")

h5siamese_filename = args.input_file

(test_in, test_out, case_count, waveform_len, feature_count) = dataset.loadSiameseDatasets(h5siamese_filename, oversampling_factor)

logging.info("Masking identifiers")
test_in = dataset.maskDataset(test_in, oversampling_factor, "NOICAO")

#keep track of aircraft we've seen and their last fingerprint(s)
known_aircraft = {}
results = { True: 0, False: 0 }
result_logs = {}

#fprinter_first = FirstMsgFingerprinter(model)
#fprinter_bestn = BestOfNFingerprinter(model, 10)
#fprinter_centroid = CentroidFingerprinter(model, 10)
fingerprinter = fingerprinter_types[args.fingerprint_method](model, args.fingerprinter_n)


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

	# #if we have no previous fingerprint, then just save
	# if claimedicao not in known_aircraft:
	# 	##generate fingerprint
	# 	##fp = fingerprint_model.predict(msg.reshape(1, 2400, 2))
	# 	##known_aircraft[claimedicao] = fp
	# 	##print("New aircraft {}, stored fingerprint".format(fp))
	#
	# 	known_aircraft[claimedicao] = msg
	# 	##print("New aircraft {}, stored MESSAGE".format(claimedicao))
	# 	result_logs[claimedicao] = []
	# else:	#otherwise check the fingerprint
	# 	msg_shaped = msg.reshape(1, msg.shape[0], msg.shape[1])
	# 	ref_shaped = known_aircraft[claimedicao].reshape(1, constants.message_symbols * oversampling_factor, feature_count)
	#
	# 	compare_result = model.predict([msg_shaped, ref_shaped])
	# 	match = compare_result.flatten()[0] > 0.5
	# 	##print("Message for {} matches: {}".format(claimedicao, match))
	# 	results[match] += 1
	# 	result_logs[claimedicao].append(match)
	# 	##if match:
	# 	##	known_aircraft[claimedicao] = msg

	#fpresult_first = fprinter_first.fingerprint_msg(msg, claimedicao)
	#fpresult_bestn = fprinter_bestn.fingerprint_msg(msg, claimedicao)
	#fpresult_centroid = fprinter_centroid.fingerprint_msg(msg, claimedicao)
	#if fpresult_first is not None:# and not match:
	#	print(f"Native: {match}, fprinter_first: {fpresult_first}, fprinter_best: {fpresult_bestn}, fprinter_centroid: {fpresult_centroid}")

logging.info(results)
