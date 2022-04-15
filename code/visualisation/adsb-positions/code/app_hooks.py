import argparse
from threading import Thread

import streamsink

def on_server_loaded(server_context):
	ap = argparse.ArgumentParser(description="Visualise a stream of ADS-B positions on a map.")
	ap.add_argument("--recv_connect_addr", type=str, help="Connect address of upstream ZMQ PUB")
	ap.add_argument("--topic", type=str, help="Topic to subscribe to")
	args, _ = ap.parse_known_args()
	
	if args.recv_connect_addr is None or args.topic is None:
		print("Missing required arguments --recv_connect_addr and/or --topic")
		exit(1)
	
	print("Triggered server hook")
	t = Thread(target=streamsink.streamFromZMQ, args=(args.recv_connect_addr, args.topic))
	t.setDaemon(True)
	t.start()

