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

#ifndef INCLUDED_TRIGGERS_DOUBLESLIDINGWINDOWTRIGGER_H
#define INCLUDED_TRIGGERS_DOUBLESLIDINGWINDOWTRIGGER_H

#include <triggers/api.h>
#include <gnuradio/block.h>

namespace gr {
  namespace triggers {

    /*!
     * \brief <+description of block+>
     * \ingroup triggers
     *
     */
    class TRIGGERS_API DoubleSlidingWindowTrigger : virtual public gr::block
    {
     public:
      typedef boost::shared_ptr<DoubleSlidingWindowTrigger> sptr;

      /*!
       * \brief Return a shared_ptr to a new instance of triggers::DoubleSlidingWindowTrigger.
       *
       * To avoid accidental use of raw pointers, triggers::DoubleSlidingWindowTrigger's
       * constructor is in a private implementation
       * class. triggers::DoubleSlidingWindowTrigger::make is the public interface for
       * creating new instances.
       */
      static sptr make(int windowsizeparam, float thresholdparam, int pdusampcountparam, int dontstopbeforeparam);
    };

  } // namespace triggers
} // namespace gr

#endif /* INCLUDED_TRIGGERS_DOUBLESLIDINGWINDOWTRIGGER_H */

