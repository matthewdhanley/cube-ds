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
from vcdu_processing import *
from config import *
from csv_out import *
from postgresql import *
from idl_out import *
from save_data import *
from cleaning import *
from slack import *
from statistics import *
from satnogs import *
from special_processing import *

LOGGER = pylogger.get_logger(__name__)

if __name__ == "__main__":
    # set up LOGGER.
    LOGGER.info("========================= Started ==========================")

    # Parsing command line arguments
    parser = argparse.ArgumentParser(description='Command Line Parser')

    parser.add_argument('-t', '--test', action="store_true", help="If present, program will be run in test mode")
    parser.add_argument('-d', '--debug', action="store_true", help="If present, program will be run in debug mode")

    LOGGER.debug("Parsing for any command line arguements")
    args = parser.parse_args()  # test bool will be stored in args.test

    if args.test:
        TEST = 1

    if args.debug:
        DEBUG = 1

    LOGGER.debug("reading in CSV file")

    # how the raw files are named
    file_re_patterns = ['^raw.*', '.*\.kss', '.*sband.*']
    file_exclude_patterns = ['.*flatsat.*']

    if not TEST:
        rawFiles = find_files(file_re_patterns,
                              CONFIG_INFO['rundirs']['location'],
                              exclude=file_exclude_patterns)

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
        rawFiles = find_files(file_re_patterns,
                              CONFIG_INFO['rundirs_test']['location'],
                              exclude=file_exclude_patterns)

        LOGGER.info("Rundirs: "+CONFIG_INFO['rundirs_test']['location'])
        LOGGER.info("Found "+str(len(rawFiles))+" in the Rundirs folder.")

    tlm = []

    for file in rawFiles:
        file_basename = os.path.split(file)[-1]
        if not TEST:
            # don't process file twice.
            foundFlag = 0
            for line in logFiles:
                if file.rstrip() == line.rstrip():
                    foundFlag = 1
            if foundFlag:
                continue
            LOGGER.info("Processing "+file)

        file_stats = Statistics(file_basename)  # used to log info about the file
        header_length = 16  # size of ax25 header
        data = get_tlm_data(file)

        if re.search('.*\.kss', file_basename):
            packets = process_ax25_kiss(data, stats=file_stats)

        elif re.search('.*sband.*', file_basename):
            packets = process_vcdu(data, stats=file_stats)

        else:
            packets = process_ax25_raw(data, stats=file_stats)

        packets = sort_packets(packets)
        file_stats.add_stat("Extracted "+str(len(packets.keys()))+" Unique APIDs")

        if DEBUG:
            write_to_pickle(packets, "debug/sorted_packets_"+file_basename+".pickle")

        packets = assign_csv_info(packets)

        out_data = extract_tlm_from_sorted_packets(packets, stats=file_stats)
        file_stats.add_stat("Extracted data from "+str(len(out_data))+" full CCSDS packets")

        if not out_data:
            LOGGER.info("No data found, trying other approach")
            out_data = special_processing(data, stats=file_stats)

            if not out_data:
                LOGGER.warning("No data found in "+file_basename)
                if not TEST:
                    # append file to processed file log
                    file_log = open(process_log, mode='a')
                    file_log.write(file + '\n')
                    file_log.close()
                continue

        out_data_df = tlm_to_df(out_data, CONFIG_INFO['SAVE']['KEY'])

        if int(CONFIG_INFO['CLEANING']['CLEAN_DATA']):
            out_data_df = clean_times(out_data_df, CONFIG_INFO['SAVE']['KEY'], utc_to_tai, stats=file_stats)

        if int(CONFIG_INFO['SAVE']['INDIVIDUAL_CSV']):
            tlm_df_to_csv(out_data_df, file_basename+'_summary.csv', CONFIG_INFO['SAVE']['KEY'])
            file_stats.add_stat("Data saved to individual csv in summaries/"+file_basename+'_summary.csv')

        save_telemetry(out_data_df, stats=file_stats)

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

    if int(CONFIG_INFO['SATNOGS']['SATNOGS_DATA']):
        get_satnogs_data()

    if len(tlm) < 1:
        LOGGER.info("No new files to process.")

    LOGGER.info("Data Processing Complete!")

