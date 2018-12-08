import numpy as np
import pylogger

pylogger.get_logger()

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

    return(ax25_packets)


def strip_ax25(ax25_packets, header_len):
    for i in range(0, len(ax25_packets)):
        ax25_packets[i] = ax25_packets[i][header_len:]
    return ax25_packets