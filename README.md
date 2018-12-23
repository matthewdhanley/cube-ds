
# cube-ds
[![Build Status](https://travis-ci.org/matthewdhanley/cube-ds.svg?branch=master)](https://travis-ci.org/matthewdhanley/cube-ds)

Telemetry decoding, storing, and retrieval tool

## High Level Procedure
### Setup
1. Set up Logging
2. Read in configuration file
3. Parse commmand line arguments
4. Find files recursively from specified directory, which I call "Rundirs"
  * Files to be processed should match one of the RegEx strings in a list and none of the RegEx strings in an exclusion list.

### Perform the following for each file found in the Setup section
1. Cross reference the file found with the "Process Log," a log that keeps track of all the files that have already been processed. If the file has already been processed, skip it and move on to the next one
  * This step is ignored if in Testing mode
  * TODO: Provide configuration paramter to skip this step (seperate from testing mode)
2. Load data from raw file into a Python bytearray object
3. Determine type of processing that needs to be done. Currently supported types are AX.25(pre KISS stripping), AX.25(Post KISS stripping), and VCDU Frames (assumed to have good data alignment).
4. Turn the bytearray into a list of bytearrays, each containing a complete CCSDS frame. Note that there are multiple intermediate steps noted in the [section below](#going-from-raw-data-to-ccsds).
  * TODO: Make decoding more configurable
5. Sort the packets by Application Identification (APID) and add specific packet information as gleamed from [var/packet_defs.csv](var/packet_defs.csv)
  * TODO: Change to DataFrame from using dictionary
6. Loop through the sorted packets and extract data based on APID
  * Packet telemetry mappings shall be placed in var/points/ as CSV files
  * TODO: Read directly into DataFrame
7. Save data to different methods specified by configuration file.
8. Log that the file has been processed
9. Post any statistics gained from file processing

### Process SatNOGS data
  * WIP


## Going from raw data to CCSDS
### AX.25 Protocol
  * In an AX.25 frame, there is a static header of 16 bytes. This static header can be used to synchronize the frame. After the frame has been found, this header provides no useful function, so it is stripped.
### KISS Protocol
  * KISS is another protocol that allows decoded data frames to be found regardless of the content. The identifying bytes are as follows:
  ```angular2html
    KISS_FRAME_ESC  0xDB
    KISS_TFRAME_END 0xDC
    KISS_TFRAME_ESC 0xDD
    KISS_FRAME_END  0xC0
    KISS_FRAME_DATA 0x00
  ```
   If the sequence 0xDB 0xDC is found, that means that 0xDC was escaped by 0xDB and thus 0xDB must be removed. Same goes for 0xDB 0xDD. 

### VCDUs
  * VCDU Frames vary from mission to mission (TODO: Update to be more configurable). They tell some basic information including such as which Virtual Channel the data is coming down on, what the master frame count is, what that specific VC count is, and where the first full frame starts. These frames are a fixed size and can easily be interpreted as such. Any misalignment, however, will throw off processing.