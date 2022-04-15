import glob
import threading
import serial
import time

BAUD_RATE = 115200	#9600, 19200, 38400, 57600, 115200, 128000, 256000 ... 9216000

class Monitor:
	def __init__(self, ttypath):
		self.ttypath = ttypath
		#self.stop = False
		self.t = None
	
	def monitor(self):
		self.t = threading.Thread(target=self._watcher, args=[])
		self.t.start()
		
	def _watcher(self):
		#print(f"Watching {self.ttypath}")
		ser = serial.Serial(self.ttypath, BAUD_RATE, timeout=5)
		#while not self.stop:
		
		try:
			line = ser.readline().decode()
			if len(line) == 0:
				line = "[TIMEOUT]\n"
		except:
			line = "[FAILURE]\n"
		print(f"\t{self.ttypath} : {line}", end="")

			
ttypaths = sorted(glob.glob("/dev/ttyUSB*"))
print(f"Found {len(ttypaths)} devices")
print(f"Configuring for {BAUD_RATE} baud")

for tp in ttypaths:
	with open(tp, "wb") as t:
		print(f"Testing from {tp}")
		
		monitors = []
		for tpl in ttypaths:
			if tpl != tp:
				m = Monitor(tpl)
				monitors.append(m)
				m.monitor()
		
		time.sleep(1.0)
		#t.write(f"{tp}\n".encode("utf-8"))
		ser = serial.Serial(tp, BAUD_RATE, timeout=5)
		ser.write(f"{tp}\n".encode("utf-8"))
		
		for tp2 in ttypaths:
			m.t.join()
		print()
		
time.sleep(3.0)
print("Stopping monitors")
for m in monitors:
	m.stop = True
#for tp in ttypaths:
#	with open(tp, "wb") as t:
#		t.write("\n")