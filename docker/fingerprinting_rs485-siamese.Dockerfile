#FROM tensorflow/tensorflow:latest		#runs into .pyc mismatch on start -- maybe need to build model against newer version?
FROM tensorflow/tensorflow:2.6.0
#FROM tensorflow/tensorflow:latest-gpu

# avoid questions when installing stuff in apt-get
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get -y update
RUN apt-get -y install git wget nano

RUN pip3 install numpy
RUN pip3 install matplotlib
RUN pip3 install pandas keras h5py zmq sqlalchemy

WORKDIR /
RUN mkdir /code
COPY code /code

