import glob
import os
import hashlib
import serial
import threading
import time


#these are md5 hashes of some device properties, along with an extra identifier (number from the label) but only if the device id isn't unique
UNIQUE_TX_DEVICES = {
	"cb3e26ee7effb979268abc35cac8b180": "Identical, bare-board, black 'FTDI_FT232R_USB_UART_A50285BI' devices with cables. Marked '1'.", 
	"f8bde97d87baad9bff11969eceab4e80": "Identical, bare-board, black 'FTDI_FT232R_USB_UART_A50285BI' devices with cables. Marked '2'.",
	"257eb55c4ce227e861a04fb0758d7cf9": "Big, translucent, blue device. Marked '3'.",
	"3793fa4f2676024c81c9feb01830d39a": "Small, black, two-port dongle. Marked '4'.",
}
NON_UNIQUE_TX_DEVICES = {
	"d2f044c0746e0473cea24aedb3fa19d6": "Either of the identical, bare-board, black 'FTDI_FT232R_USB_UART_A50285BI' devices with cables.",
}
BAUD_RATE = 9600

class TTYIdentifier:
	def identify(self):
		print("Identifying ttyUSB devices")
		self.devices = sorted(glob.glob("/sys/bus/usb-serial/devices/ttyUSB*"))
		self.identities = dict()
		
		for device in self.devices:
			#get the device details and hash them to get a device id
			record = self.deviceRecord(device)
			rawdeviceid = self.hashRecord(record)
			ttyname = record["ttyname"]
			ttypath = f"/dev/{ttyname}"
			
			#check if it is already uniquely identified
			if rawdeviceid in UNIQUE_TX_DEVICES:
				print(f"Unique device found ({ttyname})")
				deviceid = rawdeviceid
				identity = {
					"ttyname": ttyname,
					"ttypath": ttypath,
					"devicepath": device,
					"rawdeviceid": rawdeviceid,
					"extraid": None,
					"deviceid": deviceid,
					"desc": UNIQUE_TX_DEVICES[rawdeviceid]
				}
				self.identities[ttyname] = identity
			elif rawdeviceid in NON_UNIQUE_TX_DEVICES:
				#must deconflict by testing each and asking user to input
				print(f"Non-unique device found ({ttyname}), commencing user deconfliction")
				with serial.Serial(f"/dev/{ttyname}", BAUD_RATE) as ser:
					extra_id = DeviceTester().test(ttyname, ser)
					record["extra"] = extra_id
					deviceid = self.hashRecord(record)
				identity = {
					"ttyname": ttyname,
					"ttypath": ttypath,
					"devicepath": device,
					"rawdeviceid": rawdeviceid,
					"extraid": extra_id,
					"deviceid": deviceid,
					"desc": UNIQUE_TX_DEVICES[deviceid]
				}
				self.identities[ttyname] = identity
			else:
				#unrecognised device, either it is unknown or it is non-unique
				raise ValueError(f"Unknown device {rawdeviceid}: {record}")
				
		return self.identities
				
	def deviceRecord(self, ttypath):
		ttyname = os.path.basename(ttypath)

		stream = os.popen(f"udevadm info {ttypath}")
		output = stream.read().strip()

		#sanity check
		if "SUBSYSTEM=usb-serial" not in output:
			raise ValueError(f"Device {ttypath} does not appear to be USB serial device")		#TODO: may not work right for GPIO ones

		pathtext = output.split("\n")[0][3:]
		devpath = "/".join(["", "sys"] + pathtext.split("/")[1:-2] + [""])
		#print(devpath)

		#print("Calling: " + f"udevadm info {devpath}")
		stream = os.popen(f"udevadm info {devpath}")
		info = dict()
		#output = stream.read().strip()

		for line in stream.readlines():
			if line[:3] == "E: ":
				line = line[3:].strip()
				elems = line.split("=")
				key = elems[0]
				val = "".join(elems[1:])
				info[key] = val

		record = {
			"ttyname" : ttyname,
			"ttypath": ttypath, 
			"id_model": info["ID_MODEL"],
			"id_model_id": info["ID_MODEL_ID"],
			"id_model_db": info["ID_MODEL_FROM_DATABASE"],
			"id_revision": info["ID_REVISION"],
			"id_serial": info["ID_SERIAL"],
			"id_vendor": info["ID_VENDOR"],
			"id_vendor_id": info["ID_VENDOR_ID"],
			"id_vendor_db": info["ID_VENDOR_FROM_DATABASE"],
			"usec_init": info["USEC_INITIALIZED"],
		}

		return record

	def hashRecord(self, record):
		h = hashlib.md5()
		h.update(record["id_vendor_db"].encode("utf-8"))
		h.update(record["id_model_db"].encode("utf-8"))
		h.update(record["id_serial"].encode("utf-8"))
		if "extra" in record:
			h.update(record["extra"].encode("utf-8"))
		return h.hexdigest()

class DeviceTester:
	def test(self, ttyname, ser):
		self.finish = False
		testthread = threading.Thread(target=self._testDevice, args=([ser]))
		testthread.start()
		extra = input(f"\tTesting device {ttyname}, enter id from label: ")
		self.finish = True
		testthread.join()
		return extra

	def _testDevice(self, ser):
		while not self.finish:
			ser.write(b"test")
			time.sleep(0.5)
	
#class DeviceDeconflicter:
#	#def __init__(self):
#	#	self.finish = False
#	
#	def deconflict(self, ttyname, ser):
#		self.finish = False
#		testthread = threading.Thread(target=self.testDevice, args=([ser]))
#		testthread.start()
#		extra = input(f"\tTesting device {ttyname}, enter id: ")
#		self.finish = True
#		testthread.join()
#		return extra
#	
#	def check(self, ttyname, ser):
#		self.finish = False
#		testthread = threading.Thread(target=self.testDevice, args=([ser]))
#		testthread.start()
#		check = input(f"\tTesting device {ttyname}, press enter to confirm or enter any text to abort: ")
#		self.finish = True
#		testthread.join()
#		return check
#	
#	def testDevice(self, ser):
#		while not self.finish:
#			ser.write(b"test")
#			time.sleep(0.5)