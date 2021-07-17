FROM ubuntu:bionic

WORKDIR /code

#avoid questions when installing stuff in apt-get
ARG DEBIAN_FRONTEND=noninteractive

#install pip and basic dependencies
RUN apt-get update && apt-get install -y python3-pip wget udev git

#install pip dependencies
RUN pip3 install numpy matplotlib h5py zmq pySerial

#configure sources for picoscope libraries
RUN bash -c 'echo "deb https://labs.picotech.com/debian/ picoscope main" >/etc/apt/sources.list.d/picoscope.list'
RUN wget -O - https://labs.picotech.com/debian/dists/picoscope/Release.gpg.key | apt-key add -

#install picoscope libraries, but work around the postinstall script failure because udevadm control fails (not needed here anyway)
RUN apt-get update && apt-get install libusb-1.0-0 libpicoipp
RUN apt-get download libps5000a
RUN dpkg --unpack libps5000a*.deb
RUN sed -i "s/udevadm control/#udevadm control/g" /var/lib/dpkg/info/libps5000a.postinst
RUN dpkg --configure libps5000a
RUN apt-get install -yf

#install the picosdk python wrappers
RUN git clone https://github.com/picotech/picosdk-python-wrappers
RUN cd picosdk-python-wrappers && pip3 install .

COPY code/PicoScope5000Wrapper.py /code
COPY code/TTYIdentifier.py /code
COPY code/capture_rs485_picoscope.py /code

ENTRYPOINT ["/bin/bash", "-c"]




