#if no USRP needed
#docker run -dit -v /home/sdr/dockerplayground:/radio -p 2225:22 -p 10090:10090 --name autophyfp-capture-adsb autophyfp-capture-adsb

#need priv and mapping dev/proc to use USRP inside container
echo "WARNING: This configuration is insecure, use in a trusted environment only! It exposes a port to the container's SSH (with known password and --privileged docker flag)."
docker run -dit --rm --privileged -v /dev:/dev -v /proc:/proc -v /home/sdr/dockerplayground:/radio -p 2225:22 --name autophyfp-capture-adsb autophyfp-capture-adsb
