import yaml
from bitarray import bitarray
import cubeds.pylogger
import cubeds.exceptions
import struct
import os
import numpy as np
import csv
import json


def read_yaml(file):
    """
    Reads in yaml (.yml) file
    :param file: yaml file location
    :return: dictionary of information
    """
    with open(file, mode='r') as stream:
        out = yaml.load(stream)

    return out


def extract_bits_from_bytes(data, start_bit, num_bits):
    """
    Extracts bits from a group of bytes
    :param data: byte data
    :param start_bit: starting bit to begin extraction
    :param num_bits: number of bits to extract
    :return: bitarray of requested bits
    """
    b = bitarray(endian='big')
    b.frombytes(data)
    out = b[start_bit:start_bit+num_bits]
    return out


def bitstring_to_int(bitstr):
    """
    Converts a bitstring to an integer
    :param bitstr: bitstring
    :return: integer representation of bitstring
    """
    b_list = bitstr.tolist()
    mystring = ''
    for s in b_list:
        if s:
            mystring += '1'
        else:
            mystring += '0'
    b = int(mystring, 2)
    return b


def get_unpack_format(in_dtype, dsize, endian='big'):
    """
    Given data type and size, generate a format for struct.unpack.
    ASSUMES BIG ENDIAN for the data that will be unpacked. can specifiy by using endian="little"
    :param in_dtype: Type of data. Valid types are dn (unsigned), sn (signed), char, float, or double
    :param dsize: size of data in BITS!!!!
    :param endian: endianess of the data
    :return:
    """
    logger = cubeds.pylogger.get_logger(__name__)
    if dsize <= 8:
        # bits
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
        in_dtype = 'int'
        dsize = 1
    else:
        logger.fatal("parsing error for datatype size")
        raise cubeds.exceptions.UnpackFormatError(msg="parsing error for datatype size")

    if in_dtype == 'dn':
        letter = letter.upper()
    elif in_dtype == 'sn':
        letter = letter.lower()
    elif in_dtype == 'char':
        letter = str(int(dsize/8)) + 's'
    elif in_dtype == 'float' or in_dtype == 'double':
        letter = 'd'
    else:
        logger.fatal("parsing error for datatype \"" + in_dtype + "\" with size \"" + str(dsize) + "\"")
        raise cubeds.exceptions.UnpackFormatError(msg="parsing error for datatype \"" + in_dtype + "\" with size \""
                                                      + str(dsize) + "\"")

    if endian == 'big':
        letter = '>' + letter
    elif endian == 'little':
        letter = '<' + letter
    else:
        logger.fatal("DID NOT SPECIFY ENDIANNESS CORRECTLY")
        raise cubeds.exceptions.UnpackFormatError("Endianness not specified correctly.")
    return letter


def extract_bits(data, bit, length=1):
    """
    Extracts bits given data, start bit, and length
    :param data: data to extract bits from
    :param bit: starting position for extraction
    :param length: number of bits to extract, default=1
    :return: resulting integer of extracted bits
    """
    bits = bitarray(data, endian='big')
    if length > 1:
        out = bits[bit:bit+length]
        try:
            out = struct.unpack('>B', out.tobytes())[0]
        except struct.error:
            out = 0
    else:
        try:
            out = bits[bit]
        except IndexError:
            out = 0
    return int(out)


def get_csv_encoding(config):
    """
    Grabs the CSV encoding type form the config file, csv section, encoding variable.
    :return: csv encoding type string
    """
    logger = cubeds.pylogger.get_logger(__name__)
    try:
        csv_encoding = config.config['telemetry'][config.yaml_key]['encoding']
    except KeyError:
        csv_encoding = 'utf-8'
        logger.debug('Using utf-8 encoding because couldn\'t find encoding type in config file')

    return csv_encoding


def get_csv_info(config):
    """
    Reads in CSV info from top level file
    :param csv_filename: csv file name
    :return: dictionary of csv lines
    """
    logger = cubeds.pylogger.get_logger(__name__)
    csv_filename = config.config['telemetry'][config.yaml_key]['packet_definitions']

    # make sure file exists
    try:
        assert os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), csv_filename))
    except AssertionError as e:
        logger.fatal(e)
        logger.fatal("Cannot find packet definition file "+csv_filename)
        raise cubeds.exceptions.DecoderError

    csv_encoding = get_csv_encoding(config)

    with open(csv_filename, mode='r', encoding=csv_encoding) as csv_f:
        reader = csv.DictReader(csv_f)
        csv_dict_list = []
        for row in reader:
            csv_dict_list.append(row)
    return csv_dict_list


def get_tlm_points(points_file, config):
    """
    This function will get all the points from the points file input to the function
    :param points_file: csv file with all the points.
    :param config: cubeds.config.Config object.
    :return: List of dictionaries of points.
    """
    logger = cubeds.pylogger.get_logger(__name__)
    # make sure file exists
    assert os.path.exists(points_file)

    csv_encoding = get_csv_encoding(config)

    with open(points_file, mode='r', encoding=csv_encoding) as csv_f:
        # create a dictionary from the top level csv file
        reader = csv.DictReader(csv_f)

        # init list for saving the points dict
        points_dict_list = []
        for row in reader:
            # if the "state" column includes a "/", that means that there is a properly formatted state pair,
            # i.e. "0/ON 1/OFF"
            # ALL PAIRS SHOULD BE SEPERATED BY A SPACE AND FORMATTED AS FOLLOWS: VAL/STR VAL/STR
            if '/' in row['state']:
                row['unit'] = ''

                # Seperate pairs and strip whitespace
                state_array = [x.strip() for x in row['state'].split(' ')]

                # init empty dictionary
                state_dict = {}

                # loop through the pairs and stor them in the dictionary with the integer as the key and the string as
                # the value
                for keyStrPair in state_array:
                    # extract the "key/str" pair
                    state_val, state_str = keyStrPair.split('/')
                    state_dict[state_val] = state_str

                row['state'] = json.dumps(state_dict)
            else:
                row['state'] = ''

            # append the new dictionary to the list
            points_dict_list.append(dict(row))
    return points_dict_list
