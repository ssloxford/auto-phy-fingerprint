docker run -it --rm -v /home/sdr/auto-phy-fingerprint-mountdir:/radio --name autophyfp-demod-adsb-file autophyfp-demod-adsb "python3 bursts_to_libmodes.py /radio/$1"
