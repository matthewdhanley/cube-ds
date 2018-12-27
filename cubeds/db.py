import psycopg2
import psycopg2.extras
import cubeds.pylogger
import cubeds.exceptions


class Database:
    def __init__(self, config):
        self._logger = cubeds.pylogger.get_logger(__name__)
        self.config = config
        self.conn = None
        self.dbname = self.config.config['save']['postgresql'][self.config.yaml_key]['dbname']
        self.password = self.config.config['save']['postgresql'][self.config.yaml_key]['password']
        self.user = self.config.config['save']['postgresql'][self.config.yaml_key]['user']
        self.host = self.config.config['save']['postgresql'][self.config.yaml_key]['host']
        self.port = self.config.config['save']['postgresql'][self.config.yaml_key]['port']
        self.index_key = 'time_index'
        self.index_min = 568085317
        self.index_max = 789010117

        self.page_size = 1000

        self.auth_string = "dbname=" + self.dbname \
                           + " user=" + self.user \
                           + " password=" + self.password \
                           + " port=" + str(self.port) \
                           + " host=" + self.host

        self.table_cmd = """CREATE TABLE IF NOT EXISTS telemetry( 
                                t INTEGER NOT NULL, 
                                tlm_val float NOT NULL,
                                mnemonic VARCHAR,
                                PRIMARY KEY (t, mnemonic));"""

        self.index_cmd = """CREATE INDEX IF NOT EXISTS common
                                ON telemetry (mnemonic, t);"""

        self.insert_query = """INSERT INTO telemetry (t, tlm_val, mnemonic) VALUES %s ON CONFLICT DO NOTHING;"""
        self.cluster_cmd = """CLUSTER telemetry USING common;"""

    def __del__(self):
        """
        Safely closes class.
        :return:
        """
        self.close()

    def connect(self):
        try:
            conn = psycopg2.connect(self.auth_string)
            self._logger.verbose("Connected to database "+self.dbname)
            conn.autocommit = True
            self.conn = conn

        except psycopg2.OperationalError as e:
            self._logger.fatal(e)
            self._logger.fatal("Cannot connect to database. Exiting.")
            raise e

    def close(self):
        if self.conn is not None:
            self._logger.verbose("Closed DB connection to database "+self.dbname)
            self.conn.close()
            self.conn = None

    def create_tlm_tables(self):
        if self.conn is None:
            self._logger.error("No database connection exists.")
            raise cubeds.exceptions.DbConnError("No database connection exists.")

        try:
            cur = self.conn.cursor()
            self._logger.debug(self.table_cmd)
            cur.execute(self.table_cmd)

            self._logger.debug(self.index_cmd)
            cur.execute(self.index_cmd)
            cur.close()
            self.conn.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            return False

        return True

    def add_df_to_db(self, tlm_df):
        if self.conn is None:
            self._logger.error("No database connection exists.")
            raise cubeds.exceptions.DbConnError("No database connection exists.")
        self.create_tlm_tables()
        cur = self.conn.cursor()
        self._logger.info("Adding data to db")
        bad_inserts = 0
        for column in tlm_df:
            datadf = tlm_df[[self.index_key, column]]
            data = datadf[(datadf[self.index_key] > self.index_min)
                          & (datadf[self.index_key] < self.index_max)].dropna().values.tolist()

            try:
                psycopg2.extras.execute_values(
                    cur, self.insert_query, data, template="(%s, %s, '" + column + "')", page_size=self.page_size
                )

            except psycopg2.DataError as e:
                self._logger.info("Bad tlm point, can't insert into db")
                self._logger.error(e)
                self._logger.debug(data)
                bad_inserts += 1
                continue
            except psycopg2.InternalError as e:
                self._logger.info("Bad tlm point, can't insert into db")
                self._logger.error(e)
                self._logger.debug(data)
                bad_inserts += 1

        if bad_inserts:
            self._logger.info("Had " + str(bad_inserts) + " errors when inserting points into database")

        self.conn.commit()
        cur.close()
        self.cluster()

    def cluster(self):
        cur = self.conn.cursor()
        cur.execute(self.cluster_cmd)
        self.conn.commit()
        cur.close()
        self._logger.info("Clustered db")

