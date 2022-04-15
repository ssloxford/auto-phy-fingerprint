#FROM tensorflow/tensorflow:latest		#runs into .pyc mismatch on start -- maybe need to build model against newer version?
FROM tensorflow/tensorflow:2.6.0
#FROM tensorflow/tensorflow:latest-gpu

# avoid questions when installing stuff in apt-get
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get -y update
#RUN apt-get -y install python-opencv python3-tk
RUN apt-get -y install git wget nano
#RUN apt-get -y install ffmpeg
#RUN apt-get -y install v4l-utils

RUN pip3 install numpy
#RUN pip3 install opencv-python
#RUN pip3 install opencv-contrib-python
#RUN pip3 install pyyaml
#RUN pip3 install jupyter
#RUN pip3 install jupyterlab
#RUN pip3 install imutils
#RUN pip3 install Cython
#RUN pip3 install contextlib2
#RUN pip3 install pillow
#RUN pip3 install lxml
RUN pip3 install matplotlib
#RUN pip3 install pycocotools
#RUN pip3 install scikit-image
#RUN pip3 install scikit-video
#RUN pip3 install scikit-learn
RUN pip3 install pandas keras h5py pyModeS zmq sqlalchemy

WORKDIR /root
COPY siamese.py /root/siamese.py
COPY fingerprinter.py /root/fingerprinter.py
COPY models /root/models
RUN ln -s /root/models/siamese-hisamp-94percent.h5 /root/models/siamese-hisamp.h5
