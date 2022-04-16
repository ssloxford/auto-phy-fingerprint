FROM python:3

#avoid questions when installing stuff in apt-get
ARG DEBIAN_FRONTEND=noninteractive

RUN pip3 install numpy bokeh pyModeS zmq pyproj

#copy in the codebase
WORKDIR /
RUN mkdir /code
COPY code /code

#WORKDIR /code/visualisation/adsb-positions/code
ENTRYPOINT ["bokeh", "serve", "/code/visualisation/adsb-positions/code"]

