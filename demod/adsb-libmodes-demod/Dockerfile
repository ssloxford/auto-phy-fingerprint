FROM python:3

WORKDIR /code

#install pip dependencies
RUN pip3 install numpy pyplot pyModeS

#set up pySDRBurstfile
COPY code/pySDRBurstfile code/pySDRBurstfile
RUN cd pySDRBurstfile && python3 setup.py install

COPY code/bursts_to_libmodes.py /code
CMD ["python3", "bursts_to_libmodes.py"]


