
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
        print(packet['seconds'])

        # check to make sure that the time is within a valid range
        if not MIN_TIME < packet_dt < MAX_TIME:
            # log the warning and continue if out of range
            LOGGER.warning("Found packet with bogus time of " + packet_dt.strftime("%Y-%m-%d %H:%M:%S") + ". Trying other epoch.")
            packet_dt = get_tlm_time_dt(packet['seconds'], epoch=CCSDS_EPOCH)
            if not MIN_TIME < packet_dt < MAX_TIME:
                LOGGER.warning("CCSDS Epoch Did not work")
                # continue
            LOGGER.info("CCSDS Epoch did work")
            packet['seconds'] = int((packet_dt - TAI_EPOCH).total_seconds())
            LOGGER.debug(str(packet['seconds']))

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
            if point['dtype'] != 'char':
                try:
                    tlm_value = struct.unpack(unpack_data_format, tlmData)[0] * conversion
                except struct.error:
                    # not extracting the right amount of data. Print some debug information and move on
                    # LOGGER.warning("Packet ended unexpectedly.")
                    pprint(point)
                    pprint(tlmData)
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

            if point['name'] == 'bct_tai_seconds':
                new_key = int(tlm_value)
                LOGGER.debug("new key: "+str(new_key))

            # # if mainGroup is supplied to the function call, add point to netcdf file
            if mainGroup != '':
                if point['name'] not in mainGroup.variables.keys():
                    # If not, create it.
                    dtype_string = get_netcdf_dtype(point['size'], state=point['state'])
                    datapt = mainGroup.createVariable(point['name'], dtype_string, ("time",))
                    datapt.setncattr('unit', point['unit'])
                    datapt.setncattr('state', point['state'])
                    datapt.setncattr('description', point['description'])

            new_key = data_struct[packet_key]['bct_tai_seconds']
        data_struct[new_key] = data_struct[packet_key]
        del data_struct[packet_key]
    return data_struct



#
# def extract_CCSDS_packets(csv_info, data):
#     """
#     This function will go through raw data and extract raw packets.
#     ASSUMPTIONS:
#     Data is not in a nice format, will need to find the beginning of frames.
#     However, frames are continuous. Any AX25 has been dealt with.
#     :param data: Raw data to find the packets in
#     :param apids: list of apids to look for
#     :return: dictionary? of packets
#     """
#
#     # loop through apids and find potential frames
#     packet_dict_list = []
#     for csv_dict in csv_info:
#
#         header_file = csv_dict['headerFile']
#         # LOGGER.debug("looking at "+header_file)
#         header_dict_list = get_header_dict(header_file)
#
#         # apid_dict = csv_info[top_key]
#
#         known_dict_list = []  # keeps track of how many fields that we know we can use to sync up the packet
#
#         # loop through fields in the header and generate an unpack string
#         # init some variables to keep track of header continuity
#         last_byte = 0
#         last_bit = 0
#         last_size = 0
#         header_size = 0
#         index_counter = 0
#
#         header_index_dict = {}
#
#         # flags
#         first_iteration = 1
#         processing_bits = 0
#
#         # init the format string holder
#         # the '>' is specifying big endian
#         format_string = '>'
#         for header_dict_field in header_dict_list:
#
#             # Some error checking
#             if first_iteration:
#                 # check to make sure that the header starts at bit/byte 0
#                 if int(header_dict_field['startBit']) != 0 or int(header_dict_field['startByte']) != 0:
#                     LOGGER.fatal("Header does not start at zero.")
#                     exit(-1)
#                 first_iteration = 0
#
#             else:
#                 # make sure that the fields in the header are not overlappinsg. This will cause problems
#                 if int(header_dict_field['startByte']) == int(last_byte and header_dict_field['startBit']) == 0:
#                     LOGGER.fatal("There is overlap in the header for " + csv_dict['packetName'] +
#                                  ". This is not currently supported.")
#                     exit(-1)
#
#                 # make sure there are no gaps
#                 if last_byte * 8 + last_bit + last_size !=\
#                         int(header_dict_field['startBit']) + int(header_dict_field['startByte']) * 8:
#                     LOGGER.fatal("There is a gap in your header for " + csv_dict['packetName'] +
#                                  " at " + header_dict_field['field'] + ". Consider adding \"padding\"")
#                     exit(-1)
#
#             # this if statement is checking if we are at a new byte or not.
#             # if there are bits involved, we need to know so we can do special masking.
#             if (int(header_dict_field['startByte'])*8 + int(header_dict_field['size'])) // 8 != last_byte:
#                 processing_bits = 0
#
#             # ASSUMPTION: HEADERS ARE ALL GOING TO BE DNs
#             # building a string to use with struct.unpack
#             # this should never really need to be altered.
#             current_letter = ''
#             packet_size = int(header_dict_field['size'])
#             if packet_size % 8 != 0:
#                 if not processing_bits:
#                     processing_bits = 1
#                     current_letter = 'B'
#                 else:
#                     current_letter = ''
#                 pass
#                 # todo - write function to unmask bits
#             elif packet_size == 8:
#                 current_letter = 'B'
#             elif packet_size == 16:
#                 current_letter = 'H'
#             elif packet_size == 32:
#                 current_letter = 'I'
#             elif packet_size == 64:
#                 current_letter = 'Q'
#             else:
#                 LOGGER.fatal('Issue decoding header sizes into struct.unpack string')
#                 exit(0)
#
#             header_size += packet_size
#             format_string += current_letter
#             try:
#                 header_index_dict[header_dict_field['field']] = index_counter
#             except KeyError:
#                 LOGGER.fatal(pprint(header_dict_field))
#                 exit(-1)
#             if current_letter:
#                 index_counter += 1
#
#             if header_dict_field['expected'] != '':
#                 tmpDict = {'startByte': int(header_dict_field['startByte']),
#                            'startBit': int(header_dict_field['startBit']),
#                            'value': int(header_dict_field['expected'])}
#                 known_dict_list.append(tmpDict)
#
#             # update continuation variables
#             last_size = int(header_dict_field['size'])
#             last_bit = int(header_dict_field['startBit'])
#             last_byte = int(header_dict_field['startByte'])
#
#         if len(known_dict_list) == 0:
#             LOGGER.fatal("No expected values included in the json file for " + csv_dict['packetName'] + " packet!")
#             continue  # skip the file for now
#
#         # now the format string has been generated and the known dict has been generated
#
#         # recall that the input variable "data" has the raw data in it
#
#         # find the initial possible syncs
#         sync_possible = np.where(data == known_dict_list[0]['value'])[0]
#
#         sync_possible = sync_possible - known_dict_list[0]['startByte']
#
#         for known_dict in known_dict_list[1:-1]:
#             sync_possible_test = np.where(data == known_dict['value'])[0] - known_dict['startByte']
#             sync_possible = np.intersect1d(sync_possible, sync_possible_test)
#
#         header_size = header_size // 8
#
#         for ind in sync_possible:
#             packet_end = header_size + int(csv_dict['length'])
#             packet_dict = create_packet_dict(csv_dict, header_size, format_string, data[ind:ind+packet_end], header_index_dict)
#             packet_dict_list.append(packet_dict)
#
#             if TEST:
#                 with open('test/'+str(ind)+'.dat', mode='wb') as f:
#                     pprint(packet_dict)
#                     f.write(data[ind:ind+packet_end])
#                     f.close()
#
#     return packet_dict_list




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

