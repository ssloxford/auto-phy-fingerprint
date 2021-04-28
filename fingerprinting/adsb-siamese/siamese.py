import numpy as np
import matplotlib.pyplot as plt
import h5py
#import pyModeS as modes


#def getSiameseModel():
#	left_input = layers.Input((waveform_len, 2))
#	right_input = layers.Input((waveform_len, 2))
#	
#	model = models.Sequential()
#	
#	#model.add(layers.Input(shape=(waveform_len,2)))
#	model.add(layers.BatchNormalization())
#	model.add(layers.ZeroPadding1D(padding=2))
#	#model.add(layers.UpSampling1D(size=6))
#	print("***NOT UPSAMPLING BECAUSE USING 20MSPS DATA NOW***")
#	
#	#64,48,32,16 did well (91.4% after long lunch)
#	#model.add(layers.Conv1D(48, 2, activation='relu'))			#copied from my decoding model
#	model.add(layers.Conv1D(64, 2, activation='relu'))			#copied from my decoding model
#	#model.add(layers.Conv1D(16, 8, activation='relu'))			#'normal' layer from Siamese tutorial		(seemed to perform worse with high-samp captures)
#	model.add(layers.MaxPooling1D())
#	
#	model.add(layers.Conv1D(64, 4, activation='relu'))			#copied from my decoding model
#	#model.add(layers.Conv1D(32, 4, activation='relu'))			#'normal' layer from Siamese tutorial
#	model.add(layers.MaxPooling1D())
#	
#	model.add(layers.Conv1D(32, 8, activation='relu'))			#copied from my decoding model
#	#model.add(layers.Conv1D(48, 2, activation='relu'))			#'normal' layer from Siamese tutorial
#	model.add(layers.MaxPooling1D())
#
#	model.add(layers.Conv1D(32, 16, activation='relu'))			#added
#	model.add(layers.MaxPooling1D())
#	
#	model.add(layers.Conv1D(32, 32, activation='relu'))			#added
#	model.add(layers.MaxPooling1D())
#
#
##	model.add(layers.Conv1D(4, 8, activation='relu'))			#added
##	model.add(layers.MaxPooling1D())
#	
#	## general VGG-style layers
#	#for i in range(8):
#	#	model.add(layers.Conv1D(32, 3, padding='same', activation='relu'))
#	#model.add(layers.MaxPooling1D(strides=2))
#
#
##	##general inception-style layers
##	lastlayer = model.layers[-1]()
##	for i in range(1):
##		conv1 = layers.Conv1D(32, 1, padding="same", activation="relu")(lastlayer)
##		conv3 = layers.Conv1D(64, 3, padding="same", activation="relu")(lastlayer)
##		conv5 = layers.Conv1D(16, 5, padding="same", activation="relu")(lastlayer)
##		pool = layers.MaxPooling1D(3, 1, padding="same")(lastlayer)
##		lout = layers.concatenate([conv1, conv3, conv5, pool], axis=-1)
##		model.add(lout)
##		lastlayer = lout
#
#
#	
#	model.add(layers.Flatten())
#	
#	model.add(layers.Dense(256, activation="sigmoid"))			#original 1024 didn't seem to do better than 256
#	
#	encoded_l = model(left_input)
#	encoded_r = model(right_input)
#	
#	# Add a customized layer to compute the absolute difference between the encodings
#	L1_layer = layers.Lambda(lambda tensors: tf.keras.backend.abs(tensors[0] - tensors[1]))
#	L1_distance = L1_layer([encoded_l, encoded_r])
#	
#	# Add a dense layer with a sigmoid unit to generate the similarity score
#	#prediction = layers.Dense(1,activation='sigmoid',bias_initializer=initialize_bias)(L1_distance)
#	prediction = layers.Dense(1,activation='sigmoid')(L1_distance)
#	
#	# Connect the inputs with the outputs
#	siamese_net = models.Model(inputs=[left_input,right_input],outputs=prediction)
#	
#	# return the model
#	return siamese_net



#def getInceptionSiameseModel():
#        left_input = layers.Input((waveform_len, 2))
#        right_input = layers.Input((waveform_len, 2))
#
#	model = models.Model()
#
#	##general inception-style layers
#	for i in range(1):
#		conv1 = layers.Conv1D(32, 1, padding="same", activation="relu")
#		conv3 = layers.Conv1D(64, 3, padding="same", activation="relu")
#		conv5 = layers.Conv1D(16, 5, padding="same", activation="relu")
#


