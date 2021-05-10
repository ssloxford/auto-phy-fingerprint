FROM python:3

WORKDIR /code

#avoid questions when installing stuff in apt-get
ARG DEBIAN_FRONTEND=noninteractive

#install swig
RUN apt-get update && apt-get install -y swig

#install pip dependencies
RUN pip3 install numpy matplotlib pyModeS h5py zmq

#RUN find / -name arrayobject.h

#set up pylibmodes (linking to install numpy headers first)
RUN ln -s "/usr/local/lib/python3.9/site-packages/numpy/core/include/numpy" "/usr/local/include/python3.9/numpy"
COPY code/libmodes code/libmodes
RUN cd code/libmodes && python3 setup.py install

#set up pySDRBurstfile
COPY code/pySDRBurstfile code/pySDRBurstfile
RUN cd code/pySDRBurstfile && python3 setup.py install

COPY code/bursts_to_libmodes.py /code
COPY code/stream_bursts_via_libmodes.py /code

#CMD ["python3", "bursts_to_libmodes.py"]
ENTRYPOINT ["/bin/bash", "-c"]






