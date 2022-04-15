FROM python:3

#avoid questions when installing stuff in apt-get
ARG DEBIAN_FRONTEND=noninteractive

#install pip dependencies
RUN pip3 install numpy pyModeS zmq

#copy in the codebase
WORKDIR /
RUN mkdir /code
COPY code /code

ENTRYPOINT ["python3", "/code/filtering/adsb-position-msg-filter/code/filter.py"]
