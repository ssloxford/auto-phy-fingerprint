FROM python:3

WORKDIR /code

#avoid questions when installing stuff in apt-get
ARG DEBIAN_FRONTEND=noninteractive

#install pip dependencies
RUN pip3 install numpy pyModeS zmq sqlalchemy

COPY code/store.py /code

ENTRYPOINT ["python3", "store.py"]

