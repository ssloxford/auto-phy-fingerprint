import sys
import numpy as np
import matplotlib.pyplot as plt
import h5py
import time


def loadSiameseDatasets(h5siamese_filename, subset=None):
	h5in = h5py.File(h5siamese_filename, "r")
	inds = h5in["inds"]
	outds = h5in["outds"]

	if subset != None:
		inds = inds[:subset]
		outds = outds[:subset]
		
	#load the datasets into memory for speed
	inds = np.array(inds)
	outds = np.array(outds)
	
	(case_count, waveform_len, feature_count) = inds.shape
	
	h5in.close()
	
	return (inds, outds, case_count, waveform_len, feature_count)

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

"""
Create a batch of pairwise samples, where half are the same class left-and-right and half are different classes left-and-right. 
This is much easier if the dataset has equal blocks of each, but we don't have that, so a lot of expensive lookups are needed (lucky numpy is fast).
"""
def select_half_half(inds, outds, batch_size=10, with_raw_vals=False):	
	start = np.random.randint(0, len(inds))
	end = (start + batch_size)
	batchi = np.arange(start, end)
	
	in_l = np.take(inds, batchi, axis=0, mode="wrap")
	out_l = np.take(outds, batchi, axis=0, mode="wrap")

	in_r = np.empty_like(in_l)
	out_r = np.empty_like(out_l)
	
	#out_r[:] = "none"
	
	#first half of right-hand side is matching (ideally not same entry, but ignore here as there are some singular entries)
	for i in range(batch_size // 2):
		same = np.argwhere(outds.reshape(-1) == out_l[i]).flatten()
		righti = np.random.randint(0, len(same))
		in_r[i,:] = inds[same[righti]]
		out_r[i,:] = outds[same[righti]]
	
	#second half is not matching
	for i in range(batch_size // 2, batch_size, 1):
		diff = np.argwhere(outds.reshape(-1) != out_l[i]).flatten()
		righti = np.random.randint(0, len(diff))
		in_r[i,:] = inds[diff[righti]]
		out_r[i,:] = outds[diff[righti]]
	
	#for i in range(len(in_l)):
	#	print(str(out_l[i]) + "\t" + str(out_r[i]))
	
	#visualise the differences in the waveforms
	#i = 8
	#print(str(out_l[i]) + "\t" + str(out_r[i]))
	#plt.plot(in_l[i][:,0])
	#plt.plot(in_r[i][:,0])
	#plt.plot(np.abs(np.fft.fft(in_l[i][:,0])))		#this is cool, generally the same planes have a very similar fft and the different ones have noticeable differences
	#plt.plot(np.abs(np.fft.fft(in_r[i][:,0])))
	#plt.show()
	
	if with_raw_vals:
		return in_l, in_r, (out_l == out_r).astype(int), out_l, out_r
	else:
		return in_l, in_r, (out_l == out_r).astype(int)

def halfhalf_generator(inds, outds, batch_size=10):
	while True:
		(in_l, in_r, out) = select_half_half(inds, outds, batch_size)
		yield ([in_l, in_r], out)	#TF2.2
		#yield ([in_l, in_r], out, [None])	#handle TF2.1 bug

def halfhalf_testinggenerator(inds, outds, batch_size=10):
	while True:
		(in_l, in_r, out, out_l, out_r) = select_half_half(inds, outds, batch_size, True)		#third-last param to request raw data too
		yield ([in_l, in_r], out, out_l, out_r)	#TF2.2
		#yield ([in_l, in_r], out, [None], out_l, out_r)	#handle TF2.1 bug
		
def shuffle_in_unison_scary(a, b):
	#from: https://stackoverflow.com/questions/4601373/better-way-to-shuffle-two-numpy-arrays-in-unison (another, more elegant, answer in replies if needed)
    rng_state = np.random.get_state()
    np.random.shuffle(a)
    np.random.set_state(rng_state)
    np.random.shuffle(b)
	

#########################################

# Fingerprinting method
# 'first': First received message
# 'bestN': Best out of first fp_n received messages
#          Fingerprint is the message that maximises the similarity to the other messages out of the first 10 received messages
# 'centroidN': Centroid of first fp_n received messages
fp_method = 'centroidN'

# Multi-fingerprint config and setup
fp_dict = {}  # Temporary message storage until fingerprint is computed
fp_n = 10  # Number of messages considered for fingerprint
assert(fp_method is 'first' or fp_n > 0)

#get the model ready
print("Beginning ML")
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '1' #0 = all messages are logged (default behavior), 1 = INFO messages are not printed, 2 = INFO and WARNING messages are not printed, 3 = INFO, WARNING, and ERROR messages are not printed
import tensorflow as tf
from tensorflow.keras import layers, models

#limit gpu usage
gpus = tf.config.list_physical_devices('GPU')
if gpus:
	try:
		# Currently, memory growth needs to be the same across GPUs
		print("Setting GPU memory policy to 'grow as needed'")
		for gpu in gpus:
			tf.config.experimental.set_memory_growth(gpu, True)
		logical_gpus = tf.config.experimental.list_logical_devices('GPU')
		print(len(gpus), "Physical GPUs,", len(logical_gpus), "Logical GPUs")
	except RuntimeError as e:
		# Memory growth must be set before GPUs have been initialized
		print(e)

#from tensorflow.python.framework import ops

#ops.disable_eager_execution()
#if tf.executing_eagerly():
#	print("Warning: Eager execution is still enabled, performance will be severely impacted")

# if fp_method is not 'centroidN':
tf.compat.v1.disable_eager_execution()
if tf.executing_eagerly():
    print("Warning: Eager execution is still enabled, performance will be severely impacted")

print("Loading model")
#model = models.load_model("/data/mlsdr/siamese-hisamp.h5")
model = models.load_model("models/siamese-hisamp-94percent.h5")

# Extract the fingerprint generating model
fingerprint_model = models.Model(inputs=model.layers[2].input, outputs=model.layers[2].output)
fingerprint_input = layers.Input(shape=(256,), name="fp_input")
message_input = layers.Input(shape=(256,), name="msg_input")

# Create helper model for new messages
#helper_model = models.Model(inputs=[fingerprint_model.input], outputs=[fingerprint_model.call(fingerprint_model.input)])

# Pipe saved fingerprint and new message through final layers
#prediction = model.layers[4](model.layers[3]([fingerprint_input, helper_model.output]))
prediction = model.layers[4](model.layers[3]([fingerprint_input, message_input]))

# Connect the inputs with the outputs
# verification_model = models.Model(inputs=[fingerprint_input, fingerprint_model.input], outputs=prediction)
verification_model = models.Model(inputs=[fingerprint_input, message_input], outputs=prediction)

print("Fingerprinting messages")

oversampling_factor = 10
if len(sys.argv) < 2:
	h5siamese_filename = "/data/adsb-8er-jan2022.hdf5"
	#h5siamese_filename = "/data/mlsdr/adsb_rhb_20000000.0_1617410604-df17.hdf5"
else:
	h5siamese_filename = sys.argv[1]


(test_in, test_out, case_count, waveform_len, feature_count) = loadSiameseDatasets(h5siamese_filename)
print("Masking identifiers")
test_in = maskDataset(test_in, oversampling_factor, "NOICAO")
(case_count, waveform_len, feature_count) = test_in.shape

#keep track of aircraft we've seen and their last fingerprint(s)
known_aircraft = {}
results = { True: 0, False: 0}
result_logs = {}

t0 = time.time()
fp_df = fingerprint_model.predict(test_in)  # Fingerprint all the messages
t1 = time.time()
print(f"{t1 - t0}s")

# sess = tf.compat.v1.Session()
# sess.run(tf.compat.v1.global_variables_initializer())

t0 = time.time()
# for each message, compare it to the fingerprint
for msgi in range(case_count):
    if msgi % 1000 == 0:
        t1 = time.time()
        print(f"{t1 - t0}s")
        t0 = t1
        if results[True] + results[False] > 0:
            print((msgi, len(known_aircraft), results, results[True] / (results[True] + results[False])))
    (msg, claimedicao) = (test_in[msgi], test_out[msgi].tobytes().decode("utf-8"))

    # create fingerprint dataframe with icao? and is_fingerprint flag
    # predict everything, loop over to find fingerprints

    # if we have no previous fingerprint, then just save
    if claimedicao not in known_aircraft:
        save_fp = False
        fp = None
        if fp_method is 'centroidN':
            if fp_n == 1:
                # fp = fingerprint_model.predict([msg.reshape(1, 2400, 2)])
                fp = fp_df[msgi]
                save_fp = True
            elif claimedicao not in fp_dict:
                # fp_dict[claimedicao] = [fingerprint_model.predict([msg.reshape(1, 2400, 2)])]
                fp_dict[claimedicao] = [fp_df[msgi]]
            elif len(fp_dict[claimedicao]) < fp_n - 1:
                # fp_dict[claimedicao].append(fingerprint_model.predict([msg.reshape(1, 2400, 2)]))
                fp_dict[claimedicao].append(fp_df[msgi])
            else:
                # fp_dict[claimedicao].append(fingerprint_model.predict([msg.reshape(1, 2400, 2)]))
                fp_dict[claimedicao].append(fp_df[msgi])
                fp = np.mean(fp_dict[claimedicao], axis=0)
                del fp_dict[claimedicao]
                save_fp = True
        elif fp_method is 'bestN':
            if fp_n == 1:
                #fp = msg
                fp = fp_df[msgi]
                save_fp = True
            elif claimedicao not in fp_dict:
                #fp_dict[claimedicao] = [msg]
                fp_dict[claimedicao] = [fp_df[msgi]]
            elif len(fp_dict[claimedicao]) < fp_n - 1:
                #fp_dict[claimedicao].append(msg)
                fp_dict[claimedicao].append(fp_df[msgi])
            else:
                #fp_dict[claimedicao].append(msg)
                fp_dict[claimedicao].append(fp_df[msgi])
                fp_list = []
                for i, m in enumerate(fp_dict[claimedicao]):
                    fp_result = 0
                    for j, m_ in enumerate(fp_dict[claimedicao]):
                        if i == j:
                            continue
                        # fp_result += model.predict([m.reshape(1, waveform_len, feature_count),
                        #                            m_.reshape(1, waveform_len, feature_count)]).flatten()[0]
                        fp_result += verification_model.predict([m.reshape(1, 256), m_.reshape(1, 256)]).flatten()[0]
                    fp_list.append(fp_result)
                max_ = max(fp_list)
                fp = fp_dict[claimedicao][fp_list.index(max_)]
                del fp_dict[claimedicao]
                save_fp = True
        elif fp_method is 'first':
            # fp = msg
            fp = fp_df[msgi]
            save_fp = True
        else:
            raise ValueError('Invalid fingerprinting method given')
        if save_fp:
            assert fp is not None
            known_aircraft[claimedicao] = fp
            result_logs[claimedicao] = []
    # generate fingerprint
    # fp = fingerprint_model.predict(msg.reshape(1, 2400, 2))
    # known_aircraft[claimedicao] = fp
    # print("New aircraft {}, stored fingerprint".format(fp))

    # known_aircraft[claimedicao] = msg
    # print("New aircraft {}, stored MESSAGE".format(claimedicao))
    # result_logs[claimedicao] = []
    else:  # otherwise check the fingerprint
        if fp_method is 'first':
            # compare_result = model.predict([msg.reshape(1, 2400, 2), known_aircraft[claimedicao].reshape(1, 2400, 2)])
            compare_result = verification_model.predict([fp_df[msgi].reshape(1, 256), known_aircraft[claimedicao].reshape(1, 256)])
            match = compare_result.flatten()[0] > 0.5
        elif fp_method is 'bestN':
            # compare_result = model.predict([msg.reshape(1, 2400, 2), known_aircraft[claimedicao].reshape(1, 2400, 2)])
            compare_result = verification_model.predict([fp_df[msgi].reshape(1, 256), known_aircraft[claimedicao].reshape(1, 256)])
            match = compare_result.flatten()[0] > 0.5
        elif fp_method is 'centroidN':
            # result = model.predict([msg.reshape(1, 2400, 2), msg.reshape(1, 2400, 2)])
            # compare_result = verification_model.predict([known_aircraft[claimedicao], msg.reshape(1, 2400, 2)])
            compare_result = verification_model.predict([fp_df[msgi].reshape(1, 256), known_aircraft[claimedicao].reshape(1, 256)])
            match = compare_result.flatten()[0] > 0.5
        else:
            raise ValueError('Invalid fingerprinting method given')
        # print("Message for {} matches: {}".format(claimedicao, match))
        results[match] += 1
        result_logs[claimedicao].append(match)
    # if match:
    #	known_aircraft[claimedicao] = msg

print(results)
rli = 1
for (k, v) in result_logs.items():
	#plt.subplot(len(result_logs), 1, rli)
	plt.plot(v, label=k)
	plt.savefig("verifications/"+str(k))
	plt.clf()
	rli += 1
#plt.show()