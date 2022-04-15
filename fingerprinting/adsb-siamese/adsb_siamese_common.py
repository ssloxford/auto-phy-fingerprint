import numpy as np
import h5py
import tensorflow as tf

import adsb_siamese_constants as const

def tf_tweak_limit_gpu_memory_usage():
	# limit gpu usage
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

def tf_tweak_disable_eager_execution():
	from tensorflow.python.framework.ops import disable_eager_execution
	disable_eager_execution()
	if tf.executing_eagerly():
		print("Warning: Eager execution is still enabled, performance will be severely impacted")


def loadSiameseDatasets(h5siamese_filename, subset=None):
	h5in = h5py.File(h5siamese_filename, "r")
	inds = h5in["inds"]
	outds = h5in["outds"]

	if subset != None:
		inds = inds[:subset]
		outds = outds[:subset]

	# load the datasets into memory for speed
	inds = np.array(inds)
	outds = np.array(outds)

	(case_count, waveform_len, feature_count) = inds.shape

	h5in.close()

	return (inds, outds, case_count, waveform_len, feature_count)

def validate_dataset_dimensions(case_count, waveform_len, feature_count):
	if waveform_len != const.message_symbols * const.oversampling_factor:
		raise ValueError(f"Input waveform length of {waveform_len} is not expected size based on constants file ({const.message_symbols * const.oversampling_factor})")
	if feature_count != const.iq_sampling_feature_count:
		raise ValueError(f"Input channel depth of {feature_count} is not expected size based on constants file ({const.iq_sampling_feature_count})")

def maskDataset(inds, osf, maskname):
	if maskname is None or maskname == "NONE":
		return inds  # nothing
	elif maskname == "HEADERONLY":
		return inds[:, :32 * osf,
			   :]  # aggressive masking, 32 samples is only the beginning of the header, no icao, no data, no crc
		# inds[:,32*osf:,:] = 0.0
		return inds
	elif maskname == "NOICAO":
		inds[:, 32 * osf:80 * osf, :] = 0.0  # masking out icao
		return inds
	elif maskname == "INVERSE-ICAOONLY":
		inds[:, :32 * osf, :] = 0.0  # inverse icao masking -- leaving *only* the icao
		inds[:, 80 * osf:, :] = 0.0  # inverse icao masking -- leaving *only* the icao
		return inds
	elif maskname == "NOICAOORLATLON":
		inds[:, 32 * osf:80 * osf, :] = 0.0  # masking out icao
		inds[:, 124 * osf:192 * osf, :] = 0.0  # masking out latlon
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

	# out_r[:] = "none"

	# first half of right-hand side is matching (ideally not same entry, but ignore here as there are some singular entries)
	for i in range(batch_size // 2):
		same = np.argwhere(outds.reshape(-1) == out_l[i]).flatten()
		righti = np.random.randint(0, len(same))
		in_r[i, :] = inds[same[righti]]
		out_r[i, :] = outds[same[righti]]

	# second half is not matching
	for i in range(batch_size // 2, batch_size, 1):
		diff = np.argwhere(outds.reshape(-1) != out_l[i]).flatten()
		righti = np.random.randint(0, len(diff))
		in_r[i, :] = inds[diff[righti]]
		out_r[i, :] = outds[diff[righti]]

	# for i in range(len(in_l)):
	#	print(str(out_l[i]) + "\t" + str(out_r[i]))

	# visualise the differences in the waveforms
	# i = 8
	# print(str(out_l[i]) + "\t" + str(out_r[i]))
	# plt.plot(in_l[i][:,0])
	# plt.plot(in_r[i][:,0])
	# plt.plot(np.abs(np.fft.fft(in_l[i][:,0])))		#this is cool, generally the same planes have a very similar fft and the different ones have noticeable differences
	# plt.plot(np.abs(np.fft.fft(in_r[i][:,0])))
	# plt.show()

	if with_raw_vals:
		return in_l, in_r, (out_l == out_r).astype(int), out_l, out_r
	else:
		return in_l, in_r, (out_l == out_r).astype(int)


def halfhalf_generator(inds, outds, batch_size=10):
	while True:
		(in_l, in_r, out) = select_half_half(inds, outds, batch_size)
		yield ([in_l, in_r], out)  # TF2.2
	# yield ([in_l, in_r], out, [None])	#handle TF2.1 bug


def halfhalf_testinggenerator(inds, outds, batch_size=10):
	while True:
		(in_l, in_r, out, out_l, out_r) = select_half_half(inds, outds, batch_size,
														   True)  # third-last param to request raw data too
		yield ([in_l, in_r], out, out_l, out_r)  # TF2.2
	# yield ([in_l, in_r], out, [None], out_l, out_r)	#handle TF2.1 bug


def shuffle_in_unison_scary(a, b):
	# from: https://stackoverflow.com/questions/4601373/better-way-to-shuffle-two-numpy-arrays-in-unison (another, more elegant, answer in replies if needed)
	rng_state = np.random.get_state()
	np.random.shuffle(a)
	np.random.set_state(rng_state)
	np.random.shuffle(b)
