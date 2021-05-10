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

import json
import zmq

class BurstStreamer(gr.sync_block):
	"""
	docstring for block BurstStreamer
	"""
	def __init__(self, bind_addr):
		gr.sync_block.__init__(self, name="BurstStreamer", in_sig=[numpy.complex64, ], out_sig=None)

		self.trigger_tag = "burst"
		self.writing = False
		self.noprogresscounter = 0
		
		self.context = zmq.Context()
		self.socket = self.context.socket(zmq.PUB)
		self.socket.setsockopt(zmq.SNDHWM, 1024)	#1024 messages ~= 32MiB if burst is 4096 complex samples long
		self.socket.bind(bind_addr)
	
#	#TODO: this is just guestimating the forecast (and will miss the last samples of a file) -- need to replace this whole class
#	def forecast(self, noutput_items, ninput_items_required):
#		#if self.writing:
#		#	ninput_items_required[0] = 4000
#		#else:
#		#	ninput_items_required = noutput_items
#		ninput_items_required[0] = 4000
	
	def work(self, input_items, output_items):
		in0 = input_items[0]

		#debug and hack around the buffer overfill issue
		#TODO: (currently handled by bigger output buffer from upstream)
		#print((len(in0), self.writing))
		#if len(in0) > 8000:						#longer than we ever expect for the 20msps ADS-B case
		#	print("Avoiding buffer overfill issue")
		#	self.writing = False
		#	return len(in0)
		if self.noprogresscounter > 10000:				#probably not a block issue at this point (could get this length of run from concurrency, but hopefully unlikely)
			print("Making no progress, discarding current write")
			self.writing = False
			self.noprogresscounter = 0
			return len(in0)
		
		#get the tags
		total_read = self.nitems_read(0)
		tags = self.get_tags_in_window(0, 0, len(input_items[0]))

		for tag in tags:
			offset, key, val = tag.offset, pmt.to_python(tag.key), pmt.to_python(tag.value)
			rel_offset = offset - total_read
			#print("\t"+str((offset, rel_offset, key, val)))
			if key != "burst":
				continue										#nothing with these
			elif key == "burst" and val == True:
				if rel_offset > 0:
					#print("realigning")
					self.noprogresscounter = 0
					return rel_offset								#align to the start tag
				self.writing = True
			elif key == "burst" and val == False:
				if self.writing:
					##print("writing: {} {}".format(0, rel_offset))
					#meta = json.dumps({"start": total_read, "end": tag.offset})
					##self.bfw.write(in0[0:rel_offset].tobytes(), meta)				#end of the burst, trigger write from start of buffer to here
					#data = in0[0:rel_offset].tobytes()
					#msg = meta.encode("utf-8") + b"\x00" + data
					#self.socket.send(msg)
					
					topic = b"ADS-B"
					meta = json.dumps({"start": total_read, "end": tag.offset, "source": "gr-streamer"}).encode("utf-8")
					data = in0[0:rel_offset].tobytes()
					self.socket.send_multipart([topic, meta, data])
					
					self.writing = False
					return rel_offset
				else:
					self.writing = False								#shouldn't be in this situation, silently drop
			else:
				raise ValueError("Bad burst tag")

		#if not writing then consume everything, otherwise wait until the end tag comes into the buffer as well				#TODO: potential for no progress -- maybe add a max size cutoff or switch to continuation writing
		if not self.writing:
			self.noprogresscounter = 0
			return len(in0)
		else:
			self.noprogresscounter += 1
			return 0

