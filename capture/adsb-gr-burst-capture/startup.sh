echo 'export PYTHONPATH=/usr/local/lib/python3/dist-packages:usr/local/lib/python2.7/site-packages:$PYTHONPATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/user/local/lib:$LD_LIBRARY_PATH' >> ~/.bashrc
echo 'export PYTHONPATH=/usr/local/lib/python3/dist-packages:usr/local/lib/python2.7/site-packages:$PYTHONPATH' >> ~/.profile
echo 'export LD_LIBRARY_PATH=/user/local/lib:$LD_LIBRARY_PATH' >> ~/.profile

export PYTHONPATH=/usr/local/lib/python3/dist-packages:usr/local/lib/python2.7/site-packages:$PYTHONPATH
export LD_LIBRARY_PATH=/user/local/lib:$LD_LIBRARY_PATH
export PYTHONPATH=/usr/local/lib/python3/dist-packages:usr/local/lib/python2.7/site-packages:$PYTHONPATH
export LD_LIBRARY_PATH=/user/local/lib:$LD_LIBRARY_PATH

#ensure ssh running
service ssh restart

#/bin/bash                                                              		#live environment with no running capture
#/usr/bin/python3 -u /root/flowgraphs/trigger_to_burstfile_nogui.py     		#run live capture to burstfile
#/usr/bin/python3 -u /root/flowgraphs/file_to_trigger_to_stream_nogui.py 		#process raw waveform file to stream
/usr/bin/python3 -u /root/flowgraphs/trigger_to_stream_nogui.py 				#run live capture to stream
