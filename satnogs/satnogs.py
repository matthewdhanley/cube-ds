import requests
import datetime as dt
import binascii
import cubeds.db
import cubeds.config
import psycopg2.extras

NETWORK_BASE_URL = 'https://network.satnogs.org'
DB_API_URL = 'https://db.satnogs.org/api/telemetry/'
NORAD = 43793  # norad id as it apperas on satnogs


def get_paginated_endpoint(url, max_entries=None, min_time=dt.datetime(2000, 1, 1)):
    r = requests.get(url=url)
    r.raise_for_status()

    data = r.json()

    timestamp = dt.datetime(2050, 1, 1)

    while 'next' in r.links and (not max_entries or len(data) < max_entries) and timestamp > min_time:
        next_page_url = r.links['next']['url']

        r = requests.get(url=next_page_url)
        r.raise_for_status()
        j = r.json()
        timestamp = dt.datetime.strptime(j[-1]['timestamp'], '%Y-%m-%dT%H:%M:%SZ')
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


def create_satnogs_db(conn):
    """
    Creates table for SATNOGS database
    :param conn: database connection as defined by DB section in config file
    :return: void
    """
    cmd = """CREATE TABLE IF NOT EXISTS satnogs( 
        observation_t TIMESTAMP,
        observer VARCHAR,
        PRIMARY KEY (observer, observation_t));"""

    cur = conn.cursor()
    cur.execute(cmd)
    cur.close()


def save_satnogs_data(config):
    """
    Main driver for satnogs data processing
    :param csv_info: csv_info dict as returned by helpers.get_csv_info
    :return: nothing.
    """
    insert_cmd = """INSERT INTO satnogs (observer, observation_t) VALUES %s ON CONFLICT DO NOTHING;"""
    insert_data = []
    data = get_paginated_endpoint(DB_API_URL+'?satellite='+str(NORAD))
    db = cubeds.db.Database(config)
    db.connect()
    create_satnogs_db(db.conn)
    with open('all_satnogs.kss', 'wb') as fout:
        for d in data:
            fout.write(
                binascii.unhexlify(d['frame'])
            )
            insert_data.append((d['observer'], d['timestamp']))
        cur = db.get_cursor()
        psycopg2.extras.execute_values(
            cur, insert_cmd, insert_data, page_size=1000
        )
        cur.close()
        db.conn.commit()



if __name__ == "__main__":
    config = cubeds.config.Config(file='D:\\home\\mhanl\\git\\cube-ds\\cubeds\\cfg\\csim.yml')
    save_satnogs_data(config)