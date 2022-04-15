import numpy as np
import matplotlib.pyplot as plt
import h5py
import adsb_siamese_common as asc
import adsb_siamese_constants as const

#import pyModeS as modes

def getSiameseModel():
	left_input = layers.Input((waveform_len, 2))
	right_input = layers.Input((waveform_len, 2))
	
	dummy_input = layers.Input((waveform_len, 2))
	l = layers.BatchNormalization()(dummy_input)
	l = layers.ZeroPadding1D(padding=2)(l)
	
	l = layers.Conv1D(64, 2, activation='relu')(l)
	l = layers.MaxPooling1D()(l)
	l = layers.Conv1D(64, 4, activation='relu')(l)
	l = layers.MaxPooling1D()(l)
	l = layers.Conv1D(32, 8, activation='relu')(l)
	l = layers.MaxPooling1D()(l)
	l = layers.Conv1D(32, 16, activation='relu')(l)
	l = layers.MaxPooling1D()(l)
	l = layers.Conv1D(32, 32, activation='relu')(l)
	l = layers.MaxPooling1D()(l)
	
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
	siamese_net = models.Model(inputs=[left_input, right_input], outputs=prediction)
	
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

#########################################

SHOULD_TRAIN = False


#get the model ready
print("Beginning ML")
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '1' #0 = all messages are logged (default behavior), 1 = INFO messages are not printed, 2 = INFO and WARNING messages are not printed, 3 = INFO, WARNING, and ERROR messages are not printed
import tensorflow as tf
from tensorflow.keras import layers, models

#limit gpu usage
asc.tf_tweak_limit_gpu_memory_usage()

if SHOULD_TRAIN:
	print("Training model")
	
	print("Loading datasets")
	#h5siamese_filename = "/data/mlsdr/siamese-4rc-adsb-24h-20200916-allsuccesses.hdf5"							#original captures with rtlsdr
	#h5siamese_filename = "/data/mlsdr/adsb_20000000.0_1616673750-df17.hdf5"										#new high sample-rate captures
	#h5siamese_filename = "/data/mlsdr/adsb_20000000.0_1616720475-df17.hdf5"
	h5siamese_filename = "/data/mlsdr/adsb_20000000.0_1617071599-df17.hdf5"
	oversampling_factor = 10
	(train_in, train_out, case_count, waveform_len, feature_count) = asc.loadSiameseDatasets(h5siamese_filename)
	asc.validate_dataset_dimensions(case_count, waveform_len, feature_count)
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
	train_in = asc.maskDataset(train_in, oversampling_factor, "NOICAO")					#options: NONE, HEADERONLY, NOICAO, NOICAOORLATLON and the opposite INVERSE-ICAOONLY

	model = getSiameseModel()
	model.summary()
	#from tensorflow.keras.utils import plot_model
	#plot_model(model, to_file='model_plot.png', show_shapes=True, show_layer_names=True)
	#
	#exit()

	model.compile(optimizer='adam', loss='binary_crossentropy')

	hist = model.fit(x=asc.halfhalf_generator(train_in, train_out, 100), epochs=15, steps_per_epoch=len(train_in) // 100)
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


#print("Doing x-way one shot validation")
#
#print(select_xway_oneshot(inds, outds, 4))


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
(test_in, test_out, case_count, waveform_len, feature_count) = asc.loadSiameseDatasets(h5siamese_filename)
asc.validate_dataset_dimensions(case_count, waveform_len, feature_count)

print("Masking identifiers")
test_in = asc.maskDataset(test_in, oversampling_factor, "NOICAO")

test_batches = 1000000
batch_size = 10
test_sum = 0
test_count = 0
for ([in_l, in_r], matches, out_l, out_r) in asc.halfhalf_testinggenerator(test_in, test_out, batch_size):
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
