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

#ifndef INCLUDED_TRIGGERS_DOUBLESLIDINGWINDOWTRIGGER_IMPL_H
#define INCLUDED_TRIGGERS_DOUBLESLIDINGWINDOWTRIGGER_IMPL_H

#include <triggers/DoubleSlidingWindowTrigger.h>

namespace gr {
  namespace triggers {

    class DoubleSlidingWindowTrigger_impl : public DoubleSlidingWindowTrigger
    {
     private:
      // Nothing to declare in this block.
        int windowsize;
      float threshold;
      int pdusampcount;
          int dontstopbefore;

      float* pwrs;
      bool initialvals;
      float winA;
      float winB;
      int propagateCount;

     public:
      DoubleSlidingWindowTrigger_impl(int windowsizeparam, float thresholdparam, int pdusampcountparam, int dontstopbeforeparam);
      ~DoubleSlidingWindowTrigger_impl();

      // Where all the action really happens
      void forecast (int noutput_items, gr_vector_int &ninput_items_required);

      int general_work(int noutput_items,
           gr_vector_int &ninput_items,
           gr_vector_const_void_star &input_items,
           gr_vector_void_star &output_items);

    };

  } // namespace triggers
} // namespace gr

#endif /* INCLUDED_TRIGGERS_DOUBLESLIDINGWINDOWTRIGGER_IMPL_H */

