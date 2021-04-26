#FROM tensorflow/tensorflow:2.1.0-py3
FROM tensorflow/tensorflow:latest-gpu

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
RUN pip3 install pandas
RUN pip3 install keras
RUN pip3 install h5py

#WORKDIR /home
#COPY pyMLSDR /home/pyMLSDR

# use Github deployment key (ro access to pyMLSDR private repo)
#COPY github-pymlsdr-deploy-ro /root/.ssh/id_rsa
#COPY github-pymlsdr-deploy-ro.pub /root/.ssh/id_rsa.pub
#RUN ssh-keyscan github.com >> ~/.ssh/known_hosts

# get latest code
#WORKDIR /home
#RUN git clone ssh://git@github.com/rb-sdr/pyMLSDR

WORKDIR /root
COPY siamese.py /root/siamese.py

