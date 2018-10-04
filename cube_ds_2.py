import numpy as np
import json
import os
import logging
import logging.config
import struct
from ccsds import extract_CCSDS_packets
import csv
import re
import configparser
import pprint

CONFIG_FILE = "cube_ds_2.cfg"
APIDS_FILE = "apids_lite.json"  # todo - move to config
TEST_FILE = "D:\\home\\mhanl\\git\\cube-ds\\test\\Rundirs\\2018_269_12_15_46\\bct_fsw_2018_272_15_05_45"




def extract_tlm_from_packets(json_info, packets):
    for packet in packets:
        apid_dict = json_info[packet['name']]
        try:
            tlm_points = apid_dict['points']
        except KeyError:
            logger.error("No points defined for "+packet['name'])
            exit(0)

        for key in tlm_points:
            startByte = int(tlm_points[key]['startByte'])
            startBit = int(tlm_points[key]['startBit'])
            tlm_length = int(tlm_points[key]['size'])
            conversion = float(tlm_points[key]['conversion'])
            dtype = tlm_points[key]['dtype']
            header_length = int(packet['headerSize'])
            # pprint.pprint(packet['data'][header_length+startByte-2:header_length+startByte+tlm_length//8+2])
            # pprint.pprint(packet['data'][header_length+startByte:header_length+startByte+tlm_length//8])
            # print(packet['seconds'])
            tlmData = packet['data'][header_length+startByte:header_length+startByte+tlm_length//8]
            unpack_data_format = get_unpack_format(dtype, tlm_length)
            tlm_value = struct.unpack(unpack_data_format, tlmData)[0] * conversion
            print(key+": "+str(tlm_value))


def get_unpack_format(type, dsize):
    if dsize == 1:
        # bit
        letter = 'b'
    elif dsize == 3:
        # for some reason there is a datapoint that is 3 bits...
        letter = 'b'
        type = 'uint' # spoof next part
    elif dsize == 8:
        # char
        letter = 'b'
    elif dsize == 16:
        # short
        letter = 'h'
    elif dsize == 32:
        # int
        letter = 'i'
    elif dsize == 64:
        # long long
        letter = 'q'
    elif dsize == -1:
        # padding
        letter = str(dsize//8)+'x'  # want self.size bytes of padding
        type = 'int'
        size = 1
    else:
        logger.fatal("parsing error for datatype size")
        exit(0)

    if type == 'dn':
        letter = letter.upper()
    elif type == 'sn':
        letter = letter.lower()
    elif type == 'char':
        letter = str(int(size/8)) + 's'
    elif type == 'float':
        letter = 'd'
    else:
        logger.fatal("parsing error for datatype type")
        exit(0)

    letter = '>'+letter
    return letter


def get_json_info(jsonfilename):
    # make sure file exists
    assert os.path.exists(jsonfilename)

    with open(jsonfilename, 'r') as json_f:
        json_dict = json.load(json_f)

    return json_dict


def get_tlm_data(raw_file):
    logger.debug("Telemetry file -  "+raw_file)

    # check that the file exists
    if not os.path.exists(raw_file):
        logger.fatal("Telemetry Definition Directory does not exits. Check config file.")
        exit(0)

    # read the data into a numpy array
    logger.debug("reading data into numpy byte array")
    raw_data = np.fromfile(raw_file, dtype='>B')
    return raw_data


def get_logger():
    """
    Create a logging object for easy logging
    :return: logging object
    """
    # set up logger from config file
    if os.path.isfile(CONFIG_FILE):
        logging.config.fileConfig(CONFIG_FILE)
        logger = logging.getLogger('cube_ds')
    else:
        # use defaults if no config file
        format = '%(levelname)s - %(asctime)s - %(filename)s - %(funcName)s - %(lineno)d - %(message)s'
        logging.basicConfig(format=format)
        logger = logging.getLogger('cube_ds')
        logger.warning(CONFIG_FILE+' not found. Using defaults for logging.')

    logger.info('Logger started.')
    return logger


if __name__ == "__main__":
    # set up logger.
    global logger
    logger = get_logger()

    logger.debug("reading in json file")
    # returned a list of dicts
    json_info = get_json_info(APIDS_FILE)

    logger.debug("reading in tlm data")
    tlm_data = get_tlm_data(TEST_FILE)

    logger.debug("extracting ccsds packets")
    packets = extract_CCSDS_packets(json_info, tlm_data)
    extract_tlm_from_packets(json_info, packets)