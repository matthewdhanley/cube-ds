from config import *
from ccsds_processing import *
from helpers import *
from packet_processing import *


def special_processing(data, stats=Statistics('none')):
    stats.reset()
    packets = find_ccsds_packets(data)

    LOGGER.info("Found "+str(len(packets))+" potential packets")
    stats.add_stat("Found "+str(len(packets))+" potential packets")

    if CONFIG_INFO['SAVE']['CCSDS_STATS']:
        ccsds_stats(packets, stats.basefile)

    packets = sort_packets(packets)
    stats.add_stat("Extracted " + str(len(packets.keys())) + " unique APIDs")

    packets = assign_csv_info(packets)

    out_data = extract_tlm_from_sorted_packets(packets, stats=stats)
    stats.add_stat("Extracted data from "+str(len(out_data))+" full CCSDS packets")
    return out_data