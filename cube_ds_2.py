__author__ = "Matthew Hanley"
__email__ = "mattdhanley@gmail.com"

import numpy as np
import os
import argparse
import struct
import csv
import re
import configparser
import pprint
import datetime as dt
import pickle
import json
from netCDF4 import Dataset
import pylogger


# GLOBALS ==================================================================================
TAI_EPOCH = dt.datetime(2000, 1, 1, 11, 59, 27)  # Epoch time for incoming time stamps
MAX_TIME = dt.datetime(2020, 1, 1, 12, 0, 0)  # max allowable time for naive filtering
MIN_TIME = dt.datetime(2018, 1, 1, 12, 0, 0)  # minimum allowable time for naive filtering


CONFIG_FILE = "cube_ds_2.cfg"  # defines config file for configparser
# Parsing the config file.
CONFIG_INFO = configparser.ConfigParser()
CONFIG_INFO.read(CONFIG_FILE)

# Setup for TEST mode
TEST = int(CONFIG_INFO['TEST']['TEST'])  # check if TEST mode is set in config file

LOGGER = pylogger.get_logger()


def get_csv_encoding():
    """
    Grabs the CSV encoding type form the config file, csv section, encoding variable.
    :return: csv encoding type string
    """

    if TEST:
        config_param = 'csv_test'
    else:
        config_param = 'csv'

    try:
        csv_encoding = CONFIG_INFO[config_param]['encoding']
    except KeyError:
        csv_encoding = 'utf-8'
        LOGGER.debug('Using utf-8 encoding because couldn\'t find encoding type in config file')

    return csv_encoding


def get_tlm_points(pointsFile, csv_encoding='utf-8'):
    """
    This function will get all the points from the points file input to the function
    :param pointsFile: csv file with all the points.
    :return: List of dictionaries of points.
    """
    # make sure file exists
    assert os.path.exists(pointsFile)

    csv_encoding = get_csv_encoding()

    with open(pointsFile, mode='r', encoding=csv_encoding) as csv_f:
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
                stateArray = [x.strip() for x in row['state'].split(' ')]

                # init empty dictionary
                state_dict = {}

                # loop through the pairs and stor them in the dictionary with the integer as the key and the string as
                # the value
                for keyStrPair in stateArray:
                    # extract the "key/str" pair
                    stateVal, stateStr = keyStrPair.split('/')
                    state_dict[stateVal] = stateStr

                row['state'] = json.dumps(state_dict)
            else:
                row['state'] = ''

            # append the new dictionary to the list
            points_dict_list.append(dict(row))
    return points_dict_list


