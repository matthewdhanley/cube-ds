import numpy as np
import struct
from helpers import *
from sband_processing import *


if __name__ == "__main__":
    data = get_tlm_data('test/sband/raw_2018_346_10_50_30')
    sband_packets = extract_sband_vcdus(data)

    for packet in sband_packets:
        output = ' '.join('{:02x}'.format(x) for x in packet[0:30])
        print(output)