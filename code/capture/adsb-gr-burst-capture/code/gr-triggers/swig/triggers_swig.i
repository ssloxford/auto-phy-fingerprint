/* -*- c++ -*- */

#define TRIGGERS_API

%include "gnuradio.i"           // the common stuff

//load generated python docstrings
%include "triggers_swig_doc.i"

%{
#include "triggers/DoubleSlidingWindowTrigger.h"
%}

%include "triggers/DoubleSlidingWindowTrigger.h"
GR_SWIG_BLOCK_MAGIC2(triggers, DoubleSlidingWindowTrigger);