def extract_tlm_from_packets(csv_info, packets, mainGroup=''):
    """
    This function will extract telemetry values from the given packets list using information from the csv file
    :param csv_info: List of dictionaries as returned by function get_csv_info
    :param packets: list of packet dictionaries as returned by extract_CCSDS_packets
    :param mainGroup: netCDF main group, if set it will write points to this group.
    :return: dictionary of telemetry points and values with the top level key being a time and the value being
    a dictionary of telemetry points mapped to values
    """
    # init return variable
    data_struct = {}

    # loop through inputted data
    for packet in packets:
        # get datetime object for the time of the packet
        packet_dt = get_tlm_time_dt(packet['seconds'])

        # check to make sure that the time is within a valid range
        if not MIN_TIME < packet_dt < MAX_TIME:
            # log the warning and continue if out of range
            LOGGER.warning("Found packet with bogus time of " + packet_dt.strftime("%Y-%m-%d %H:%M:%S") + ". Skipping it.")
            continue

        # make the packet key the seconds field of the packet. should be unique for each packet...maybe
        packet_key = str(packet['seconds'])

        # create entry into the data_struct using the key. Init to an empty dictionary that will then hold
        # mnemonics and values for telemetry
        data_struct[packet_key] = {}

        # empty points file, do a check later to see if it is set
        points_file = ''
        for csv_def in csv_info:
            # need to loop through the top file to find the packet definition
            if csv_def['packetName'] == packet['name']:
                # if it is a match, store the points definition file and break out of the search loop
                points_file = csv_def['pointsFile']
                break

        # if the file wasn't found, send message to user and exit
        if points_file == '':
            LOGGER.error('error finding points definitions for packet ' + packet['name'])
            exit(0)

        # extract the telemetry points from the file
        tlm_points = get_tlm_points(points_file)

        for point in tlm_points:
            # get start bit and start byte for data extraction
            startByte = int(point['startByte'])
            startBit = int(point['startBit'])

            # size is needed for selecting the right amount of data
            tlm_length = int(point['size'])

            # need a check to see if the length is less than one byte
            # python can only grab one byte at a time
            if tlm_length < 8:
                tlm_length = 8

            # conver the conversion to a float
            conversion = float(point['conversion'])

            # get the datatype
            dtype = point['dtype']

            # grab the header length from the packet
            header_length = int(packet['headerSize'])

            # get the relavent data from the packet
            tlmData = packet['data'][header_length+startByte:header_length+startByte+tlm_length//8]

            # generate a format string for struct.unpack
            unpack_data_format = get_unpack_format(dtype, tlm_length)

            # try to unpack the data (if it's not a char, chars are having issues?)
            # ALSO CONVERT TO THE EU
            # todo - why aren't we decoding chars?
            if point['dtype'] != 'char':
                try:
                    tlm_value = struct.unpack(unpack_data_format, tlmData)[0] * conversion
                except struct.error:
                    # not extracting the right amount of data. Print some debug information and move on
                    LOGGER.warning("Packet ended unexpectedly.")
                    pprint.pprint(point)
                    pprint.pprint(tlmData)
                    print(unpack_data_format)
                    continue
                except TypeError as e:
                    # had an issue with types. Print debug info and exit. This is a more serious issue.
                    print(point)
                    print(tlm_value)
                    print(e)
                    exit(1)

            # index into the struct and save the value for the tlm point
            data_struct[packet_key][point['name']] = tlm_value

            # # if mainGroup is supplied to the function call, add point to netcdf file
            if mainGroup != '':
                if point['name'] not in mainGroup.variables.keys():
                    # If not, create it.
                    dtype_string = get_netcdf_dtype(point['size'], state=point['state'])
                    datapt = mainGroup.createVariable(point['name'], dtype_string, ("time",))
                    datapt.setncattr('unit', point['unit'])
                    datapt.setncattr('state', point['state'])
                    datapt.setncattr('description', point['description'])

    return data_struct


def get_tlm_time_dt(taiTime):
    """
    Convert seconds since epoch to datetime object
    :param taiTime: seconds since TAI_EPOCH variable
    :return: datetime object
    """
    tlm_dt = TAI_EPOCH + dt.timedelta(seconds=taiTime)
    return tlm_dt


def get_unpack_format(type, dsize, endian='big'):
    """
    Given data type and size, generate a format for struct.unpack.
    ASSUMES BIG ENDIAN for the data that will be unpacked. can specifiy by using endian="little"
    :param type: Type of data. Valid types are dn (unsigned), sn (signed), char, float, or double
    :param dsize: size of data in BITS!!!!
    :return:
    """
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
        type = 'int'
        dsize = 1
    else:
        LOGGER.fatal("parsing error for datatype size")
        exit(0)

    if type == 'dn':
        letter = letter.upper()
    elif type == 'sn':
        letter = letter.lower()
    elif type == 'char':
        letter = str(int(dsize/8)) + 's'
    elif type == 'float' or type == 'double':
        letter = 'd'
    else:
        LOGGER.fatal("parsing error for datatype \"" + type + "\" with size \"" + str(dsize) + "\"")
        exit(1)

    if endian == 'big':
        letter = '>' + letter
    elif endian == 'little':
        letter = '<' + letter
    else:
        LOGGER.warning("DID NOT SPECIFY ENDIANNESS CORRECTLY")

    return letter


def get_csv_info(csvfilename):
    """
    Reads in CSV info from top level file
    :param csvfilename: csv file name
    :return: dictionary of csv lines
    """
    # make sure file exists
    assert os.path.exists(csvfilename)

    csv_encoding = get_csv_encoding()

    with open(csvfilename, mode='r', encoding=csv_encoding) as csv_f:
        reader = csv.DictReader(csv_f)
        csv_dict_list = []
        for row in reader:
            csv_dict_list.append(row)
    return csv_dict_list


def get_tlm_data(raw_file, endian="big"):
    """
    reads in raw data
    :param raw_file: binary data file. currently need continuous CCSDS packets in file.
    TODO - GET KISS DECODING
    :return: large endian numpy byte array
    """
    LOGGER.debug("Telemetry file -  " + raw_file)

    # check that the file exists
    if not os.path.exists(raw_file):
        LOGGER.fatal("Telemetry Definition Directory does not exits. Check config file.")
        exit(0)

    # read the data into a numpy array
    LOGGER.debug("reading data into numpy byte array")
    if endian=="big":
        raw_data = np.fromfile(raw_file, dtype='>B')
    elif endian=="little":
        raw_data = np.fromfile(raw_file, dtype='<B')
    else:
        LOGGER.error("DID NOT specify correct endian")
        exit(1)
    return raw_data


def get_header_dict(headerfile):
    """
    Generates a header dictionary list from the header csv file
    :param headerfile: CSV Header File
    :return: list of dictionaries of components of the header
    """
    # make sure file exists
    assert os.path.exists(headerfile)

    csv_encoding = get_csv_encoding()

    with open(headerfile, mode='r', encoding=csv_encoding) as csv_f:
        reader = csv.DictReader(csv_f)
        header_dict_list = []
        for row in reader:
            header_dict_list.append(dict(row))
    return header_dict_list


def extract_CCSDS_packets(csv_info, data):
    '''
    This function will go through raw data and extract raw packets.
    ASSUMPTIONS:
    Data is not in a nice format, will need to find the beginning of frames.
    However, frames are continuous. Any AX25 has been dealt with.
    :param data: Raw data to find the packets in
    :param apids: list of apids to look for
    :return: dictionary? of packets
    '''

    # loop through apids and find potential frames
    packet_dict_list = []
    for csv_dict in csv_info:

        header_file = csv_dict['headerFile']
        # LOGGER.debug("looking at "+header_file)
        header_dict_list = get_header_dict(header_file)

        # apid_dict = csv_info[top_key]

        known_dict_list = []  # keeps track of how many fields that we know we can use to sync up the packet

        # loop through fields in the header and generate an unpack string
        # init some variables to keep track of header continuity
        last_byte = 0
        last_bit = 0
        last_size = 0
        header_size = 0
        index_counter = 0

        header_index_dict = {}

        # flags
        first_iteration = 1
        processing_bits = 0

        # init the format string holder
        # the '>' is specifying big endian
        format_string = '>'
        for header_dict_field in header_dict_list:

            # Some error checking
            if first_iteration:
                # check to make sure that the header starts at bit/byte 0
                if int(header_dict_field['startBit']) != 0 or int(header_dict_field['startByte']) != 0:
                    LOGGER.fatal("Header does not start at zero.")
                    exit(0)
                first_iteration = 0

            else:
                # make sure that the fields in the header are not overlappinsg. This will cause problems
                if int(header_dict_field['startByte']) == int(last_byte and header_dict_field['startBit']) == 0:
                    LOGGER.fatal("There is overlap in the header for " + csv_dict['packetName'] +
                                 ". This is not currently supported.")
                    exit(0)

                # make sure there are no gaps
                if last_byte * 8 + last_bit + last_size !=\
                        int(header_dict_field['startBit']) + int(header_dict_field['startByte']) * 8:
                    LOGGER.fatal("There is a gap in your header for " + csv_dict['packetName'] +
                                 " at " + header_dict_field['field'] + ". Consider adding \"padding\"")
                    exit(0)

            # this if statement is checking if we are at a new byte or not.
            # if there are bits involved, we need to know so we can do special masking.
            if (int(header_dict_field['startByte'])*8 + int(header_dict_field['size'])) // 8 != last_byte:
                processing_bits = 0

            # ASSUMPTION: HEADERS ARE ALL GOING TO BE DNs
            # building a string to use with struct.unpack
            # this should never really need to be altered.
            current_letter = ''
            packet_size = int(header_dict_field['size'])
            if packet_size % 8 != 0:
                if not processing_bits:
                    processing_bits = 1
                    current_letter = 'B'
                else:
                    current_letter = ''
                # todo - write function to unmask bits
                pass
            elif packet_size == 8:
                current_letter = 'B'
            elif packet_size == 16:
                current_letter = 'H'
            elif packet_size == 32:
                current_letter = 'I'
            elif packet_size == 64:
                current_letter = 'Q'
            else:
                LOGGER.fatal('Issue decoding header sizes into struct.unpack string')
                exit(0)

            header_size += packet_size
            format_string += current_letter
            header_index_dict[header_dict_field['field']] = index_counter
            if current_letter:
                index_counter += 1

            if header_dict_field['expected'] != '':
                tmpDict = {'startByte': int(header_dict_field['startByte']),
                           'startBit': int(header_dict_field['startBit']),
                           'value': int(header_dict_field['expected'])}
                known_dict_list.append(tmpDict)

            # update continuation variables
            last_size = int(header_dict_field['size'])
            last_bit = int(header_dict_field['startBit'])
            last_byte = int(header_dict_field['startByte'])

        if len(known_dict_list) == 0:
            LOGGER.fatal("No expected values included in the json file for " + csv_dict['packetName'] + " packet!")
            continue  # skip the file for now

        # now the format string has been generated and the known dict has been generated

        # recall that the input variable "data" has the raw data in it

        # find the initial possible syncs
        sync_possible = np.where(data == known_dict_list[0]['value'])[0]
        sync_possible = sync_possible - known_dict_list[0]['startByte']

        for known_dict in known_dict_list[1:-1]:
            sync_possible_test = np.where(data == known_dict['value'])[0] - known_dict['startByte']
            sync_possible = np.intersect1d(sync_possible, sync_possible_test)

        header_size = header_size // 8

        for ind in sync_possible:
            packet_end = header_size + int(csv_dict['length'])
            packet_dict = create_packet_dict(csv_dict, header_size, format_string, data[ind:ind+packet_end], header_index_dict)
            packet_dict_list.append(packet_dict)
    return packet_dict_list


def create_packet_dict(apid_dict, header_size, format_string, data, header_index_dict):
    """
    Creates a dictionary for a packet
    :param apid_dict: dictionary from csv file
    :param header_size: size of the header
    :param format_string: format for unpacking
    :param data: data in the packet
    :param header_index_dict: indicies of header information
    :return: dictionary with packet information
    """
    header_info = extract_header_data(format_string, data, header_size, header_index_dict)
    packet_dict = {'apid': apid_dict['apid'],
                   'headerSize': header_size,
                   'seqCount': header_info['seqCount'],
                   'name': apid_dict['packetName'],
                   'packet_length': apid_dict['length'],
                   'seconds': header_info['seconds'],
                   'data': data}
    return packet_dict


def extract_header_data(format_string, data, header_length, header_index_dict):
    """
    Extracts header information
    :param format_string: unpack format
    :param data: raw data for packet
    :param header_length:  length of the header
    :param header_index_dict: dictionary of header indicies
    :return: dictionary with header information for packet
    """
    header_data = struct.unpack(format_string, data[0:header_length])
    header_info_dict = dict()
    header_info_dict['seconds'] = header_data[header_index_dict['seconds']]
    header_info_dict['subseconds'] = header_data[header_index_dict['subSeconds']]
    header_info_dict['seqCount'] = header_data[header_index_dict['seqCount']]
    return header_info_dict


# ========================== NETCDF FUNCTIONS ===========================================
def createFile(filename):
    """
    Creates netCDF File
    :param filename: name of the file, default extension is .nc
    :return: void
    """
    mainGroup = Dataset(filename, "w", format="NETCDF4")
    time = mainGroup.createDimension("time", None)  # None sets the dimension size to unlimited.
    times = mainGroup.createVariable("time", "f8", ("time",))
    times.setncattr('unit', 'seconds since 2000/001 - 11:59:27')
    """
    TAI Epoch Source:
    Seidelmann, P. K., Ed. (1992). Explanatory Supplement to the Astronomical Almanac. 
        Sausalito, CA: University Science Books. Glossary, s.v. Terrestrial Dynamical Time.
    """
    mainGroup.close()


def get_netcdf_dtype(size, state=''):
    """
    Gets netCDF variable type. States will be stored as ints.
    :param size: size in bits of variable
    :param state: state string. state='' if no state present
    :return:
    """
    # Determine if it's a state or not. If it is, store it as an int.
    if state != '':
        type_str = 'i'
    else:
        type_str = 'f'

    size = int(size) / 8
    if size <= 1 and type_str == 'i':
        size_str = '1'
    elif size <= 2 and type_str == 'i':
        size_str = '2'
    elif size <= 4:
        size_str = '4'
    elif size <= 8:
        size_str = '8'
    else:
        format_str = 'f8'
        LOGGER.warning('Using default f8 value for NetCDF because the size didn\'t match anything expected')
        return format_str

    format_str = type_str + size_str
    return format_str


def get_main_group(filename):
    """
    Retrieves NetCDF main group from given filename. If can't find the filename, makes the file.
    :param filename: name of NetCDF File
    :return: main group object
    """
    LOGGER.info("Opening NetCDF file " + filename)
    if not os.path.isfile(filename):
        LOGGER.warning("Could not find netCDF file " + filename + ", creating it.")
        createFile(filename)
    mainGroup = Dataset(filename, "a", format="NETCDF4")
    return mainGroup


# def direct_add_point(timeIndex, point, value, mainGroup):
#     times = mainGroup.variables['time']
#     # length = len(mainGroup.dimensions['time'])
#     tlm_name = point['name']
#
#     if tlm_name in mainGroup.variables.keys():
#         # If it has, retrieve it.
#         datapt = mainGroup.variables[tlm_name]
#     else:
#         # If not, create it.
#         dtype_string = get_netcdf_dtype(point['size'], state=point['state'])
#         datapt = mainGroup.createVariable(tlm_name, dtype_string, ("time",))
#         datapt.setncattr('unit', point['unit'])
#         datapt.setncattr('state', point['state'])
#         datapt.setncattr('description', point['description'])
#     try:
#         timeIndex = int(timeIndex)
#         datapt[timeIndex] = value
#         times[timeIndex] = timeIndex
#     except OverflowError:
#         LOGGER.warning('Overflow Error on '+point['name']+' with value '+str(value))


def netcdf_add_data(tlm_data, mainGroup):
    """
    This version adds using the TAI time as the insert index
    :param tlm_data:
    :param mainGroup:
    :return:
    """
    times = mainGroup.variables['time']

    for timeIndex, packet in tlm_data.items():
        for tlm_name, value in packet.items():
            if tlm_name not in mainGroup.variables.keys():
                LOGGER.fatal("Something went wrong and could not find variable in NetCDF File...")
                exit(1)

            datapt = mainGroup.variables[tlm_name]
            timeIndex = int(timeIndex)
            datapt[timeIndex] = value
            times[timeIndex] = timeIndex


def netcdf_add_data_2(tlm_data, mainGroup):
    """
    This version adds using the TAI time as the insert index
    :param tlm_data:
    :param mainGroup:
    :return:
    """
    times = mainGroup.variables['time']

    for timeIndex, packet in tlm_data.items():
        length = length = len(mainGroup.dimensions['time'])
        for tlm_name, value in packet.items():
            if tlm_name not in mainGroup.variables.keys():
                LOGGER.fatal("Something went wrong and could not find variable in NetCDF File...")
                exit(1)

            datapt = mainGroup.variables[tlm_name]
            timeIndex = int(timeIndex)
            datapt[length] = value
            times[length] = timeIndex


def write_to_pickle(data, filename):
    """
    writes data to a pickle file with given filename
    :param data: data to write to file
    :param filename: i.e. mydata.pkl
    :return:
    """
    with open('obj/'+filename, 'wb') as f:
        pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)


