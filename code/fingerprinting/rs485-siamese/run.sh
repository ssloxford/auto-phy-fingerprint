#CPU version
#docker run -dit --volume="/home/sdr/auto-phy-fingerprint-mountdir:/data/mlsdr" --name=autophyfp-fingerprint-rs485 autophyfp-fingerprint-rs485:latest

#GPU version
docker run -dit --runtime=nvidia --volume="/home/sdr/auto-phy-fingerprint-mountdir:/data/mlsdr" --name=autophyfp-fingerprint-rs485 autophyfp-fingerprint-rs485:latest
