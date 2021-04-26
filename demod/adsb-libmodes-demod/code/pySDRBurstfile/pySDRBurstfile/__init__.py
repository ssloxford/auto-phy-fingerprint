import struct

magic = b"BURSTFILE"
datahead = b"BURST"

class SDRBurstFileReader:
	
	def __init__(self, filename):
		self.filename = filename
		self.filemeta = None
		
		self.f = open(filename, "rb")
		self._read_file_header()
	
	def _read_file_header(self):
		#read and check magic bytes
		buf = self.f.read(len(magic))
		if buf != magic:
			raise ValueError("Invalid magic bytes")
		
		#read metadata
		buf = self.f.read(8)
		metalen = struct.unpack("<Q", buf)[0]
		buf = self.f.read(metalen)
		self.filemeta = struct.unpack("<"+str(metalen)+"s", buf)[0].decode("utf-8")
	
	def read(self):
		while True:
			#read "BURST"
			buf = self.f.read(len(datahead))
			if len(buf) != len(datahead):
				break		#probably run out of data
			if buf != datahead:
				raise ValueError("Invalid data header")

			#read metadata
			buf = self.f.read(8)
			metalen = struct.unpack("<Q", buf)[0]
			buf = self.f.read(metalen)
			datameta = struct.unpack("<"+str(metalen)+"s", buf)[0].decode("utf-8")

			#read data
			buf = self.f.read(8)
			datalen = struct.unpack("<Q", buf)[0]
			data = self.f.read(datalen)

			yield (data, datameta)
	
	def close(self):
		self.f.close()

class SDRBurstFileWriter:
	
	def __init__(self, filename, filemeta):
		self.filename = filename
		self.filemeta = filemeta
		
		self.f = open(filename, "wb")
		self._write_file_header(filemeta)
	
	def _write_file_header(self, filemeta):
		filemetalen = len(filemeta)
		fileheader = struct.pack("<" + str(len(magic)) + "sQ"+str(filemetalen)+"s", magic, filemetalen, filemeta)

		self.f.write(fileheader)

	def write(self, databytes, datameta):
		header = struct.pack("<" + str(len(datahead)) + "s", datahead)
		meta = struct.pack("<Q"+str(len(datameta))+"s", len(datameta), datameta)
		dlen = struct.pack("<Q", len(databytes))
		self.f.write(header + meta + dlen + databytes)

	def close(self):
		self.f.close()