def find_files(re_string, rootdir):
    rawFiles = []
    for root, directories, filenames in os.walk(rootdir):
        for filename in filenames:
            m = re.search(re_string, filename)
            if m:
                rawFiles.append(os.path.join(root, filename))

    if rawFiles == []:
        LOGGER.warning("Didn't find any raw files in " + rootdir)

    return rawFiles


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
    file_re_pattern = 'bct_\d{4}.*'

    if not TEST:
        rawFiles = find_files(file_re_pattern, CONFIG_INFO['rundirs']['location'])
        mainGroup = get_main_group(CONFIG_INFO['netcdf']['location'])
        processLog = CONFIG_INFO['process_log']['location']
        try:
            fileReadLog = open(processLog, mode='r')
        except PermissionError:
            LOGGER.fatal("Could not get permissions on " + processLog)
            exit(1)
    else:
        LOGGER.info("RUNNING IN TESTING MODE.")
        rawFiles = find_files(file_re_pattern, CONFIG_INFO['rundirs_test']['location'])
        mainGroup = get_main_group(CONFIG_INFO['netcdf_test']['location'])

    for file in rawFiles:
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

        data = extract_tlm_from_packets(csv_info, packets, mainGroup=mainGroup)
        LOGGER.debug("Extracted all the data, adding to NetCDF file . . .")
        netcdf_add_data(data, mainGroup)
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

    mainGroup.close()

    LOGGER.info("Done")

