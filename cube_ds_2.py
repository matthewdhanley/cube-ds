__author__ = "Matthew Hanley"
__email__ = "mattdhanley@gmail.com"

from config import *
import argparse
from helpers import *
from packet_processing import *
from netcdf import *
from ax25_processing import *
from ccsds_processing import *
from pylogger import *
from csv_out import *
from postgresql import *
from idl_out import *


if __name__ == "__main__":
    # set up LOGGER.
    LOGGER.info("========================= Started ==========================")

    # Parsing command line arguments
    parser = argparse.ArgumentParser(description='Command Line Parser')

    parser.add_argument('-t', '--test', action="store_true", help="If present, program will be run in test mode")
    args = parser.parse_args()  # test bool will be stored in args.test

    if args.test:
        TEST = 1

    LOGGER.debug("reading in CSV file")
    csv_file = CONFIG_INFO['csv']['location']

    # returned a list of dicts
    csv_info = get_csv_info(csv_file)

    # how the raw files are named
    # file_re_pattern = '^bct_\d{4}.*'
    file_re_patterns = ['^raw.*', '.*\.kss']

    if not TEST:
        rawFiles = find_files(file_re_patterns, CONFIG_INFO['rundirs']['location'])
        processLog = CONFIG_INFO['process_log']['location']
        try:
            fileReadLog = open(processLog, mode='r')
        except PermissionError:
            LOGGER.fatal("Could not get permissions on " + processLog)
            exit(1)
    else:
        LOGGER.info("RUNNING IN TESTING MODE.")
        rawFiles = find_files(file_re_patterns, CONFIG_INFO['rundirs_test']['location'])
        LOGGER.info("Rundirs: "+CONFIG_INFO['rundirs_test']['location'])
        LOGGER.info("Found "+str(len(rawFiles))+" in the Rundirs folder.")

    tlm = []

    for file in rawFiles:
        if not TEST:
            # don't process file twice.
            foundFlag = 0
            for line in fileReadLog:
                if line.rstrip() == file:
                    foundFlag = 1
            if foundFlag:
                continue
        LOGGER.info("Processing "+file)

        header_length = 16  # size of ax25 header
        data = get_tlm_data(file)
        packets = extract_ax25_packets(data)
        packets = strip_ax25(packets, header_length)
        packets = strip_kiss(packets)
        packets = stitch_ccsds(packets)
        packets = sort_packets(packets)

        for key in packets:
            for a in csv_info:
                if key == a['source'] + a['apid']:
                    packets[key]['csv_info'] = a

        out_data = extract_tlm_from_sorted_packets(packets)
        for d in out_data:
            tlm.append(d)

        # Clean up some variables
        del data
        del packets
        del out_data

        if not TEST:
            # append file to processed file log
            fileLog = open(processLog, mode='a')
            fileLog.write(file+'\n')
            fileLog.close()

    if int(CONFIG_INFO['SAVE']['CSV']):
        LOGGER.info("Saving telemetry to "+CONFIG_INFO['SAVE']['CSV_FILE'])
        df = tlm_to_df(tlm, CONFIG_INFO['SAVE']['KEY'])
        tlm_df_to_csv(df, CONFIG_INFO['SAVE']['CSV_FILE'], CONFIG_INFO['SAVE']['KEY'],
                      pass_summary=int(CONFIG_INFO['SAVE']['SUMMARY_CSV']))

    if int(CONFIG_INFO['SAVE']['NETCDF']):
        LOGGER.info("Saving telemetry to "+CONFIG_INFO['SAVE']['NETCDF_FILE'])
        save_to_netcdf(tlm, CONFIG_INFO['SAVE']['NETCDF_FILE'], index_key=CONFIG_INFO['SAVE']['KEY'])

    if int(CONFIG_INFO['SAVE']['POSTGRESQL']):
        LOGGER.info("Saving telemetry to database . . .")
        df = tlm_to_df(tlm, CONFIG_INFO['SAVE']['KEY'])
        add_df_to_db(df, CONFIG_INFO['SAVE']['KEY'],
                  CONFIG_INFO['DB']['DBNAME'],
                  CONFIG_INFO['DB']['USER'],
                  CONFIG_INFO['DB']['PASSWORD'],
                  CONFIG_INFO['DB']['HOST'],
                  CONFIG_INFO['DB']['PORT'])

    if int(CONFIG_INFO['SAVE']['IDL']):
        df = tlm_to_df(tlm, CONFIG_INFO['SAVE']['KEY'])
        df_to_dict(df, CONFIG_INFO['SAVE']['KEY'])

    if not TEST:
        LOGGER.debug("Closed file read log")
        fileReadLog.close()

    LOGGER.info("Data Processing Complete!")

