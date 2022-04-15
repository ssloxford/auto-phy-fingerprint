import logging
import argparse

import adsb_siamese_common as asc
import adsb_siamese_constants as const

#########################################

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s|%(message)s', level=logging.INFO)

ap = argparse.ArgumentParser(description="Process a file of bursts, perform verification on each one via a specified model and annotate them with the result.")
ap.add_argument("input_file", type=str, help="Filename from which to load input bursts for fingerprinting")
#ap.add_argument("model_file", type=str, help="Filename from which to load the model")
#ap.add_argument("database_filename", type=str, help="Filename for SQLite3 file in which to store fingerprints")
args = ap.parse_args()


#get the model ready
logging.info("Beginning ML")
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '1' #0 = all messages are logged (default behavior), 1 = INFO messages are not printed, 2 = INFO and WARNING messages are not printed, 3 = INFO, WARNING, and ERROR messages are not printed

from tensorflow.keras import models

asc.tf_tweak_limit_gpu_memory_usage()		#limit use of gpu memory
asc.tf_tweak_disable_eager_execution()		#disable eager execution mode

logging.info("Loading model")
model = models.load_model("models/siamese-hisamp-94percent.h5")

#extract the fingerprint generating model
#model.summary()
#fingerprint_model = models.Model(inputs=model.layers[2].input, outputs=model.layers[2].output)
#fingerprint_model.summary()

logging.info("Fingerprinting messages")

h5siamese_filename = args.input_file

(test_in, test_out, case_count, waveform_len, feature_count) = asc.loadSiameseDatasets(h5siamese_filename)
asc.validate_dataset_dimensions(case_count, waveform_len, feature_count)

logging.info("Masking identifiers")
test_in = asc.maskDataset(test_in, const.oversampling_factor, "NOICAO")

#keep track of aircraft we've seen and their last fingerprint(s)
known_aircraft = {}
results = { True: 0, False: 0 }
result_logs = {}

#for each message, compare it to the fingerprint
for msgi in range(case_count):
	if msgi % 1000 == 0:
		logging.info((msgi, len(known_aircraft), results))
	(msg, claimedicao) = (test_in[msgi], test_out[msgi].tobytes().decode("utf-8"))
	
	#if we have no previous fingerprint, then just save
	if claimedicao not in known_aircraft:
		#generate fingerprint
		#fp = fingerprint_model.predict(msg.reshape(1, 2400, 2))
		#known_aircraft[claimedicao] = fp
		#print("New aircraft {}, stored fingerprint".format(fp))
		
		known_aircraft[claimedicao] = msg
		#print("New aircraft {}, stored MESSAGE".format(claimedicao))
		result_logs[claimedicao] = []
	else:	#otherwise check the fingerprint
		msg_shaped = msg.reshape(1, const.message_symbols * const.oversampling_factor, feature_count)
		ref_shaped = known_aircraft[claimedicao].reshape(1, const.message_symbols * const.oversampling_factor, feature_count)
		compare_result = model.predict([msg_shaped, ref_shaped])
		match = compare_result.flatten()[0] > 0.5
		#print("Message for {} matches: {}".format(claimedicao, match))
		results[match] += 1
		result_logs[claimedicao].append(match)
		#if match:
		#	known_aircraft[claimedicao] = msg

logging.info(results)
