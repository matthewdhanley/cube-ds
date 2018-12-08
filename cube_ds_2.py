__author__ = "Matthew Hanley"
__email__ = "mattdhanley@gmail.com"

import numpy as np
import os
import argparse
import struct
import csv
import re
import pprint
import datetime as dt
import pickle
import json
from config import *









def sort_packets(packets):
    packets_sorted = {}
    for packet in packets:
        packet_id = str(packet[0]) + str(packet[1])
        if packet_id in packets_sorted:
            packets_sorted[packet_id]['raw_packets'].append(packet)
        else:
            packets_sorted[packet_id] = {}
            packets_sorted[packet_id]['raw_packets'] = [packet]
    return packets_sorted




# ========================== NETCDF FUNCTIONS ===========================================



if __name__ == "__main__":
    # set up LOGGER.
    LOGGER.info("========================= Started ==========================")

    # Parsing command line arguments
    parser = argparse.ArgumentParser(description='Command Line Parser')
    parser.add_argument('-t', '--test', action="store_true", help="If present, program will be run in test mode")
    args = parser.parse_args()  # test bool will be stored in args.test
    if args.test:
        TEST = 1

    LOGGER.debug("reading in CSV file")
    csv_file = CONFIG_INFO['csv']['location']
    LOGGER.debug('csv file: ' + csv_file)

    # returned a list of dicts
    csv_info = get_csv_info(csv_file)

    # how the raw files are named
    # file_re_pattern = '^bct_\d{4}.*'
    file_re_pattern = '.*playback.*341_08.*'

    if not TEST:
        rawFiles = find_files(file_re_pattern, CONFIG_INFO['rundirs']['location'])
        mainGroup_location = CONFIG_INFO['netcdf']['location']
        processLog = CONFIG_INFO['process_log']['location']
        try:
            fileReadLog = open(processLog, mode='r')
        except PermissionError:
            LOGGER.fatal("Could not get permissions on " + processLog)
            exit(1)
    else:
        LOGGER.info("RUNNING IN TESTING MODE.")
        rawFiles = find_files(file_re_pattern, CONFIG_INFO['rundirs_test']['location'])
        mainGroup_location = CONFIG_INFO['netcdf_test']['location']

    for file in rawFiles:
        LOGGER.info("Processing "+file)
        if not TEST:
            # don't process file twice.
            foundFlag = 0
            for line in fileReadLog:
                if line.rstrip() == file:
                    foundFlag = 1
            if foundFlag:
                continue

        tlm_data = get_tlm_data(file)

        packets = extract_CCSDS_packets(csv_info, tlm_data)

        mainGroup = get_main_group(mainGroup_location)
        data = extract_tlm_from_packets(csv_info, packets, mainGroup=mainGroup)
        LOGGER.debug("Extracted all the data, adding to NetCDF file . . .")
        netcdf_add_data(data, mainGroup)
        mainGroup.close()
        # netcdf_add_data_2(data, mainGroup)

        # Clean up some variables
        del(data)
        del(tlm_data)
        del(packets)

        if not TEST:
            # append file to processed file log
            fileLog = open(processLog, mode='a')
            fileLog.write(file+'\n')
            fileLog.close()

    if not TEST:
        LOGGER.debug("Closed file read log")
        fileReadLog.close()

    LOGGER.info("Done")

