from config import *
from helpers import *
LOGGER = pylogger.get_logger('root')


def tlm_to_csv(data, file_name, time_key=''):
    LOGGER.info("writing to file "+file_name)
    if len(data) == 0:
        LOGGER.error("No data found to write to CSV")
        return(1)
    num_headers = len(data[0].values())
    if time_key:
        num_headers += 1
    if not os.path.exists(file_name):
        handle = open(file_name, 'a')
        csv_f = csv.writer(handle, delimiter=',', lineterminator='\n')
        if time_key:
            headers = ['UTC'] + [x for x in data[0]]
        else:
            headers = [x for x in data[0]]
        csv_f.writerow(headers)
    else:
        handle = open(file_name, 'a')
        csv_f = csv.writer(handle, delimiter=',', lineterminator='\n')

    for d in data:
        if time_key:
            time = tai_to_utc(d[time_key])
            row = [time] + [x for x in d.values()]
        else:
            row = [x for x in d.values()]

        if len(row) < num_headers:
            LOGGER.warning("Found a frame that is not full. Skipping writing it to CSV.")
        elif len(row) > num_headers:
            LOGGER.critical("More entries in the extracted telemetry than CSV errors")
            return 1
        else:
            csv_f.writerow(row)
    handle.close()
    return 0