def getSiameseModel():
	left_input = layers.Input((waveform_len, 2))
	right_input = layers.Input((waveform_len, 2))
	
	dummy_input = layers.Input((waveform_len, 2))
	l = layers.BatchNormalization()(dummy_input)
	l = layers.ZeroPadding1D(padding=2)(l)
	
	#l = layers.Conv1D(64, 2, activation='relu')(l)
	#l = layers.MaxPooling1D()(l)
	#l = layers.Conv1D(64, 4, activation='relu')(l)
	#l = layers.MaxPooling1D()(l)
	#l = layers.Conv1D(32, 8, activation='relu')(l)
	#l = layers.MaxPooling1D()(l)
	#l = layers.Conv1D(32, 16, activation='relu')(l)
	#l = layers.MaxPooling1D()(l)
	#l = layers.Conv1D(32, 32, activation='relu')(l)
	#l = layers.MaxPooling1D()(l)
	
	##general inception-style layers
	for i in range(1):
		conv1 = layers.Conv1D(32, 1, padding="same", activation="relu")(l)
		conv3 = layers.Conv1D(64, 3, padding="same", activation="relu")(l)
		conv5 = layers.Conv1D(16, 5, padding="same", activation="relu")(l)
		pool = layers.MaxPooling1D(3, strides=1, padding='same')(l)
		l = layers.concatenate([conv1, conv3, conv5, pool], axis=-1)
		
	
	l = layers.Flatten()(l)
	
	l = layers.Dense(256, activation="sigmoid")(l)
	
	extractor = models.Model(inputs=[dummy_input], outputs=[l])
	
	#intermediate model with fingerprints on both sides	
	encoded_l = models.Model(inputs=[left_input], outputs=[extractor.call(left_input)])			#call() cuts off old input layer and attaches new one
	encoded_r = models.Model(inputs=[right_input], outputs=[extractor.call(right_input)])
	
	# Add a customized layer to compute the absolute difference between the encodings
	L1_layer = layers.Lambda(lambda tensors: tf.keras.backend.abs(tensors[0] - tensors[1]))
	L1_distance = L1_layer([encoded_l.output, encoded_r.output])
	
	# Add a dense layer with a sigmoid unit to generate the similarity score
	prediction = layers.Dense(1,activation='sigmoid')(L1_distance)
	
	# Connect the inputs with the outputs
	siamese_net = models.Model(inputs=[left_input,right_input],outputs=prediction)
	
	# return the model
	return siamese_net

#not working with siamese model and don't (currently) know how to fix
def flatten_model(model_nested):
    layers_flat = []
    for layer in model_nested.layers:
        try:
            layers_flat.extend(layer.layers)
        except AttributeError:
            layers_flat.append(layer)
    print(layers_flat)
    model_flat = models.Sequential(layers_flat)
    return model_flat

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

"""
Create a batch of samples, with x-way one shot learning. Based on select_halfhalf above.
"""
def select_xway_oneshot(inds, outds, way=4, with_raw_vals=False):	
	start = np.random.randint(0, len(inds))
	end = (start + batch_size)
	batchi = np.arange(start, end)
	
	in_l = np.take(inds, batchi, axis=0, mode="wrap")
	out_l = np.take(outds, batchi, axis=0, mode="wrap")

	in_r = np.empty_like(in_l)
	out_r = np.empty_like(out_l)

	#first element of right-hand side is matching (ideally not same entry, but ignore here as there are some singular entries)
	same = np.argwhere(outds.reshape(-1) == out_l[0]).flatten()
	righti = np.random.randint(0, len(same))
	in_r[0,:] = inds[same[righti]]
	out_r[0,:] = outds[same[righti]]
	
	#rest is not matching
	for i in range(way - 1, 1, 1):
		diff = np.argwhere(outds.reshape(-1) != out_l[i]).flatten()
		righti = np.random.randint(0, len(diff))
		in_r[i,:] = inds[diff[righti]]
		out_r[i,:] = outds[diff[righti]]
	
	if with_raw_vals:
		return in_l, in_r, (out_l == out_r).astype(int), out_l, out_r
	else:
		return in_l, in_r, (out_l == out_r).astype(int)

