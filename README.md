# Automatic PHY-layer Fingerprinting

This project implements an end-to-end system for automatic fingerprinting of transmitters at the physical layer, incorporating capture, demodulation, model training, fingerprinting, fingerprint tracking and visualisation.

The project underpins work to study the usefulness of machine-learning techniques in device fingerprinting. Fingerprint derivation is typically a costly, manual task and can vary noticeably between technologies and scenarios. There is also an inherent tension between deriving fingerprinting methods which are robust and generalisable vs. taking full advantage of specifics in a given scenario to enhance performance. The goal of this work is to reduce the need for human analysis in deriving fingerprints. 

The system is built on a modular framework to permit simple variation at each stage. 

At present the framework is validated with two concrete examples, developed for this project:

* 1090 MHz ADS-B traffic, received over-the-air
* RS-485 Serial traffic, received via cabling

### Architecture

The system comprises several components:

![](documentation/verification-diagram.png) 

| Component | Description |
| --- | --- |
| Signal Capture | Retrieval of a raw signal. Compatible with either software radio frameworks (e.g., GNURadio) or other digital capture (e.g., storage oscilloscopes). |
| Demodulation | Interface to 3rd party demodulation code for message validation and data extraction. |
| Identifier Masking | A pre-processing stage to remove in-message identifiers, which lead to trivial solutions |
| Fingerprint Extraction and Comparison | A Siamese network model used to derive comparisons between received messages across observed transmitters. |
| Message Verification | Long-term tracking of message fingerprint comparisons and identity verification |


In addition to the main pipeline, some additional components are implemented to help study the data:

| Component | Description |
| --- | --- |
| Storage | Storage components receive bursts and write them to files for offline processing (e.g. model training). At present there are two storage components: one writing bursts to an HDF5 file, one writing decoded messages to an SQLite3 database. |
| Visualisation | Visualisations to show live performance. A message verification visualisation is implemented for the ADS-B case, in which messages and their verification status are displayed, alongside a map of their claimed positions. |
| Supporting (Weather) | A supporting component retrieves and stores data on local weather conditions. |

Data transfer between stages is principally through ZMQ message queues in a PUB/SUB pattern. Each part of the pipeline outputs received bursts, along with appropriate metadata, and forwards them to all subscribers. Alternatively, data can be written to files at each stage, for offline processing. However the streaming model is preferred, both for architectural convenience when splitting across containers/hosts and to support long-running, live uses in which stopping and outputting a file is cumbersome. As such, the file-based method is considered deprecated. 


### Installation

#### Dependencies

On host:

* Docker
* SecLab Docker images for GNURadio (https://github.com/ssloxford/docker-gnuradio)

Included within containers:

* Python 3
	* numPy, pyplot, h5py
	* pySDRBurstfile (https://gitlab.com/sdrburstfile/pysdrburstfile)
* Ettus USRP UHD
* GNURadio
	* gr-burstfile
	* gr-triggers
* Tensorflow 2, Keras
* ZMQ
* Bokeh

#### Process

1. Clone and build base GNURadio images

	1. `git clone https://github.com/ssloxford/docker-gnuradio`
	1. `cd docker-gnuradio`
	1. `./build_all.sh`
1. `git clone --recursive https://github.com/ssloxford/auto-phy-fingerprint`
1. Create directory `auto-phy-fingerprint-mountdir`
1. If using GPU resources, add a suitable `deploy.resources` section to `docker-compose.yml`
1. `docker-compose up -d`
1. Check for files appearing in `auto-phy-fingerprint-mountdir` and accessibility of the visualisation service on port 5006

### Case Studies

Two case studies exist at present: one for [ADS-B](documentation/case-study-adsb.md) and one for [RS-485](documentation/case-study-rs485.md). Please see each link for details. 



### Acknowledgements

This project is supported by InnovateUK under the HICLASS project. 
