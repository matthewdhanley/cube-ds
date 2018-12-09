from config import *
from helpers import *
LOGGER = pylogger.get_logger('packet processing')


def extract_key(extracted_tlm_data, key):
    """
    Gets key from tlm data
    :param extracted_tlm_data: dictionary with keys as tlm strings and values as tlm values
    :param key: string representing key, I use bct_tai_seconds
    :return:
    """
    try:
        extracted_key = extracted_tlm_data[key]
    except KeyError:
        LOGGER.critical("Could not find tlm point named "+key+" to use for key.")
        return -1
    return int(extracted_key)


def extract_tlm_from_sorted_packets(packets):
    """
    Extracts telemetry from packets that are sorted in a dictionary
    :param packets: Packet dictionary. The key is 'source+apid', i.e. '863' would be source 8, apid 63
    :return: gia
    """
    out_data = []
    for key in packets:
        csv_info = packets[key]['csv_info']
        points_file = csv_info['pointsFile']

        # if the file wasn't found, send message to user and exit
        if points_file == '':
            LOGGER.error('error finding points definitions for packet ' + csv_info['packetName'])
            exit(0)

        # extract the telemetry points from the file
        tlm_points = get_tlm_points(points_file)
        for data in packets[key]['raw_packets']:
            if not len(data):
                continue
            out_data.append(extract_data(data, tlm_points))
    if len(out_data) == 0:
        LOGGER.warning("Did not extract any data . . .")
    return out_data


def extract_data(data, tlm_points):
    extracted_data = {}
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

        # grab the header length from the packet todo - fix
        # header_length = int(packet['headerSize'])
        header_length = 12

        # get the relavent data from the packet
        tlmData = data[header_length + startByte:header_length + startByte + tlm_length // 8]

        # generate a format string for struct.unpack
        unpack_data_format = get_unpack_format(dtype, tlm_length)
        # try to unpack the data (if it's not a char, chars are having issues?)
        # ALSO CONVERT TO THE EU
        if point['dtype'] != 'char':
            try:
                tlm_value = struct.unpack(unpack_data_format, tlmData)[0] * conversion
            except struct.error:
                # not extracting the right amount of data. Print some debug information and move on
                LOGGER.warning("Packet ended unexpectedly.")
                continue
            except TypeError as e:
                # had an issue with types. Print debug info and exit. This is a more serious issue.
                print(point)
                print(tlm_value)
                print(e)
                exit(-1)

        # index into the struct and save the value for the tlm point
        extracted_data[point['name']] = tlm_value


        # todo - move to netcdf.py
        # # # if mainGroup is supplied to the function call, add point to netcdf file
        # if mainGroup != '':
        #     if point['name'] not in mainGroup.variables.keys():
        #         # If not, create it.
        #         dtype_string = get_netcdf_dtype(point['size'], state=point['state'])
        #         datapt = mainGroup.createVariable(point['name'], dtype_string, ("time",))
        #         datapt.setncattr('unit', point['unit'])
        #         datapt.setncattr('state', point['state'])
        #         datapt.setncattr('description', point['description'])
    # pprint.pprint(extracted_data['bct_battery_voltage'])
    return extracted_data


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