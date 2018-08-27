import json
import sys, os
import datetime as dt
import re
import logging, logging.config
from cube_plot import convert_tlm_time, make_time_string, time_string_to_dt
from cube_ds import get_logger, CONFIG_FILE
import configparser

# GLOBALS
TAI_EPOCH = dt.datetime(2000,1,1,11,59,27)


def get_all_files(config):
    jsonFiles = []
    for root, directories, filenames in os.walk(config['telemetry']['location']):
        for filename in filenames:
            m = re.search('\d{4}.*\.json', filename)
            if m:
                jsonFiles.append(os.path.join(root, filename))
    return jsonFiles


def get_datetime(file):
    times = []
    with open(file, 'r') as f:
        # load the json data
        jsonData = json.load(f)
        # create list of values and time
        [times.append(x['t']) for x in jsonData]
    # convert times to datetime objects
    times = convert_tlm_time(times)
    return times


def fix_times(file):
    times = get_datetime(file)
    timeStamp = get_time_string(file)

    diffSeconds = dt.timedelta(times[0], timeStamp)
    print(diffSeconds.total_seconds())


def get_time_string(file):
    m = re.search('(\d{4})_(\d{1,3})_(\d{1,2})_(\d{1,2})_(\d{1,2})\.json', file)
    if not m:
        logger.warning("Filename: " + file + " does not match format")
        exit(0)

    # extract the time fields
    try:
        year = m.group(1)
        doy = m.group(2)
        hour = m.group(3)
        minute = m.group(4)
        second = m.group(5)
    except IndexError:
        # if for some reason a filed is missing, present a warning and continue on
        logger.warning("Problem parsing filename: " + file)
        exit(0)

    # generate datetime object from file time
    fileTimeString = make_time_string(year, doy, hour, minute, second)
    dtFile = time_string_to_dt(fileTimeString)
    return dtFile




def main():
    global logger
    logger = get_logger()

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)

    files = get_all_files(config)
    for file in files:
        fix_times(file)






if __name__ == "__main__":
    main()