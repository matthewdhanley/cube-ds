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
    csv_file = CONFIG_INFO['csv']['location']

    # returned a list of dicts
    csv_info = get_csv_info(csv_file)

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

        header_length = 16  # size of ax25 header
        data = get_tlm_data(file)

        if re.search('.*\.kss', file_basename):
            # KISS file CASE
            LOGGER.info("Extracting data from .kss file.")
            packets = extract_ax25_packets(data)
            packets = strip_ax25(packets, header_length)
            packets = strip_kiss(packets)
            if CONFIG_INFO['SAVE']['CCSDS_STATS']:
                ccsds_stats(packets, file_basename)
            packets = stitch_ccsds_new(packets)

        elif re.search('.*sband.*', file_basename):
            # SBAND CASE
            LOGGER.info("Extracting SBAND data from "+file_basename)

            packets = extract_sband_vcdus(data)

            if DEBUG:
                write_to_pickle(packets, 'debug/vcdu_raw_packets_'+file_basename+'.pickle')

            if CONFIG_INFO['SAVE']['VCDU_STATS']:
                vcdu_stats(packets, file_basename)

            packets = extract_ccsds_packets(packets)

            if CONFIG_INFO['SAVE']['CCSDS_STATS']:
                ccsds_stats(packets, file_basename)

            if DEBUG:
                write_to_pickle(packets, "debug/vcdu_ccsds_packets_"+file_basename+".pickle")

        else:
            # otherwise already been stripped of kiss and stuff
            packets = extract_ax25_packets(data)
            if DEBUG:
                write_to_pickle(packets, "debug/ax25_packets_" + file_basename + ".pickle")

            packets = strip_ax25(packets, header_length)
            ccsds_stats(packets, file_basename)
            if DEBUG:
                write_to_pickle(packets, "debug/ax25_stripped_packets_"+file_basename+".pickle")

            if CONFIG_INFO['SAVE']['CCSDS_STATS']:
                ccsds_stats(packets, file_basename)

            packets = stitch_ccsds_new(packets)

            if DEBUG:
                write_to_pickle(packets, "debug/ax25_ccsds_packets_"+file_basename+".pickle")

        packets = sort_packets(packets)

        if DEBUG:
            write_to_pickle(packets, "debug/sorted_packets_"+file_basename+".pickle")

        for key in packets:
            for a in csv_info:
                if key == a['source'] + a['apid']:
                    packets[key]['csv_info'] = a

        out_data = extract_tlm_from_sorted_packets(packets)

        if int(CONFIG_INFO['SAVE']['INDIVIDUAL_CSV']):
            df = tlm_to_df(out_data, CONFIG_INFO['SAVE']['KEY'])
            tlm_df_to_csv(df, file_basename+'_summary.csv', CONFIG_INFO['SAVE']['KEY'])

        if out_data:
            save_telemetry(out_data)
        else:
            LOGGER.info("No data found, trying other approach")
            packets = find_ccsds_packets(data)
            LOGGER.info("Found "+str(len(packets))+" potential packets")

            if CONFIG_INFO['SAVE']['CCSDS_STATS']:
                ccsds_stats(packets, file_basename)

            packets = sort_packets(packets)

            for key in packets:
                for a in csv_info:
                    if key == a['source'] + a['apid']:
                        packets[key]['csv_info'] = a
            out_data = extract_tlm_from_sorted_packets(packets)
            if int(CONFIG_INFO['SAVE']['INDIVIDUAL_CSV']):
                df = tlm_to_df(out_data, CONFIG_INFO['SAVE']['KEY'])
                tlm_df_to_csv(df, file_basename + '_summary.csv', CONFIG_INFO['SAVE']['KEY'])

            if out_data:
                save_telemetry(out_data)
            else:
                LOGGER.warning("No data found in "+file_basename)
                if not TEST:
                    # append file to processed file log
                    file_log = open(process_log, mode='a')
                    file_log.write(file + '\n')
                    file_log.close()
                continue

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

    LOGGER.info("Data Processing Complete!")

