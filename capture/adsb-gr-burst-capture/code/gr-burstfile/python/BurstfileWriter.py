#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2021 Richard Baker.
#
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#


import numpy
from gnuradio import gr
import pmt

from pySDRBurstfile import *
import json

class BurstfileWriter(gr.sync_block):
	"""
	docstring for block BurstfileWriter
	"""
	def __init__(self, filename):
		gr.sync_block.__init__(self, name="BurstfileWriter", in_sig=[numpy.complex64, ], out_sig=None)

		self.trigger_tag = "burst"
		filemeta = "".encode("utf-8")
		self.bfw = SDRBurstFileWriter(filename, filemeta)

		#self.curburst = None
		#self.writing = False
		#self.writefrom = None
		#self.writeto = None
		#self.was_writing = False
		self.writing = False

	#TODO: this is just guestimating the forecast (and will miss the last samples of a file) -- need to replace this whole class
	def forecast(self, noutput_items, ninput_items_required):
		if self.writing:
			ninput_items_required[0] = 4000
		else:
			ninput_items_required = noutput_items
		
	def work(self, input_items, output_items):
		in0 = input_items[0]

		#print(len(in0))

		#get the tags
		total_read = self.nitems_read(0)
#		bursts = []
		tags = self.get_tags_in_window(0, 0, len(input_items[0]))


#		print("Tags:")
#		for tag in tags:
#			offset, key, val = tag.offset, pmt.to_python(tag.key), pmt.to_python(tag.value)
#			rel_offset = offset - total_read
#			print("\t"+str((offset, rel_offset, key, val)))
#
#		return len(in0)




#		#align to first burst tag
#		consumed = 0
#		for tag in tags:
#			if key != "burst":
#				consumed = tag.offset - total_read
#			else:
#				break
#		if consumed > 0:
#			return consumed



		for tag in tags:
			offset, key, val = tag.offset, pmt.to_python(tag.key), pmt.to_python(tag.value)
			rel_offset = offset - total_read
			#print("\t"+str((offset, rel_offset, key, val)))
			if key != "burst":
				continue										#nothing with these
			elif key == "burst" and val == True:
				if rel_offset > 0:
					#print("realigning")
					return rel_offset								#align to the start tag
				self.writing = True
			elif key == "burst" and val == False:
				if self.writing:
					#print("writing: {} {}".format(0, rel_offset))
					datameta = json.dumps({"start": total_read, "end": tag.offset}).encode("utf-8")
					self.bfw.write(in0[0:rel_offset].tobytes(), datameta)				#end of the burst, trigger write from start of buffer to here
					self.writing = False
					return rel_offset
				else:
					self.writing = False								#shouldn't be in this situation, silently drop
			else:
				raise ValueError("Bad burst tag")



#		#track the writing regions in the window
#		regions = []		#(start, end, writing?)
#		region_write = self.was_writing
#		region_start = 0
#		for tag in tags:
#			offset, key, val = tag.offset, pmt.to_python(tag.key), pmt.to_python(tag.value)
#			rel_offset = offset - total_read
#			print("\t"+str((offset, rel_offset, key, val)))
#			if key != "burst":
#				continue										#nothing with these
#			elif key == "burst" and val == True:
#				regions.append((region_start, rel_offset, region_write))				#write the region for everything before this tag
#				region_write = True
#				region_start = rel_offset
#			elif key == "burst" and val == False:
#				regions.append((region_start, rel_offset, region_write))
#				region_write = False
#				region_start = rel_offset
#			else:
#				raise ValueError("Bad burst tag")

		#last region based on the running variables
		#regions.append((region_start, None, region_write))

#		print(regions)

		#write as necessary
#		if self.writefrom is not None

#		#if there are bursts, save them
#		#for (start, end) in bursts:
#		while len(bursts) > 0:
#			(start, end) = bursts.pop(0)
#			#print("Saving burst {} - {}".format(start, end))
#			datameta = json.dumps({"start": start, "end": end}).encode("utf-8")
#			self.bfw.write(in0[start:end].tobytes(), datameta)
#
#		#if there is a remaining start, keep those samples for next time
#		if self.curburst is not None:
#			return self.curburst - 1   #presumably minus 1 as curburst is an index, and this is a count

#		for tag in tags:
#			key = pmt.to_python(tag.key) # convert from PMT to python string
#			value = pmt.to_python(tag.value) # Note that the type(value) can be several things, it depends what PMT type it was
#			print("{} : {} ({})".format(key, value, type(value)))
#
#		exit()

		#return len(input_items[0])

		#if not writing then consume everything, otherwise wait until the end tag comes into the buffer as well				#TODO: potential for no progress -- maybe add a max size cutoff or switch to continuation writing
		if not self.writing:
			return len(in0)
		else:
			return 0

