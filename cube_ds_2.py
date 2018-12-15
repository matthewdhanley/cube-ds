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
from vcdu_processing import *

LOGGER = pylogger.get_logger(__name__)


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
    file_re_patterns = ['^raw.*', '.*\.kss', '^sband.*']

    if not TEST:
        rawFiles = find_files(file_re_patterns, CONFIG_INFO['rundirs']['location'])
        process_log = CONFIG_INFO['process_log']['location']
        try:
            file_read_log = open(process_log, mode='r')
            logFiles = []
            for file in file_read_log:
                logFiles.append(file.rstrip())
        except PermissionError:
            LOGGER.fatal("Could not get permissions on " + process_log)
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
            for line in logFiles:
                # LOGGER.debug(line+' == '+file+' ?????')
                if file.rstrip() == line.rstrip():
                    foundFlag = 1
            if foundFlag:
                continue
            LOGGER.info("Processing "+file)

        header_length = 16  # size of ax25 header
        data = get_tlm_data(file)

        if re.search('.*\.kss', file):
            # KISS file CASE
            packets = extract_ax25_packets(data)
            packets = strip_ax25(packets, header_length)
            packets = strip_kiss(packets)
            packets = stitch_ccsds(packets)
        elif re.search('.*sband.*', file):
            # SBAND CASE
            packets = extract_sband_vcdus(data)
            packets = extract_ccsds_packets(packets)
        else:
            # otherwise already been stripped of kiss and stuff
            packets = extract_ax25_packets(data)
            packets = strip_ax25(packets, header_length)
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
            file_log = open(process_log, mode='a')
            file_log.write(file + '\n')
            file_log.close()

    if len(tlm) < 1:
        LOGGER.info("No new files to process.")
        exit(0)

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
        file_read_log.close()

    LOGGER.info("Data Processing Complete!")

