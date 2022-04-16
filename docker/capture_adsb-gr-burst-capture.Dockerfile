FROM sslox-gnuradio-3.8

#copy in the codebase
WORKDIR /
RUN mkdir /code
COPY code /code

#set up gr-triggers
RUN cd /code/capture/adsb-gr-burst-capture/code/gr-triggers && mkdir build && cd build && cmake .. && \
	make && make install && ldconfig

#set up pySDRBurstfile
RUN cd /code/capture/adsb-gr-burst-capture/code/pySDRBurstfile && python3 setup.py install

#set up gr-burstfile
RUN cd /code/capture/adsb-gr-burst-capture/code/gr-burstfile && mkdir build && cd build && cmake .. && \
	make && make install && ldconfig

#set up gr-streamer
RUN cd /code/capture/adsb-gr-burst-capture/code/gr-streamer && mkdir build && cd build && cmake .. && \
	make && make install && ldconfig

ENTRYPOINT [ "/bin/bash", "/code/capture/adsb-gr-burst-capture/startup.sh" ]		#run live
