from config import *
import requests
from postgresql import *
from ax25_processing import *
from ccsds_processing import *
from packet_processing import *
from cleaning import *
from csv_out import *
from save_data import *


NETWORK_BASE_URL = 'https://network.satnogs.org'
DB_BASE_URL = 'https://db.satnogs.org'
NORAD = 99918  # norad id as it apperas on satnogs


def get_paginated_endpoint(url, max_entries=None):
    r = requests.get(url=url)
    r.raise_for_status()

    data = r.json()

    while 'next' in r.links and (not max_entries or len(data) < max_entries):
        next_page_url = r.links['next']['url']

        r = requests.get(url=next_page_url)
        r.raise_for_status()

        data.extend(r.json())

    return data


def fetch_observation_data_from_id(norad_id, start, end):
    # Get all observations of the satellite
    # with the given `norad_id` in the given timeframe
    # https://network.satnogs.org/api/observations/?satellite__norad_cat_id=25544&start=2018-06-10T00:00&end=2018-06-15T00:00

    query_str = '{}/api/observations/' \
                '?satellite__norad_cat_id={}&start={}&end={}'

    url = query_str.format(NETWORK_BASE_URL,
                           norad_id,
                           start.isoformat(),
                           end.isoformat())

    observations = get_paginated_endpoint(url)

    # Current prod is broken and can't filter on NORAD ID correctly,
    # use client-side filtering instead
    observations = list(observation for observation in observations
                        if observation['demoddata'])

    return observations


def satnogs_date_to_dt(date):
    """
    Converts satnogs response date to dt object
    :param date: date string w/ format %Y-%m-%dT%H:%M:%SZ
    :return: datetime object representation of input string
    """
    return dt.datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")


def get_min_satnogs_date(response_json):
    """
    Gets minimum date from satnogs json request response
    :param response_json: json response
    :return: minimum date in datetime object
    """
    dates = [satnogs_date_to_dt(r['timestamp']) for r in response_json]
    return min(dates)


def create_satnogs_db(conn):
    """
    Creates table for SATNOGS database
    :param conn: database connection as defined by DB section in config file
    :return: void
    """
    LOGGER.debug("Creating Satnogs Database Table . . .")
    cmd = """CREATE TABLE IF NOT EXISTS satnogs( 
        t INTEGER NOT NULL, 
        mnemonic VARCHAR,
        observation_t TIMESTAMP,
        observer VARCHAR,
        tlm_val float NOT NULL,
        PRIMARY KEY (t, mnemonic, observer));"""

    cur = conn.cursor()
    cur.execute(cmd)
    cur.close()


def get_satnogs_data(csv_info):
    """
    Main driver for satnogs data processing
    :param csv_info: csv_info dict as returned by helpers.get_csv_info
    :return: nothing.
    """
    LOGGER.info("Doing SatNOGS data ingest and processing")
    data = get_paginated_endpoint('https://db.satnogs.org/api/telemetry/?satellite=99918')
    process_satnogs_data(data, csv_info)


