import numpy as np
import matplotlib.pyplot as plt
import h5py

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
	
	###general inception-style layers
	#for i in range(1):
	#	conv1 = layers.Conv1D(32, 1, padding="same", activation="relu")(l)
	#	conv3 = layers.Conv1D(64, 3, padding="same", activation="relu")(l)
	#	conv5 = layers.Conv1D(16, 5, padding="same", activation="relu")(l)
	#	pool = layers.MaxPooling1D(3, strides=1, padding='same')(l)
	#	l = layers.concatenate([conv1, conv3, conv5, pool], axis=-1)
		
	
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
	end = (start + way)
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
	for i in range(1, way, 1):
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



#if SHOULD_TRAIN:
if True:
	print("Training model")
	
	print("Loading datasets")
	h5siamese_filename = "/data/mlsdr/rs485-decoded-4tx-splitbytes-31.25msps-ideal.hdf5"
	(train_in, train_out, case_count, waveform_len, feature_count) = loadSiameseDatasets(h5siamese_filename, subset=30000)
	print((train_in.shape, train_out.shape, case_count, waveform_len, feature_count))
	
	(case_count, waveform_len, feature_count) = train_in.shape
	print(train_in.shape)
	
	##normalise input waves
	#for i in range(case_count):
	#	train_in[i,:,0] /= np.max(np.abs(train_in[i,:,0]))
	#	train_in[i,:,1] /= np.max(np.abs(train_in[i,:,1]))
	#	#train_in[i,:,0] -= np.mean(train_in[i,:,0])
	#	#train_in[i,:,1] -= np.mean(train_in[i,:,1])

if SHOULD_TRAIN:
		
	model = getSiameseModel()
	model.summary()

	model.compile(optimizer='adam', loss='binary_crossentropy')
	#model.compile(optimizer=tf.keras.optimizers.Adam(epsilon=0.001, learning_rate=tf.keras.optimizers.schedules.ExponentialDecay(initial_learning_rate=1e3, decay_steps=1000, decay_rate=0.85)), loss='binary_crossentropy')

	hist = model.fit(x=halfhalf_generator(train_in, train_out, 20), epochs=15, steps_per_epoch=len(train_in)//20)
	#hist = model.fit_generator(halfhalf_generator(train_in, train_out, 100), epochs=10, steps_per_epoch=len(train_in)//100)

	print("Saving model")
	model.save("models/rs485-siamese.h5")

	plt.plot(hist.history["loss"])
	plt.show()

else:
	print("Loading model")
	model = models.load_model("models/rs485-siamese.h5")
	#model = models.load_model("models/rs485-siamese-fluke99.9percent.h5")
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


#print("Loading datasets")
#h5siamese_filename = "/data/mlsdr/rs485-decoded-4tx-splitbytes-31.25msps.hdf5"
#(inds, outds, case_count, waveform_len, feature_count) = loadSiameseDatasets(h5siamese_filename, subset=5000)
##normalise input waves
#for i in range(case_count):
#	inds[i,:,0] /= np.max(np.abs(inds[i,:,0]))
#	inds[i,:,1] /= np.max(np.abs(inds[i,:,1]))



del train_in
del train_out

print("Testing on different dataset")
h5siamese_filename = "/data/mlsdr/rs485-decoded-4tx-splitbytes-31.25msps-ideal.hdf5"
#h5siamese_filename = "/data/mlsdr/rs485-decoded-4tx-splitbytes-31.25msps-scopelongreel.hdf5"
#h5siamese_filename = "/data/mlsdr/rs485-decoded-4tx-splitbytes-31.25msps-tx2longreel.hdf5"
(test_in, test_out, case_count, waveform_len, feature_count) = loadSiameseDatasets(h5siamese_filename, subset=10000)
(case_count, waveform_len, feature_count) = test_in.shape

##normalise input waves
#for i in range(case_count):
#	test_in[i,:,0] /= np.max(np.abs(test_in[i,:,0]))
#	test_in[i,:,1] /= np.max(np.abs(test_in[i,:,1]))
#	#test_in[i,:,0] -= np.mean(test_in[i,:,0])
#	#test_in[i,:,1] -= np.mean(test_in[i,:,1])


#test an (almost) endless sequence of waveform batches and track the running accuracy PER DEVICE (overall accuracy lower down)
test_batches = 1000000
batch_size = 10
test_sums = {}
test_counts = {}
for ([in_l, in_r], matches, out_l, out_r) in halfhalf_testinggenerator(test_in, test_out, batch_size):
	if test_batches <= 0:
		break
		
	distances = model.predict([in_l, in_r])
	decisions = np.round(distances).astype(int)

	correct = matches == decisions
	#ncorrect = np.sum(correct.astype(int))

	for i in range(len(correct)):
		if out_l[i][0] not in test_sums:
			test_sums[out_l[i][0]] = 0
		test_sums[out_l[i][0]] += correct.astype(int)[i][0]
		if out_l[i][0] not in test_counts:
			test_counts[out_l[i][0]] = 0
		test_counts[out_l[i][0]] += 1
	
	if test_batches % 100 == 0:
		for tx in test_counts:
			(ts, tc) = test_sums[tx], test_counts[tx]
			print(f"{tx} : {ts}, {tc} -> {ts/tc}")
		print()
	
	test_batches -= 1
exit()

#x-way one shot validation
print("Doing x-way one shot validation")
inds, outds = test_in, test_out
for way in [2, 3, 4, 5, 9, 15, 25]:
	nruns = 100
	ncorrect = 0
	for i in range(nruns):
		(in_l, in_r, matches) = select_xway_oneshot(inds, outds, way, with_raw_vals=False)

		similarity = model.predict([in_l, in_r])
		decisions = np.round(similarity).astype(int)

		correctbest = matches			#as there is intentionally only one real one, it should be the best
		#import random
		#if random.random() > 0.9:
		#	correctbest = np.roll(matches, 1)
		#else:
		#	correctbest = matches
		pickbest = (similarity == np.max(similarity)).astype(int)

		#print((matches, similarity, decisions, matches == decisions))
		#print((list(matches.flatten()), list(decisions.flatten())))
		
		#print(np.all(correctbest == pickbest))
		correct_result = np.all(correctbest == pickbest)
		if correct_result :
			ncorrect += 1
			
	print(f"{way}-way testing on {nruns} runs: {ncorrect} / {nruns} = {ncorrect/nruns}")
exit()



#test an (almost) endless sequence of waveform batches and track the running accuracy
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
