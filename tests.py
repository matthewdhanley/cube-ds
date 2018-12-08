from cube_ds_2 import *
from pprint import pprint

if __name__ == "__main__":
    data = get_tlm_data('C:\\csim\\Rundirs\\2018_341_22_38_40\\raw_record_2018_341_22_46_13')
    packets = extract_ax25_packets(data)
    packets = strip_ax25(packets, 16)
    packets = stitch_ccsds(packets)
    for packet in packets:
        print(packet[0:40])
    packets = sort_packets(packets)

    csv_file = CONFIG_INFO['csv']['location']

    # returned a list of dicts
    csv_info = get_csv_info(csv_file)

    for key in packets:
        for a in csv_info:
            if key == a['source'] + a['apid']:
                packets[key]['csv_info'] = a

    extract_tlm_from_sorted_packets(packets)
