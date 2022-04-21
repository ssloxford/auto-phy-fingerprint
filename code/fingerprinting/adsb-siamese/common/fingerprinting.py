import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '1' #0 = all messages are logged (default behavior), 1 = INFO messages are not printed, 2 = INFO and WARNING messages are not printed, 3 = INFO, WARNING, and ERROR messages are not printed
from tensorflow.keras import models, layers
import tensorflow as tf

import numpy as np

import common.constants as constants

def reshape_single_row(single_row):
	return single_row.reshape(1, single_row.shape[0], single_row.shape[1])

class FirstMsgFingerprinter:
	def __init__(self, model, unused):
		self.model = model
		self.known_aircraft = dict()

	def fingerprint_msg(self, msg, claimedicao):
		# if we have no previous fingerprint, then just save
		if claimedicao not in self.known_aircraft:
			self.known_aircraft[claimedicao] = msg
			return None
		else:  # otherwise check the fingerprint
			msg_shaped = reshape_single_row(msg)
			ref_shaped = reshape_single_row(self.known_aircraft[claimedicao])
			compare_result = self.model.predict([msg_shaped, ref_shaped])
			match = compare_result.flatten()[0] > 0.5
			return match

class BestOfNFingerprinter:
	def __init__(self, model, fp_n):
		self.model = model
		self.known_aircraft = dict()
		self.fp_dict = {}  				# Temporary message storage until fingerprint is computed
		self.fp_n = fp_n  			# Number of messages considered for fingerprint

	def fingerprint_msg(self, msg, claimedicao):
		# if we have no previous fingerprint, then just save
		if claimedicao not in self.known_aircraft:
			save_fp = False
			fp = None

			if self.fp_n == 1:
				fp = msg
				save_fp = True
			elif claimedicao not in self.fp_dict:
				self.fp_dict[claimedicao] = [msg]
			elif len(self.fp_dict[claimedicao]) < self.fp_n - 1:
				self.fp_dict[claimedicao].append(msg)
			else:
				self.fp_dict[claimedicao].append(msg)
				fp_list = []
				for i, m in enumerate(self.fp_dict[claimedicao]):
					fp_result = 0
					for j, m_ in enumerate(self.fp_dict[claimedicao]):
						if i == j:
							continue
						#fp_result += self.model.predict([m.reshape(1, waveform_len, feature_count), m_.reshape(1, waveform_len, feature_count)]).flatten()[0]
						fp_result += self.model.predict([reshape_single_row(m), reshape_single_row(m_)]).flatten()[0]
					fp_list.append(fp_result)
				max_ = max(fp_list)
				fp = self.fp_dict[claimedicao][fp_list.index(max_)]
				del self.fp_dict[claimedicao]
				save_fp = True

			if save_fp:
				assert fp is not None
				self.known_aircraft[claimedicao] = fp

			return None
		else:  # otherwise check the fingerprint
			msg_shaped = reshape_single_row(msg)
			ref_shaped = reshape_single_row(self.known_aircraft[claimedicao])
			compare_result = self.model.predict([msg_shaped, ref_shaped])
			match = compare_result.flatten()[0] > 0.5
			return match


class CentroidFingerprinter:
	def __init__(self, model, fp_n):
		self.model = model
		self.known_aircraft = dict()

		self.fp_dict = {}  # Temporary message storage until fingerprint is computed
		self.fp_n = fp_n  # Number of messages considered for fingerprint

		# Extract the fingerprint generating model
		fingerprint_model = models.Model(inputs=model.layers[2].input, outputs=model.layers[2].output)
		fingerprint_input = layers.Input(shape=(256,), name="fp_input")

		# Create helper model for new messages
		helper_model = models.Model(inputs=[fingerprint_model.input],
									outputs=[fingerprint_model.call(fingerprint_model.input)])

		# Pipe saved fingerprint and new message through final layers
		prediction = model.layers[4](model.layers[3]([fingerprint_input, helper_model.output]))

		# Connect the inputs with the outputs
		verification_model = models.Model(inputs=[fingerprint_input, fingerprint_model.input], outputs=prediction)

		self.fingerprint_model = fingerprint_model
		self.verification_model = verification_model

	def fingerprint_msg(self, msg, claimedicao):
		# if we have no previous fingerprint, then just save
		if claimedicao not in self.known_aircraft:
			save_fp = False
			fp = None

			if self.fp_n == 1:
				fp = self.fingerprint_model.predict([msg.reshape(1, 2400, 2)])
				save_fp = True
			elif claimedicao not in self.fp_dict:
				self.fp_dict[claimedicao] = [self.fingerprint_model.predict([msg.reshape(1, 2400, 2)])]
			elif len(self.fp_dict[claimedicao]) < self.fp_n - 1:
				self.fp_dict[claimedicao].append(self.fingerprint_model.predict([msg.reshape(1, 2400, 2)]))
			else:
				self.fp_dict[claimedicao].append(self.fingerprint_model.predict([msg.reshape(1, 2400, 2)]))
				fp = np.mean(self.fp_dict[claimedicao], axis=0)
				del self.fp_dict[claimedicao]
				save_fp = True

			if save_fp:
				assert fp is not None
				self.known_aircraft[claimedicao] = fp

			return None
		else:  # otherwise check the fingerprint
			compare_result = self.verification_model.predict([self.known_aircraft[claimedicao], reshape_single_row(msg)])
			match = compare_result.flatten()[0] > 0.5

			return match