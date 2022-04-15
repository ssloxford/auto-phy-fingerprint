docker run -it --rm -v /home/sdr/auto-phy-fingerprint-mountdir:/radio --name autophyfp-demod-rs485-streamer autophyfp-demod-rs485 "python3 decode.py $1 $2"
