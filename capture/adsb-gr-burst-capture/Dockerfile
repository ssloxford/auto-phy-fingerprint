FROM sslox-gnuradio-3.8

WORKDIR /root

#set up gr-triggers
COPY code/gr-triggers /root/gr-triggers
RUN cd gr-triggers && mkdir build && cd build && cmake .. && \
	make && make install && ldconfig

#set up pySDRBurstfile
COPY code/pySDRBurstfile /root/pySDRBurstfile
RUN cd pySDRBurstfile && python3 setup.py install

#set up gr-burstfile
COPY code/gr-burstfile /root/gr-burstfile
RUN cd gr-burstfile && mkdir build && cd build && cmake .. && \
	make && make install && ldconfig

COPY flowgraphs /root/flowgraphs
COPY startup.sh /root

WORKDIR /radio

ENTRYPOINT [ "/bin/bash", "/root/startup.sh" ]		#run live
