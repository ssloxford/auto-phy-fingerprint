docker run -it --rm -v /home/sdr/auto-phy-fingerprint-mountdir:/radio --name autophyfp-demod-adsb-streamer autophyfp-demod-adsb "python3 stream_bursts_via_libmodes.py $1 $2"
