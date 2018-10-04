import numpy as np
import struct

def extract_CCSDS_packets(json_info, data):
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
    for top_key in json_info:
        apid_dict = json_info[top_key]
        packet_header = apid_dict['header']

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
        for key in packet_header:

            # Some error checking
            if first_iteration:
                # check to make sure that the header starts at bit/byte 0
                if packet_header[key]['startBit'] != 0 or packet_header[key]['startByte'] != 0:
                    logger.fatal("Header does not start at zero.")
                    exit(0)
                first_iteration = 0

            else:
                # make sure that the fields in the header are not overlappinsg. This will cause problems
                if packet_header[key]['startByte'] == last_byte and packet_header[key]['startBit'] == 0:
                    logger.fatal("There is overlap in the header for "+apid_dict['name'] +
                                 ". This is not currently supported.")
                    exit(0)

                # make sure there are no gaps
                if last_byte * 8 + last_bit + last_size !=\
                        int(packet_header[key]['startBit']) + int(packet_header[key]['startByte']) * 8:
                    logger.fatal("There is a gap in your header for "+apid_dict['name'] +
                                 " at " + key + ". Consider adding \"padding\"")
                    exit(0)

            # this if statement is checking if we are at a new byte or not.
            # if there are bits involved, we need to know so we can do special masking.
            if (int(packet_header[key]['startByte'])*8 + packet_header[key]['size']) // 8 != last_byte:
                processing_bits = 0

            # ASSUMPTION: HEADERS ARE ALL GOING TO BE DNs
            # building a string to use with struct.unpack
            # this should never really need to be altered.
            current_letter = ''
            if packet_header[key]['size'] % 8 != 0:
                if not processing_bits:
                    processing_bits = 1
                    current_letter = 'B'
                else:
                    current_letter = ''
                # todo - write function to unmask bits
                pass
            elif packet_header[key]['size'] == 8:
                current_letter = 'B'
            elif packet_header[key]['size'] == 16:
                current_letter = 'H'
            elif packet_header[key]['size'] == 32:
                current_letter = 'I'
            elif packet_header[key]['size'] == 64:
                current_letter = 'Q'
            else:
                logger.fatal('Issue decoding header sizes into struct.unpack string')
                exit(0)

            header_size += packet_header[key]['size']
            format_string += current_letter
            header_index_dict[key] = index_counter
            if current_letter:
                index_counter += 1

            if 'expected' in packet_header[key]:
                tmpDict = {'startByte': int(packet_header[key]['startByte']),
                           'startBit': int(packet_header[key]['startBit']),
                           'value': int(packet_header[key]['expected'])}
                known_dict_list.append(tmpDict)

            # update continuation variables
            last_size = int(packet_header[key]['size'])
            last_bit = int(packet_header[key]['startBit'])
            last_byte = int(packet_header[key]['startByte'])

        if len(known_dict_list) == 0:
            logger.fatal("No expected values included in the json file for " + apid_dict['name'] + " packet!")
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
            packet_end = header_size + apid_dict['length']
            packet_dict = create_packet_dict(apid_dict, header_size, format_string, data[ind:ind+packet_end], header_index_dict)
            packet_dict_list.append(packet_dict)

    return packet_dict_list


def create_packet_dict(apid_dict, header_size, format_string, data, header_index_dict):

    header_info = extract_header_data(format_string, data, header_size, header_index_dict)
    packet_dict = {'apid': apid_dict['apid'],
                   'headerSize': header_size,
                   'seqCount': header_info['seqCount'],
                   'name': apid_dict['name'],
                   'packet_length': apid_dict['length'],
                   'seconds': header_info['seconds'],
                   'data': data}
    return packet_dict


def extract_header_data(format_string, data, header_length, header_index_dict):
    header_data = struct.unpack(format_string, data[0:header_length])
    header_info_dict = dict()
    header_info_dict['seconds'] = header_data[header_index_dict['seconds']]
    header_info_dict['subseconds'] = header_data[header_index_dict['subSeconds']]
    header_info_dict['seqCount'] = header_data[header_index_dict['seqCount']]
    return header_info_dict
