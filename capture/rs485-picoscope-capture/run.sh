#mounts for /dev and /proc required for USB access to scope and serial devices, /run/udev required to fully populate the udev rules so the container recognises the serial devices
docker run -it --rm --privileged -v /dev:/dev -v /proc:/proc -v /run/udev:/run/udev:ro -v /home/sdr/auto-phy-fingerprint-mountdir:/radio --name autophyfp-capture-rs485 autophyfp-capture-rs485 "python3 capture_rs485_picoscope.py $1 $2"

