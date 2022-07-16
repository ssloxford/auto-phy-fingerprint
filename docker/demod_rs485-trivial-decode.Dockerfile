FROM python:3

WORKDIR /code

#avoid questions when installing stuff in apt-get
ARG DEBIAN_FRONTEND=noninteractive

#install swig
RUN apt-get update && apt-get install -y swig

#install pip dependencies
RUN pip3 install numpy matplotlib zmq

#copy in the codebase
WORKDIR /
RUN mkdir /code
COPY code /code

ENTRYPOINT ["python3", "/code/demod/rs485-trivial-decode/code/decode.py"]





