FROM python:3

#avoid questions when installing stuff in apt-get
ARG DEBIAN_FRONTEND=noninteractive

#install swig
RUN apt-get update && apt-get install -y swig

#install pip dependencies
RUN pip3 install numpy matplotlib pyModeS h5py zmq

#copy in the codebase
WORKDIR /
RUN mkdir /code
COPY code /code

#RUN find / -name arrayobject.h

#set up pylibmodes (linking to install numpy headers first)
RUN ln -s "/usr/local/lib/python3.9/site-packages/numpy/core/include/numpy" "/usr/local/include/python3.9/numpy"
RUN cd /code/demod/adsb-libmodes-demod/code/libmodes && python3 setup.py install

#set up pySDRBurstfile
RUN cd /code/demod/adsb-libmodes-demod/code/pySDRBurstfile && python3 setup.py install

#CMD ["python3", "bursts_to_libmodes.py"]
ENTRYPOINT ["/bin/bash", "-c"]






