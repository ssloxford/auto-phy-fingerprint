/* -*- c++ -*- */
/*
 * Copyright 2021 Richard Baker.
 *
 * This is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3, or (at your option)
 * any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this software; see the file COPYING.  If not, write to
 * the Free Software Foundation, Inc., 51 Franklin Street,
 * Boston, MA 02110-1301, USA.
 */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <gnuradio/io_signature.h>
#include "DoubleSlidingWindowTrigger_impl.h"

#include <volk/volk.h>
//#include <volk/volk_common.h>
#include <volk/volk_malloc.h>

namespace gr {
  namespace triggers {

    DoubleSlidingWindowTrigger::sptr
    DoubleSlidingWindowTrigger::make(int windowsizeparam, float thresholdparam, int pdusampcountparam, int dontstopbeforeparam)
    {
      return gnuradio::get_initial_sptr
        (new DoubleSlidingWindowTrigger_impl(windowsizeparam, thresholdparam, pdusampcountparam, dontstopbeforeparam));
    }


    /*
     * The private constructor
     */
    DoubleSlidingWindowTrigger_impl::DoubleSlidingWindowTrigger_impl(int windowsizeparam, float thresholdparam, int pdusampcountparam, int dontstopbeforeparam)
      : gr::block("DoubleSlidingWindowTrigger",
              gr::io_signature::make(1, 1, sizeof(gr_complex)),
              gr::io_signature::make(1, 1, sizeof(gr_complex)))
    {
      windowsize = windowsizeparam;
      threshold = thresholdparam;
      pdusampcount = pdusampcountparam;
      dontstopbefore = dontstopbeforeparam;

      initialvals = true;
      winA = 0.0;
      winB = 0.0;
      propagateCount = 0;
    }

    /*
     * Our virtual destructor.
     */
    DoubleSlidingWindowTrigger_impl::~DoubleSlidingWindowTrigger_impl()
    {
    }

    void
    DoubleSlidingWindowTrigger_impl::forecast (int noutput_items, gr_vector_int &ninput_items_required)
    {
        ninput_items_required[0] = noutput_items + (2*windowsize);
    }

    int
    DoubleSlidingWindowTrigger_impl::general_work (int noutput_items,
                       gr_vector_int &ninput_items,
                       gr_vector_const_void_star &input_items,
                       gr_vector_void_star &output_items)
    {

      const int n_in = ninput_items[0];   //assuming only a single input stream

      int j = 0;    //number of propagated values this time

      const gr_complex *in = (const gr_complex *) input_items[0];
      gr_complex *out = (gr_complex *) output_items[0];

      //calculate the powers
      float* pwrs = (float*) volk_malloc(n_in * sizeof(float), volk_get_alignment());
      volk_32fc_magnitude_squared_32f(pwrs, in, n_in);

      //process the first 2*windowsize values but don't produce values - those values are dropped
      if (initialvals) {
        //haven't had enough values in yet, so just populate the windows
        for (int i = -windowsize; i < 0; i++) {
          winA += pwrs[i+(2*windowsize)];
          winB += pwrs[i+windowsize];
        }

        initialvals = false;
        std::cout << "DoubleSlidingWindowTrigger: Initial vals set" << std::endl;

        consume_each(0);  //need all the values again because they need to feed out of winA and into winB
        return 0;     //nothing produced by this - initial samples are just dropped
      }

      //process all the values (forecast has guaranteed us 2*windowsize more input than we need to output)
      for (int i = 0; i < noutput_items; i++) {
        //advance the windows
        winA += pwrs[i+(2*windowsize)];
        winA -= pwrs[i+windowsize];
        winB += pwrs[i+windowsize];
        winB -= pwrs[i];

        //calculate the change
        float startchange = winA / winB;
        float endchange = winB / winA;

        //if the change is above a threshold then trigger a burst, but don't allow retriggering during a burst
        //could also implement a counter here so that changes need to be above the threshold for x samples
        if (startchange > threshold && propagateCount == 0) {
          propagateCount = pdusampcount;
        }

        //out[i] = gr_complex(startchange, pwrs[i] * 20);    //good for debudding window size issues

                if (endchange > threshold && propagateCount > 0 && propagateCount < (pdusampcount - dontstopbefore)) {      //the end trigger shouldn't fire unless we're propagating, but ignore the end of the preamble     //TODO: make the threshold a parameter
                        propagateCount = windowsize * 2;        //as the window is computed ahead of time, need to delay here to allow the end of the message to pass
                }

        if (propagateCount > 0) {          
          out[j++] = in[i];

          //write a start tag if this is the first of a burst
          if (propagateCount == pdusampcount) {
            //out[j-1] = 10;      //handy debugging behaviour that shows up in the waveform
            add_item_tag(0, nitems_written(0) + j, pmt::mp("burst"), pmt::PMT_T);  //args: port, offset, key, value
          }

          propagateCount--;
          //write an end tag if this is the last of a burst
          if (propagateCount == 0) {
            add_item_tag(0, nitems_written(0) + j, pmt::mp("burst"), pmt::PMT_F);
          }
        }

      }

      //consume all the processed items
      consume_each(noutput_items);

      volk_free(pwrs);

      // Tell runtime system how many output items we produced.
      return j;

    }

  } /* namespace triggers */
} /* namespace gr */

