import requests
import datetime as dt
import binascii
import cubeds.db
import cubeds.config
import cubeds.pylogger
import psycopg2.extras
import os
import re
import maidenhead as mh


class Satnogs:
    def __init__(self, config):
        self._logger = cubeds.pylogger.get_logger(__name__)
        self.config = config
        self.norad_id = self.config.config['satnogs'][config.yaml_key]['norad_id']
        self.db_api_base_url = self.config.config['satnogs'][config.yaml_key]['db_api_base_url']
        self.db = cubeds.db.Database(self.config)
        self.data = None
        self.url = self.db_api_base_url + '?satellite=' + str(self.norad_id)

    def get_paginated_endpoint(self, max_entries=None, min_time=dt.datetime(2000, 1, 1)):
        """
        :param max_entries: optional argument to limit the number of entries retrieved from satnogs database
        :param min_time: datetime object from which all data will be fetched until latest time.
        :return: datetime object of last time
        """
        self._logger.info("Getting new data from satnogs database . . .")
        r = requests.get(url=self.url)
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
        self.data = data

    def get_satnogs_filename(self):
        """
        Generates satnogs .kss filename and appends it to Rundirs path
        :return: Full file path with filename
        """
        now = dt.datetime.now()
        folder = self.config.config['rundirs'][self.config.yaml_key]['location']
        filename = now.strftime('satnogs_%Y%j%H%M.kss')
        print(folder)
        filename = os.path.join(folder[0],filename)
        return filename

    def get_last_satnogs_frame(self):
        """
        Gets latest frame in local satnogs database
        :return: datetime object of last time
        """
        cmd = "SELECT observation_t FROM satnogs ORDER BY observation_t DESC LIMIT 1;"
        cur = self.db.get_cursor()
        cur.execute(cmd)
        date = cur.fetchone()[0]
        cur.close()
        return date

    def create_satnogs_db(self):
        """
        Creates table for SATNOGS database
        :param conn: database connection as defined by DB section in config file
        :return: void
        """
        cur = self.db.get_cursor()

        cmd = """CREATE TABLE IF NOT EXISTS satnogs_observers( 
                            observer VARCHAR,
                            latitude FLOAT,
                            longitude FLOAT,
                            PRIMARY KEY (observer));"""

        cur.execute(cmd)

        cmd = """CREATE TABLE IF NOT EXISTS satnogs_observations( 
            id SERIAL PRIMARY KEY,
            observation_t TIMESTAMP,
            observer VARCHAR REFERENCES satnogs_observers(observer));"""
        cur.execute(cmd)
        cur.close()

    def save_satnogs_data(self):
        """
        Main driver for satnogs data processing
        :param csv_info: csv_info dict as returned by helpers.get_csv_info
        :return: nothing.
        """
        insert_cmd = """INSERT INTO satnogs_observations (observer, observation_t) VALUES %s ON CONFLICT DO NOTHING;"""
        insert_observer = """INSERT INTO satnogs_observers (observer, latitude, longitude) VALUES %s ON CONFLICT DO NOTHING;"""
        insert_data = []
        insert_observer_data = []

        self.db = cubeds.db.Database(self.config)
        self.db.connect()
        self.create_satnogs_db()
        
        try:
            min_date = self.get_last_satnogs_frame()
            self._logger.info("Latest frame currently in database: "+min_date.strftime("%Y/%j-%H:%M:%S"))
            self.get_paginated_endpoint(min_time=min_date)
        except (psycopg2.ProgrammingError, TypeError):
            self._logger.info("Fetching all data from satnogs db. This might take a while . . .")
            self.get_paginated_endpoint(max_entries=10)

        if self.data is not None:
            self._logger.info("Found "+str(len(self.data))+" SatNOGS Frames")
            outfile = self.get_satnogs_filename()
            with open(outfile, 'wb') as fout:
                for d in self.data:
                    fout.write(
                        binascii.unhexlify(d['frame'])
                    )
                    m = re.search('(.*)-(\w\w\d\d\w\w)', d['observer'])
                    qthlocator = m.groups(1)[1]
                    observer = m.groups(1)[0]
                    latitude, longitude = mh.toLoc(qthlocator)
                    insert_data.append((observer, d['timestamp']))
                    insert_observer_data.append((observer, str(latitude), str(longitude)))
                cur = self.db.get_cursor()
                psycopg2.extras.execute_values(
                    cur, insert_observer, insert_observer_data, page_size=1000
                )
                psycopg2.extras.execute_values(
                    cur, insert_cmd, insert_data, page_size=1000
                )
                cur.close()
                self.db.conn.commit()
                self._logger.info("Created SatNOGS .kss file: "+outfile)
        else:
            self._logger.info("No SatNOGS data found.")


