from cube_ds_2 import *

if __name__ == "__main__":
    data = get_tlm_data('test/sband/raw_2018_346_10_50_30')
    packets = extract_sband_vcdus(data)
    packets = extract_ccsds_packets(packets)
    packets = sort_packets(packets)

    csv_file = CONFIG_INFO['csv']['location']

    # returned a list of dicts
    csv_info = get_csv_info(csv_file)

    for key in packets:
        for a in csv_info:
            if key == a['source'] + a['apid']:
                packets[key]['csv_info'] = a

    out_data = extract_tlm_from_sorted_packets(packets)
    for data in out_data:
        print(data['bct_battery_voltage'])
    print('done')