def shuffle_in_unison_scary(a, b):
	#from: https://stackoverflow.com/questions/4601373/better-way-to-shuffle-two-numpy-arrays-in-unison (another, more elegant, answer in replies if needed)
    rng_state = np.random.get_state()
    np.random.shuffle(a)
    np.random.set_state(rng_state)
    np.random.shuffle(b)
	

#########################################

SHOULD_TRAIN = False


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



if SHOULD_TRAIN:

	print("Training model")
	
	print("Loading datasets")
	#h5siamese_filename = "/data/mlsdr/siamese-4rc-adsb-24h-20200916-allsuccesses.hdf5"							#original captures with rtlsdr
	#h5siamese_filename = "/data/mlsdr/adsb_20000000.0_1616673750-df17.hdf5"										#new high sample-rate captures
	#h5siamese_filename = "/data/mlsdr/adsb_20000000.0_1616720475-df17.hdf5"
	h5siamese_filename = "/data/mlsdr/adsb_20000000.0_1617071599-df17.hdf5"
	oversampling_factor = 10
	(train_in, train_out, case_count, waveform_len, feature_count) = loadSiameseDatasets(h5siamese_filename)
	print((train_in.shape, train_out.shape, case_count, waveform_len, feature_count))
	
	#preliminary results (accuracy on different day's capture in long randomised trials, 3 epoch training and ~50000 trials testing):
	#	NONE (no masking)			99.63% acc (0.0124 loss)
	#	HEADERONLY*					85.70% acc (0.3545 loss)	*this masking truncated rather than zeroed 
	#	HEADERONLY					84.13% acc (0.3627 loss)
	#	NOICAO						87.32% acc (0.2981 loss)
	#	NOICAOORLATLON				85.64% acc (0.3269 loss)
	# and to demonstrate
	#	INVERSE-ICAOONLY			99.75% acc (0.0105 loss)
	print("Masking identifiers")
	train_in = maskDataset(train_in, oversampling_factor, "NOICAO")					#options: NONE, HEADERONLY, NOICAO, NOICAOORLATLON and the opposite INVERSE-ICAOONLY
	(case_count, waveform_len, feature_count) = train_in.shape
	print(train_in.shape)
	
	model = getSiameseModel()
	model.summary()
	#from tensorflow.keras.utils import plot_model
	#plot_model(model, to_file='model_plot.png', show_shapes=True, show_layer_names=True)
	#
	#exit()

	model.compile(optimizer='adam', loss='binary_crossentropy')

	hist = model.fit(x=halfhalf_generator(train_in, train_out, 100), epochs=15, steps_per_epoch=len(train_in)//100)
	#hist = model.fit_generator(halfhalf_generator(train_in, train_out, 100), epochs=10, steps_per_epoch=len(train_in)//100)

	print("Saving model")
	#model.save("/data/mlsdr/siamese-masknoicao.h5")
	#model.save("models/siamese-hisamp.h5")
	model.save("models/siamese-hisamp-testnewmodel.h5")

	plt.plot(hist.history["loss"])
	plt.show()

else:
	print("Loading model")
	#model = models.load_model("/data/mlsdr/siamese-masknoicao.h5")
	#model = models.load_model("/data/mlsdr/siamese-hisamp.h5")
	model = models.load_model("models/siamese-hisamp.h5")
	model.summary()
	
	#flatmodel = flatten_model(model)
	#flatmodel.summary()
	
	#from keras.utils.vis_utils import plot_model
	#plot_model(model, to_file='model_plot.png', show_shapes=True, show_layer_names=True)
	
#for l in model.layers[2].layers:
#	print(l)
#print(model.layers[2].layers[3].weights[0].shape)
#for i in range(2):
#	plt.plot(model.layers[2].layers[3].weights[0][i,0,:])
#	#plt.plot(np.abs(model.layers[2].layers[2].weights[0][i,0,:]))   #no upsampling layer
#plt.show()


#model.summary()
#tf.keras.utils.plot_model(model, to_file='model_plot.png', show_shapes=True, show_layer_names=True)


######some testing
#print("Lightweight testing")
#test_count = 10
#for ([in_l, in_r], matches, _, out_l, out_r) in halfhalf_testinggenerator(train_in, train_out, 10):
#	distances = model.predict([in_l, in_r])
#	for i in range(len(matches)):
#		occurrences_l = np.sum((train_out == out_l[i]).astype(int))
#		occurrences_r = np.sum((train_out == out_r[i]).astype(int))
#		print("{} vs. {} ({} and {}) : {} --> {}".format(out_l[i], out_r[i], occurrences_l, occurrences_r, matches[i], distances[i]))
#	if test_count > 0:
#		test_count -= 1
#		continue
#	break

##get the sparse representation
#sparse_rep_model = models.Model(inputs=model.input, outputs=model.layers[2].layers[-1].output)
#for ([in_l, in_r], matches, _, out_l, out_r) in halfhalf_testinggenerator(train_in, train_out, 10):
#	sparse_reps = sparse_rep_model.predict([in_l, in_r])
#	print(sparse_reps.shape)
#	for i in range(len(sparse_reps)):
#		plt.subplot(len(sparse_reps), 1, i+1)
#		plt.plot(sparse_reps[i,:])
#	plt.show()
#	break


print("Doing x-way one shot validation")

print(select_xway_oneshot(inds, outds, 4))


exit()

print("Testing on different dataset")
#h5siamese_filename = "/data/mlsdr/siamese-4rc-adsb-24h-20200917-allsuccesses.hdf5"
#h5siamese_filename = "/data/mlsdr/adsb_20000000.0_1616673750-df17.hdf5"										#new high sample-rate captures			#WARN: testing on training data
#h5siamese_filename = "/data/mlsdr/adsb_20000000.0_1616720475-df17.hdf5"										#new high sample-rate captures			#WARN: testing on training data
#h5siamese_filename = "/data/mlsdr/adsb_20000000.0_1616803398-df17.hdf5"
#h5siamese_filename = "/data/mlsdr/adsb_20000000.0_1616899669-df17.hdf5"
#h5siamese_filename = "/data/mlsdr/adsb_20000000.0_1617071599-df17.hdf5"
h5siamese_filename = "/data/mlsdr/adsb_rhb_20000000.0_1617410604-df17.hdf5"
oversampling_factor = 10
(test_in, test_out, case_count, waveform_len, feature_count) = loadSiameseDatasets(h5siamese_filename)
print("Masking identifiers")
test_in = maskDataset(test_in, oversampling_factor, "NOICAO")
(case_count, waveform_len, feature_count) = test_in.shape

test_batches = 1000000
batch_size = 10
test_sum = 0
test_count = 0
for ([in_l, in_r], matches, out_l, out_r) in halfhalf_testinggenerator(test_in, test_out, batch_size):
	if test_batches <= 0:
		break
		
	distances = model.predict([in_l, in_r])
	decisions = np.round(distances).astype(int)
	
	##detailed information on each value (inc. how often that icao appears in the dataset)
	#for i in range(len(matches)):
	#	occurrences_l = np.sum((test_out == out_l[i]).astype(int))
	#	occurrences_r = np.sum((test_out == out_r[i]).astype(int))
	#	print("{} vs. {} ({} and {}) : {} --> {} ({})".format(out_l[i], out_r[i], occurrences_l, occurrences_r, matches[i], distances[i], np.round(distances[i]).astype(int)))
	
	#print((matches == decisions).flatten())
	#print(np.sum((matches == decisions).astype(int)))
	
	correct = matches == decisions
	ncorrect = np.sum(correct.astype(int))
	#if ncorrect != batch_size:		#at least one was wrong
	#	for i in range(batch_size):
	#		if not correct[i]:
	#			occurrences_l = np.sum((test_out == out_l[i]).astype(int))
	#			occurrences_r = np.sum((test_out == out_r[i]).astype(int))
	#			print("Failed: {} vs. {} ({} and {}) : {} --> {} ({})".format(out_l[i], out_r[i], occurrences_l, occurrences_r, matches[i], distances[i], np.round(distances[i]).astype(int)))
		
	test_sum += ncorrect
	test_count += batch_size
	if test_batches % 100 == 0:
		print(test_sum, test_count, test_sum / test_count)
	
	test_batches -= 1
