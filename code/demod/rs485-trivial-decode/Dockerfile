FROM python:3

WORKDIR /code

#avoid questions when installing stuff in apt-get
ARG DEBIAN_FRONTEND=noninteractive

#install swig
RUN apt-get update && apt-get install -y swig

#install pip dependencies
RUN pip3 install numpy matplotlib zmq


COPY code/decode.py /code

ENTRYPOINT ["/bin/bash", "-c"]






