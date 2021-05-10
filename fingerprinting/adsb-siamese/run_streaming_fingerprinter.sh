#CPU version
#docker run -dit --volume="/home/sdr/auto-phy-fingerprint-mountdir:/data/mlsdr" --name=autophyfp-fingerprint-adsb autophyfp-fingerprint-adsb:latest python3 fingerprinter.py $1 $2 $3

#GPU version
docker run -dit --runtime=nvidia --volume="/home/sdr/auto-phy-fingerprint-mountdir:/data/mlsdr" --name=autophyfp-fingerprint-adsb autophyfp-fingerprint-adsb:latest python3 fingerprinter.py $1 $2 $3
