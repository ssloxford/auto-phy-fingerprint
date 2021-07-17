# Block mode capture, intended for use in collecting RS-485 serial signals using a Picoscope 5000-series device
# Developed by Richard Baker (2021), adapting an example:
# 	Adapted from PS5000A Block Mode Example by Pico Technology Ltd. (Copyright 2018)
# 	Example code: https://github.com/picotech/picosdk-python-wrappers/blob/master/ps5000aExamples/ps5000aBlockExample.py
#	License: https://github.com/picotech/picosdk-python-wrappers/blob/master/LICENSE.md
# Licensing for additional code, beyond the Pico Technology example is covered by the license terms of the auto-phy-fingerprint project


import ctypes
import numpy as np
from picosdk.ps5000a import ps5000a as ps
from picosdk.functions import adc2mV, assert_pico_ok, mV2adc


class PicoScope5000:
	def __init__(self):
		self.chandle = ctypes.c_int16()
		self.status = {}
		
		self.resolution = ps.PS5000A_DEVICE_RESOLUTION["PS5000A_DR_12BIT"]
		self.maxADC = ctypes.c_int16()
		
		self.channela = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
		self.channela_coupling_type = ps.PS5000A_COUPLING["PS5000A_DC"]
		self.channela_range = ps.PS5000A_RANGE["PS5000A_5V"]
		
		self.channelb = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_B"]
		self.channelb_coupling_type = ps.PS5000A_COUPLING["PS5000A_DC"]
		self.channelb_range = ps.PS5000A_RANGE["PS5000A_5V"]
		
		self.bufferAMax = None
		self.bufferAMin = None
		self.bufferBMax = None
		self.bufferBMin = None
		
		self.preTriggerSamples = 0
		self.postTriggerSamples = 0
		self.totalSamples = 0
		self.timebase = 0
		self.timeIntervalns = None
		
		self.initScope()
		self.initChannelA()
		self.initChannelB()
		self.setTrigger(self.channelb, 2400, 0, 5000)
		self.setCaptureSize(50, 24950)
		self.setTimebase(8)
		#self.runBlockCapture()
		
		
	def initScope(self):
		self.status["openunit"] = ps.ps5000aOpenUnit(ctypes.byref(self.chandle), None, self.resolution)		#sets the chandle
		
		try:
			assert_pico_ok(self.status["openunit"])
		except: # PicoNotOkError:

			powerStatus = self.status["openunit"]

			if powerStatus == 286:
				self.status["changePowerSource"] = ps.ps5000aChangePowerSource(self.chandle, powerStatus)
			elif powerStatus == 282:
				self.status["changePowerSource"] = ps.ps5000aChangePowerSource(self.chandle, powerStatus)
			else:
				raise

			assert_pico_ok(self.status["changePowerSource"])
			
		#find out the ADC range for this resolution
		self.status["maximumValue"] = ps.ps5000aMaximumValue(self.chandle, ctypes.byref(self.maxADC))
		assert_pico_ok(self.status["maximumValue"])
		
	def initChannelA(self):
		self.status["setChA"] = ps.ps5000aSetChannel(self.chandle, self.channela, 1, self.channela_coupling_type, self.channela_range, 0)
		assert_pico_ok(self.status["setChA"])

	def initChannelB(self):
		self.status["setChB"] = ps.ps5000aSetChannel(self.chandle, self.channelb, 1, self.channelb_coupling_type, self.channelb_range, 0)
		assert_pico_ok(self.status["setChB"])
		
	def setTrigger(self, source, thresholdmv, delay, timeout = 10000):
		thresh = int(mV2adc(thresholdmv, self.channela_range, self.maxADC))
		enabled = 1			#obvs...
		direction = 2		#PS5000A_RISING
		self.status["trigger"] = ps.ps5000aSetSimpleTrigger(self.chandle, enabled, source, thresh, direction, delay, timeout)
		assert_pico_ok(self.status["trigger"])
	
	def setCaptureSize(self, preTrigSamps, postTrigSamps):
		self.preTriggerSamples = preTrigSamps
		self.postTriggerSamples = postTrigSamps
		self.totalSamples = self.preTriggerSamples + self.postTriggerSamples
		
	def setTimebase(self, tb):
		self.timebase = tb					#value * 10 ns (i.e. 8 == 80ns), depends on resolution
		self.timeIntervalns = ctypes.c_float()
		returnedMaxSamples = ctypes.c_int32()				#TODO: maybe need to keep this and check it later somewhere?
		segment_index = 0							#???
		self.status["getTimebase2"] = ps.ps5000aGetTimebase2(self.chandle, self.timebase, self.totalSamples, ctypes.byref(self.timeIntervalns), ctypes.byref(returnedMaxSamples), segment_index)
		assert_pico_ok(self.status["getTimebase2"])
		
	def runBlockCapture(self):
		# Create buffers ready for assigning pointers for data collection
		self.bufferAMax = (ctypes.c_int16 * self.totalSamples)()
		self.bufferAMin = (ctypes.c_int16 * self.totalSamples)() # used for downsampling which isn't in the scope of this example
		self.bufferBMax = (ctypes.c_int16 * self.totalSamples)()
		self.bufferBMin = (ctypes.c_int16 * self.totalSamples)() # used for downsampling which isn't in the scope of this example
		
		time_indisposed_ms = None
		segment_index = 0
		lpReady = None				#might be callback function, if not using polling?
		pParameter = None
		self.status["runBlock"] = ps.ps5000aRunBlock(self.chandle, self.preTriggerSamples, self.postTriggerSamples, self.timebase, time_indisposed_ms, segment_index, lpReady, pParameter)
		assert_pico_ok(self.status["runBlock"])
		
	def awaitCaptureComplete(self):
		ready = ctypes.c_int16(0)
		check = ctypes.c_int16(0)
		while ready.value == check.value:
			self.status["isReady"] = ps.ps5000aIsReady(self.chandle, ctypes.byref(ready))
			
	def retrieveCaptureData(self, channels):
		segment_index = 0
		ratio_move = 0		#PS5000A_RATIO_MODE_NONE
		if self.channela in channels:
			self.status["setDataBuffersA"] = ps.ps5000aSetDataBuffers(self.chandle, self.channela, ctypes.byref(self.bufferAMax), ctypes.byref(self.bufferAMin), self.totalSamples, segment_index, ratio_move)
			assert_pico_ok(self.status["setDataBuffersA"])
		if self.channelb in channels:
			self.status["setDataBuffersB"] = ps.ps5000aSetDataBuffers(self.chandle, self.channelb, ctypes.byref(self.bufferBMax), ctypes.byref(self.bufferBMin), self.totalSamples, segment_index, ratio_move)
			assert_pico_ok(self.status["setDataBuffersB"])
		if len(channels) < 1 or (self.channela not in channels and self.channelb not in channels):
			raise ValueError("Missing or unrecognised channel(s) requested")
			
		# create overflow loaction
		overflow = ctypes.c_int16()
		# create converted type maxSamples
		cmaxSamples = ctypes.c_int32(self.totalSamples)
		
		# Retried data from scope to buffers assigned above
		start_index = 0
		downsample_ratio = 0
		downsample_mode = 0 	#PS5000A_RATIO_MODE_NONE
		segment_index = 0
		self.status["getValues"] = ps.ps5000aGetValues(self.chandle, start_index, ctypes.byref(cmaxSamples), downsample_ratio, downsample_mode, segment_index, ctypes.byref(overflow))
		assert_pico_ok(self.status["getValues"])

		# convert ADC counts data to mV
		adc2mVMaxChA, adc2mVMaxChB = None, None
		if self.channela in channels:
			adc2mVMaxChA =  adc2mV(self.bufferAMax, self.channela_range, self.maxADC)
		if self.channelb in channels:
			adc2mVMaxChB =  adc2mV(self.bufferBMax, self.channelb_range, self.maxADC)
		
		return [adc2mVMaxChA, adc2mVMaxChB]
		
	def getTimescale(self):
		timescale = np.linspace(0, (self.totalSamples.value) * self.timeIntervalns.value, self.totalSamples.value)
		return timescale
	
	def stopScope(self):
		self.status["stop"] = ps.ps5000aStop(self.chandle)
		assert_pico_ok(self.status["stop"])
	
	def close(self):
		# Close unit Disconnect the scope
		self.status["close"] = ps.ps5000aCloseUnit(self.chandle)
		assert_pico_ok(self.status["close"])
		
	def getStatus(self):
		return self.status