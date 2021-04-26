import numpy as np
import h5py
import pyModeS as modes

def shuffle_in_unison_scary(a, b):
	#from: https://stackoverflow.com/questions/4601373/better-way-to-shuffle-two-numpy-arrays-in-unison (another, more elegant, answer in replies if needed)
    rng_state = np.random.get_state()
    np.random.shuffle(a)
    np.random.set_state(rng_state)
    np.random.shuffle(b)


#h5in = h5py.File("/data/mlsdr/4rc-adsb-captures/4rc-adsb-24h-20200916-allsuccesses.hdf5", "r")
#h5dump = h5py.File("/data/mlsdr/4rc-adsb-captures/4rc-adsb-24h-20200916-dump1090-allsuccesses.hdf5", "r")

h5in = h5py.File("/data/mlsdr/4rc-adsb-captures/4rc-adsb-24h-20200917-allsuccesses.hdf5", "r")
h5dump = h5py.File("/data/mlsdr/4rc-adsb-captures/4rc-adsb-24h-20200917-dump1090-allsuccesses.hdf5", "r")

inds = h5in["bursts"]
outds = h5dump["dump1090_datahex"]

# Transform into I/Q features
feats = np.empty(shape=(inds.shape[0], inds.shape[1], 2)); 
feats[:,:,0] = np.real(inds)
feats[:,:,1] = np.imag(inds)
inds = feats

#load the dump1090 output, then extract icaos from it
outcache = np.array(outds)
outds = np.chararray(shape=outcache.shape, itemsize=6)
for i in range(len(outcache)):
	outds[i,:] = modes.icao(outcache[i,:].tobytes().decode("utf-8"))
del outcache

#shuffle inplace to attempt equal distribution of messages
shuffle_in_unison_scary(inds, outds)

#h5out = h5py.File("/data/mlsdr/siamese-4rc-adsb-24h-20200916-allsuccesses.hdf5", "w")
h5out = h5py.File("/data/mlsdr/siamese-4rc-adsb-24h-20200917-allsuccesses.hdf5", "w")
#h5py.create_dataset("
h5out["inds"] = inds
h5out["outds"] = outds
h5out.close()

h5dump.close()
h5in.close()
