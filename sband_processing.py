import numpy as np
from config import *
from helpers import *
from ccsds_processing import *
import pylogger

LOGGER = pylogger.get_logger(__name__)


def extract_sband_vcdus(data):
    header_length = int(CONFIG_INFO['SBAND']['VCDU_LENGTH'])
    i = 0
    sband_packets = []
    while i + header_length < len(data):
        sband_packets.append(data[i:i+header_length])
        i += header_length
        # print(i)

    return sband_packets


def extract_packet_header_pointer(packet):
    # pointer_data_chunk = struct.unpack('>H', packet[4:6])
    header_bytes = bytes(packet[4:6])
    pointer = extract_bits_from_bytes(header_bytes, 5, 11)
    b_list = pointer.tolist()
    mystring = ''
    for s in b_list:
        if s:
            mystring += '1'
        else:
            mystring += '0'
    b = int(mystring, 2)
    return b


def extract_vcdu_header(packet):
    out_dict = {
        "header": packet[0:2],
        "vc_frame_count": packet[3],
        "packet_pointer": extract_packet_header_pointer(packet)
    }
    # don't care about master frame count
    return out_dict


def extract_ccsds_packets(packets):
    header_len = 6
    ccsds_packets = []
    for packet in packets:
        # print(packet[0:7])
        vcdu_header = extract_vcdu_header(packet)
        if vcdu_header['header'][0] != 0 or vcdu_header['header'][1] != 16:
            continue
        ccsds_start = header_len + vcdu_header['packet_pointer']
        ccsds_header = extract_CCSDS_header(packet[ccsds_start:ccsds_start + 14])

        while ccsds_start + ccsds_header['length'] + 12 < len(packet):

            new_packet = packet[ccsds_start:ccsds_start + ccsds_header['length']+12]
            print(len(new_packet))
            ccsds_packets.append(new_packet)
            ccsds_start += ccsds_header['length'] + 12
            print(ccsds_header['length'])
            ccsds_header = extract_CCSDS_header(packet[ccsds_start:ccsds_start + 14])

    return ccsds_packets