from cube_ds_2 import *
from pprint import pprint

if __name__ == "__main__":
    data = get_tlm_data('test\\data\\raw_record_2018_341_10_20_44')
    packets = extract_ax25_packets(data)
    packets = strip_ax25(packets, 16)
    packets = stitch_ccsds(packets)
    packets = sort_packets(packets)

    csv_file = CONFIG_INFO['csv']['location']

    # returned a list of dicts
    csv_info = get_csv_info(csv_file)

    for key in packets:
        for a in csv_info:
            if key == a['source'] + a['apid']:
                packets[key]['csv_info'] = a

    data = extract_tlm_from_sorted_packets(packets)
    pprint(data)