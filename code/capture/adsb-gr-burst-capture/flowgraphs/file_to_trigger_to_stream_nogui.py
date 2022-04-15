#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Not titled yet
# GNU Radio version: 3.8.2.0

from gnuradio import blocks
import pmt
from gnuradio import gr
from gnuradio.filter import firdes
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
import streamer
import triggers


class trigger_to_stream_nogui(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "Not titled yet")

        ##################################################
        # Variables
        ##################################################
        self.sym_rate = sym_rate = 2e6
        self.samp_rate = samp_rate = 20e6
        self.sps = sps = samp_rate/sym_rate

        ##################################################
        # Blocks
        ##################################################
        self.triggers_DoubleSlidingWindowTrigger_0 = triggers.DoubleSlidingWindowTrigger( 200, 10, 2500, 160 )
        self.streamer_BurstStreamer_0 = streamer.BurstStreamer('tcp://172.17.0.3:5678')
        self.blocks_file_source_0 = blocks.file_source(gr.sizeof_gr_complex*1, '/radio/adsb-samp.cf32', False, 0, 0)
        self.blocks_file_source_0.set_begin_tag(pmt.PMT_NIL)



        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_file_source_0, 0), (self.triggers_DoubleSlidingWindowTrigger_0, 0))
        self.connect((self.triggers_DoubleSlidingWindowTrigger_0, 0), (self.streamer_BurstStreamer_0, 0))


    def get_sym_rate(self):
        return self.sym_rate

    def set_sym_rate(self, sym_rate):
        self.sym_rate = sym_rate
        self.set_sps(self.samp_rate/self.sym_rate)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.set_sps(self.samp_rate/self.sym_rate)

    def get_sps(self):
        return self.sps

    def set_sps(self, sps):
        self.sps = sps





def main(top_block_cls=trigger_to_stream_nogui, options=None):
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
