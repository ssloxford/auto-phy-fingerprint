import h5py
import numpy as np

"""
Load a dataset from an HDF5 file.
    Parameters:
        h5filename: the filename of the HDF5 file
        subset: the number of cases to load from the file
    Returns:
        inds: the input data (waveform)
        outds: the output data (fixed-length string of the ICAO)
        case_count: the number of cases in the dataset
        waveform_len: the number of samples in each waveform
        feature_count: the number of features in each waveform
"""
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
Mask the input dataset to remove identifying information.
NONE: no masking
HEADERONLY: mask the first 32 samples of each waveform (beginning of the header, no icao/data/crc)
NOICAO: mask out the ICAO
INVERSE-ICAOONLY: mask out everything except the ICAO
NOICAOORLATLON: mask out the ICAO and the latlon
    Parameters:
        inds: the input data (waveform)
        osf: the oversampling factor
        maskname: the name of the mask to use
    Returns:
        inds: the input data masked to remove identifying information.
"""
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
        raise ValueError("Unknown mask name.")

"""
Create a batch of pairwise samples, where half are the same class left-and-right and half are different classes left-and-right.
This is much easier if the dataset has equal blocks of each, but we don't have that, so a lot of expensive lookups are needed (lucky numpy is fast).
    Parameters:
        inds: the input data
        outds: the output data
        batch_size: the number of samples in the batch
        with_raw_vals: whether to return the values of outds as well
    Returns:
        TODO
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

"""
Create a generator of pairwise samples, where half are the same class left-and-right and half are different classes left-and-right.
    Parameters:
        inds: the input data
        outds: the output data
        batch_size: the number of samples in the batch
        with_raw_vals: whether to return the values of outds as well
    Returns:
        TODO
"""
def halfhalf_generator(inds, outds, batch_size=10):
    while True:
        (in_l, in_r, out) = select_half_half(inds, outds, batch_size)
        yield ([in_l, in_r], out)

"""
Create a generator of pairwise samples, where half are the same class left-and-right and half are different classes left-and-right.
Also yield output values for use in testing.
    Parameters:
        inds: the input data
        outds: the output data
        batch_size: the number of samples in the batch
        with_raw_vals: whether to return the values of outds as well
    Returns:
        TODO
"""
def halfhalf_generator_testing(inds, outds, batch_size=10):
    while True:
        (in_l, in_r, out, out_l, out_r) = select_half_half(inds, outds, batch_size, True)
        yield ([in_l, in_r], out, out_l, out_r)