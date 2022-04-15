import sys
import os
import time
import numpy as np
import zmq
import pyModeS as pms
import logging
import json
import argparse
#import h5py
from datetime import datetime

import sqlalchemy as db
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class dbVerifiedMessage(Base):
	__tablename__ = "verifiedmsgs"
	id = db.Column(db.Integer, primary_key=True)
	icao = db.Column(db.String, index=True)
	tc = db.Column(db.Integer)
	lat = db.Column(db.Float)
	lon = db.Column(db.Float)
	verif_status = db.Column(db.String)
	msguuid = db.Column(db.String)
	msg = db.Column(db.String)
	msgtime = db.Column(db.Float)
	msgtime_dt = db.Column(db.DateTime)
	savetime_coarse = db.Column(db.Float)
	savetime_coarse_dt = db.Column(db.DateTime)

###########################

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s|%(message)s', level=logging.INFO)

ap = argparse.ArgumentParser(description="Listen to a stream of verified bursts and record them in an SQLite3 file.")
ap.add_argument("recv_connect_addr", type=str, help="Connect address of upstream ZMQ PUB")
ap.add_argument("database_filename", type=str, help="Filename for SQLite3 file")
ap.add_argument("topic", type=str, help="Topic to subscribe to")
args = ap.parse_args()

logging.info(f"Creating SQLite3 file at {args.database_filename}")
engine = db.create_engine(f"sqlite:///{args.database_filename}")
connection = engine.connect()
Base.metadata.create_all(engine)

Session = db.orm.sessionmaker(bind=engine)
session = Session()

context = zmq.Context()

logging.info(f"Setting up ZMQ SUB socket connecting to {args.recv_connect_addr}")
insocket = context.socket(zmq.SUB)
#insocket.setsockopt(zmq.RCVHWM, 1024)	#1024 messages ~= 32MiB if burst is 4096 complex samples long
#insocket.setsockopt(zmq.RCVBUF, 1024*1024)		#based on default max buffer allowed in Ubuntu 20.04
insocket.connect(args.recv_connect_addr)
#insocket.setsockopt(zmq.SUBSCRIBE, b'') # subscribe to topic of all (needed or else it won't work)

insocket.subscribe(args.topic)
logging.info(f"Subscribed to topic \"{args.topic}\"")


#TODO: when I have a new enough version of libhdf5, move to swmr mode to allow copies of the file to be taken while streaming to it (and for crash protection)
#outf.swmr_mode = True

msgi = 0
while True:
	if insocket.poll(10) != 0: # check if there is a message on the socket
		(topic, meta, data) = insocket.recv_multipart()
		logging.debug(f"Received message of len {len(topic) + len(meta) + len(data)} bytes")
	else:
		time.sleep(0.05) # wait 100ms and try again
		continue

	jmeta = json.loads(meta)

	logging.debug(meta)

	msg = jmeta["decode.msg"]
	icao = msg[2:8]										#TODO: this should probably be provided by the demod, as it's so easy to get there
	tc = pms.adsb.typecode(msg)
	logging.debug(f"ADSB Typecode: {tc}")
	#RCVLAT, RCVLON = 51.753037, -1.258651				#Oxford
	RCVLAT, RCVLON = 51.0691, 0.6894					#Tenterden
	if tc is None:		#very rare occurence, but has happened in PRD occasionally, just discard
		logging.warn(f"No typecode in message: {jmeta}")
		continue
	(lat, lon) = (None, None) if tc < 9 or tc > 18 else pms.adsb.position_with_ref(msg, RCVLAT, RCVLON)

	msgtime = float(jmeta["msgtime"])
	savetime = time.time()

	#if (lat, lon) == (None, None):
	#	logging.debug("Got Lat,Lon of None,None. Skipping")
	#	continue

	vm = dbVerifiedMessage()
	vm.icao = icao
	vm.tc = tc
	vm.lat = lat
	vm.lon = lon
	vm.verif_status = jmeta["verify.status"]
	vm.msguuid = jmeta["uuid"]
	vm.msg = msg
	vm.msgtime = msgtime
	vm.msgtime_dt = datetime.fromtimestamp(msgtime)#.isoformat(sep=" ")
	vm.savetime_coarse = savetime
	vm.savetime_coarse_dt = datetime.fromtimestamp(savetime)#.isoformat(sep=" ")

	session.add(vm)
	session.commit()

	msgi += 1

	if msgi % 100 == 0:
		logging.info(f"Stored results for {msgi} messages")
