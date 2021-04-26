import sys
import os
import glob

import numpy as np
import matplotlib.pyplot as plt

import h5py

def checkExpectedDatasets(h5file, expected):
	a = set(h5file.keys())
	b = set(expected)
	
	return a == b

def addDatasetShapes(a, b):
	if len(a) != len(b):
		print(len(a))
		print(len(b))
		raise ValueError("Mismatched shapes")
	res = [a[0] + b[0]]
	for i in range(1, len(a)):
		if a[i] != b[i]:
			raise ValueError("Shapes differ in later dimensions")
		else:
			res.append(a[i])
	return tuple(res)

##############################

globstring = "/data/mlsdr/adsb_2*-df17.hdf5"
outputfile = "/data/mlsdr/combined_adsb_20000000.0-df17.hdf5"

print(f"Globbing for: \"{globstring}\"")
filenames = glob.glob(globstring)		#only the 4rc ones
print(f"Found {len(filenames)} files")

#count all the sizes
inds_total_shape = (0, 2400, 2)
outds_total_shape = (0, 1)
for filename in filenames:
	h5f = h5py.File(filename, "r")
	if not checkExpectedDatasets(h5f, ["inds", "outds"]):
		raise ValueError("Unexpected datasets found")
	
	inds_total_shape = addDatasetShapes(inds_total_shape, h5f["inds"].shape)
	outds_total_shape = addDatasetShapes(outds_total_shape, h5f["outds"].shape)
	
	h5f.close()

print(f"Total inds:  {inds_total_shape}")
print(f"Total outds: {outds_total_shape}")

#create the new file and consolidate into it
h5out = h5py.File(outputfile, "w")
h5out.create_dataset("inds", inds_total_shape, dtype=np.float32)
h5out.create_dataset("outds", outds_total_shape, dtype="S6")
h5outi = 0
for filename in filenames:
	h5f = h5py.File(filename, "r")
	numthisfile = h5f["inds"].shape[0]
	(copystart, copyend) = (h5outi, h5outi + numthisfile)
	h5out["inds"][copystart:copyend,:,:] = h5f["inds"]
	h5out["outds"][copystart:copyend,:] = h5f["outds"]
	h5outi += numthisfile
	h5f.close()
h5out.close()

