FROM python:3

WORKDIR /root

#set up zmq
RUN pip3 install zmq
RUN pip3 install numpy

#set up pySDRBurstfile
COPY code/pySDRBurstfile /root/code/pySDRBurstfile
RUN cd code/pySDRBurstfile && python3 setup.py install

COPY code/stream.py /root/code/stream.py

ENTRYPOINT [ "python3", "/root/code/stream.py" ]                #run live
