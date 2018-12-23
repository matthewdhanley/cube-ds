from config import *
import numpy as np
import pylogger
from ccsds_processing import *

LOGGER = pylogger.get_logger(__name__)


def extract_ax25_packets(data):
    header = np.array(bytearray.fromhex('84 86 A8 40 40 40 60 86 A6 92 9A 40 40 E1 03 F0'))
    header_len = len(header)
    inds = []
    ax25_packets = []

    for x in range(0, len(data-header_len)):
        if np.all(data[x:x+header_len] == header):
            inds.append(x)

    for x in range(0, len(inds)-1):
        ax25_packets.append(data[inds[x]:inds[x+1]])
    return ax25_packets


def strip_ax25(ax25_packets, header_len):
    for i in range(0, len(ax25_packets)):
        ax25_packets[i] = ax25_packets[i][header_len:]
    return ax25_packets


def strip_kiss(packets):
    # KISS_FRAME_ESC 0xDB
    # KISS_TFRAME_END 0xDC
    # KISS_TFRAME_ESC 0xDD
    # KISS_FRAME_END 0xC0
    # KISS_FRAME_DATA 0x00
    for j in range(0, len(packets)):
        len_packet = len(packets[j])
        i = 0
        while i in range(0, len_packet-1):
            if packets[j][i] == 219:  # 0xDB
                if packets[j][i + 1] == 220:  # 0xDB 0xDC
                    packets[j][i] = 220
                    packets[j] = np.delete(packets[j], i + 1)
                    len_packet -= 1
                elif packets[j][i + 1] == 221:  # 0xDB 0xDD
                    packets[j][i] = 221
                    packets[j] = np.delete(packets[j], i + 1)
                    len_packet -= 1
            i += 1
    return packets


def process_ax25_kiss(data, stats=Statistics('none')):
    # KISS file CASE
    header_length = 16
    stats.add_stat("Interpreted as KISS file")
    LOGGER.info("Extracting data from .kss (or SatNOGS) file " + stats.basefile)
    packets = extract_ax25_packets(data)
    stats.add_stat("Extracted " + str(len(packets)) + ' AX.25 packets')
    LOGGER.info("Extracted " + str(len(packets)) + ' AX.25 packets')
    packets = strip_ax25(packets, header_length)
    packets = strip_kiss(packets)
    if CONFIG_INFO['SAVE']['CCSDS_STATS']:
        ccsds_stats(packets, stats.basefile)
    packets = stitch_ccsds_new(packets)
    stats.add_stat("Stitched together " + str(len(packets)) + ' CCSDS Packets')
    LOGGER.info("Stitched together " + str(len(packets)) + ' CCSDS Packets')
    return packets


def process_ax25_raw(data, stats=Statistics('none')):
    # otherwise already been stripped of kiss and stuff
    header_length = 16
    stats.add_stat("Interpreting as stripped KISS file")
    packets = extract_ax25_packets(data)
    stats.add_stat("Found "+str(len(packets))+" AX.25 Packets")
    if DEBUG:
        write_to_pickle(packets, "debug/ax25_packets_" + stats.basefile + ".pickle")

    packets = strip_ax25(packets, header_length)

    if DEBUG:
        write_to_pickle(packets, "debug/ax25_stripped_packets_"+stats.basefile+".pickle")

    if CONFIG_INFO['SAVE']['CCSDS_STATS']:
        ccsds_stats(packets, stats.basefile)

    packets = stitch_ccsds_new(packets)
    stats.add_stat("Stitched together "+str(len(packets)))+" CCSDS Packets"
    if DEBUG:
        write_to_pickle(packets, "debug/ax25_ccsds_packets_"+stats.basefile+".pickle")

    return packets