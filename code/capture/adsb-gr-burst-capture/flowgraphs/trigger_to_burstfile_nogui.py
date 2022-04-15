#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Not titled yet
# GNU Radio version: 3.8.2.0

from gnuradio import gr
from gnuradio.filter import firdes
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import uhd
import time
import burstfile
import triggers


class trigger_to_burstfile_nogui(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "Not titled yet")

        ##################################################
        # Variables
        ##################################################
        self.sym_rate = sym_rate = 2e6
        self.samp_rate = samp_rate = 20e6
        self.sps = sps = samp_rate/sym_rate
        self.filename = filename = "/radio/adsb_" + str(samp_rate) + "_" + str(int(time.time())) + ".sdrbf"

        ##################################################
        # Blocks
        ##################################################
        self.uhd_usrp_source_0 = uhd.usrp_source(
            ",".join(("", "")),
            uhd.stream_args(
                cpu_format="fc32",
                args='num_recv_frames=1024',
                channels=list(range(0,1)),
            ),
        )
        self.uhd_usrp_source_0.set_center_freq(1090e6, 0)
        self.uhd_usrp_source_0.set_gain(55, 0)
        self.uhd_usrp_source_0.set_antenna('RX2', 0)
        self.uhd_usrp_source_0.set_bandwidth(3e6, 0)
        self.uhd_usrp_source_0.set_samp_rate(samp_rate)
        self.uhd_usrp_source_0.set_time_unknown_pps(uhd.time_spec())
        self.triggers_DoubleSlidingWindowTrigger_0 = triggers.DoubleSlidingWindowTrigger( 200, 10, 2500, 160 )
        self.burstfile_BurstfileWriter_0 = burstfile.BurstfileWriter(filename)



        ##################################################
        # Connections
        ##################################################
        self.connect((self.triggers_DoubleSlidingWindowTrigger_0, 0), (self.burstfile_BurstfileWriter_0, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.triggers_DoubleSlidingWindowTrigger_0, 0))


    def get_sym_rate(self):
        return self.sym_rate

    def set_sym_rate(self, sym_rate):
        self.sym_rate = sym_rate
        self.set_sps(self.samp_rate/self.sym_rate)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.set_filename("/radio/adsb_" + str(self.samp_rate) + "_" + str(int(time.time())) + ".sdrbf")
        self.set_sps(self.samp_rate/self.sym_rate)
        self.uhd_usrp_source_0.set_samp_rate(self.samp_rate)

    def get_sps(self):
        return self.sps

    def set_sps(self, sps):
        self.sps = sps

    def get_filename(self):
        return self.filename

    def set_filename(self, filename):
        self.filename = filename





def main(top_block_cls=trigger_to_burstfile_nogui, options=None):
    tb = top_block_cls()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()

    try:
        input('Press Enter to quit: ')
    except EOFError:
        pass
    tb.stop()
    tb.wait()


if __name__ == '__main__':
    main()
