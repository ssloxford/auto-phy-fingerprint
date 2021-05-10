FROM python:3

WORKDIR /code

#avoid questions when installing stuff in apt-get
ARG DEBIAN_FRONTEND=noninteractive

RUN pip3 install numpy bokeh pyModeS zmq pyproj

COPY code /code/mapview

ENTRYPOINT ["bokeh", "serve", "mapview"]