def process_satnogs_data(data, csv_info):
    """
    Strips telemetry from SatNOGS data and saves it
    :param data: SatNOGS api json response
    :param csv_info: csv_info dict as returned by helpers.get_csv_info
    :return: nothing
    """
    frames_by_observer = {}
    LOGGER.info("sorting SatNOGS data . . .")
    for d in data:
        frame = d['frame']
        observer = d['observer']
        t = satnogs_date_to_dt(d['timestamp'])
        if observer not in frames_by_observer.keys():
            frames_by_observer[observer] = {}
            frames_by_observer[observer]['data'] = np.array(bytearray.fromhex(frame), dtype='>B')
            frames_by_observer[observer]['timestamp'] = t
        else:
            frames_by_observer[observer]['data'] = \
                np.append(frames_by_observer[observer]['data'], np.array(bytearray.fromhex(frame), dtype='>B'))
            if t > frames_by_observer[observer]['timestamp']:
                frames_by_observer[observer]['timestamp'] = t

    for key in frames_by_observer:
        file_basename = key+'_'+dt.datetime.now().strftime("%y_%j_%H_%M_SatNOGS")
        stats = Statistics(file_basename)
        stats.add_stat("SatNOGS Observer: "+key)
        packets = process_ax25_kiss(frames_by_observer[key]['data'], stats=stats)
        LOGGER.info("Found "+str(len(packets))+" potential packets from observer "+key)
        packets = sort_packets(packets)

        for p_key in packets:
            for a in csv_info:
                if p_key == a['source'] + a['apid']:
                    packets[p_key]['csv_info'] = a

        out_data = extract_tlm_from_sorted_packets(packets, stats=stats)

        if not out_data:
            LOGGER.info(key + " did not find any good frames.")
            continue
        stats.add_stat("Extracted data from " + str(len(out_data)) + " full CCSDS packets")
        out_data_df = tlm_to_df(out_data, CONFIG_INFO['SAVE']['KEY'])
        if int(CONFIG_INFO['CLEANING']['CLEAN_DATA']):
            out_data_df = clean_times(out_data_df, CONFIG_INFO['SAVE']['KEY'], utc_to_tai, stats=stats)

        if int(CONFIG_INFO['SAVE']['INDIVIDUAL_CSV']):
            tlm_df_to_csv(out_data_df, file_basename+'_summary.csv', CONFIG_INFO['SAVE']['KEY'])
            stats.add_stat("Data saved to individual csv in summaries/"+file_basename+'_summary.csv')

        save_telemetry(out_data_df, stats=stats)

        if int(CONFIG_INFO['SAVE']['POSTGRESQL']):
            LOGGER.info("Logging to satnogs db . . .")
            add_df_to_satnogs_db(out_data_df,
                                 CONFIG_INFO['SAVE']['KEY'],
                                 CONFIG_INFO['DB']['DBNAME'],
                                 CONFIG_INFO['DB']['USER'],
                                 CONFIG_INFO['DB']['PASSWORD'],
                                 CONFIG_INFO['DB']['HOST'],
                                 CONFIG_INFO['DB']['PORT'],
                                 key,
                                 frames_by_observer[key]['timestamp'].strftime("%Y-%m-%d %H:%M:%S"),
                                 stats=stats)
        stats.write()


def add_df_to_satnogs_db(tlm_df, index_key, db, user, password, host, port, callsign, timestamp, stats=Statistics('none')):
    """
    Adds SatNOGS data to the satnogs database
    :param tlm_df: telemetry dataframe
    :param index_key: key to use to store the data
    :param db: database
    :param user: database user
    :param password: database password
    :param host: database host
    :param port: database port
    :param callsign: observer callsign
    :param timestamp: observation timestamp
    :param stats: statistics file
    :return: void
    """
    conn = connect_to_db(db, user, password, port, host)
    create_satnogs_db(conn)
    cur = conn.cursor()
    LOGGER.info("Adding data to db")
    bad_inserts = 0
    for column in tlm_df:
        datadf = tlm_df[[index_key, column]]
        data = datadf[
            (datadf[index_key] > 568085317) & (datadf[index_key] < 789010117)].dropna().values.tolist()
        insert_query = \
            'INSERT INTO satnogs (t, tlm_val, mnemonic, observer, observation_t) VALUES %s ON CONFLICT DO NOTHING;'
        try:
            psycopg2.extras.execute_values(
                cur, insert_query, data,
                template="(%s, %s, '" + column + "','"+callsign+"','"+timestamp+"')", page_size=1000
            )

        except psycopg2.DataError as e:
            LOGGER.info("Bad tlm point, can't insert into db")
            LOGGER.error(e)
            LOGGER.debug(data)
            bad_inserts += 1
            continue
        except psycopg2.InternalError as e:
            LOGGER.info("Bad tlm point, can't insert into db")
            LOGGER.error(e)
            LOGGER.debug(data)
            bad_inserts += 1

    if bad_inserts:
        stats.add_stat("Had " + str(bad_inserts) + " errors when inserting points into database")

    conn.commit()
    cur.close()
    cluster(conn)
    conn.close()


def get_latest_satnogs_timestamp():
    """
    Fetches the latest timestamp from the satnogs databse
    :return: latest timestamp from satnogs database
    """
    conn = connect_to_db(CONFIG_INFO['DB']['DBNAME'],
                                    CONFIG_INFO['DB']['USER'],
                                    CONFIG_INFO['DB']['PASSWORD'],
                                    CONFIG_INFO['DB']['PORT'],
                                    CONFIG_INFO['DB']['HOST'])
    
    cur = conn.cursor()

    cmd = "SELECT observation_t FROM satnogs ORDER BY observation_t DESC LIMIT 1;"

    cur.execute(cmd)
    date = cur.fetchone()
    print(date)

    cur.close()
    conn.close()


if __name__ == "__main__":
    d = fetch_observation_data_from_id(NORAD, dt.datetime(2018, 12, 3), dt.datetime(2018, 12, 22))
    print(d)