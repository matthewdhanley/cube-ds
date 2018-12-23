from config import *
from helpers import *
import psycopg2
import psycopg2.extras

LOGGER = pylogger.get_logger(__name__)


def connect_to_db(dbname, user, password, port, host):
    LOGGER.info("Connecting to DB . . .")
    auth_string = "dbname="+dbname+" user="+user+" password="+password+" port="+port+" host="+host
    LOGGER.debug(auth_string)
    try:
        conn = psycopg2.connect(auth_string)
        conn.autocommit = True
        return conn
    except psycopg2.OperationalError as e:
        LOGGER.fatal(e)
        LOGGER.fatal("Cannot connect to database. Exiting.")
        exit(1)


def print_version(conn):
    cur = conn.cursor()
    print('PostgreSQL database version:')
    cur.execute('SELECT version()')
    db_version = cur.fetchone()
    print(db_version)


def create_tlm_tables(conn):
    try:
        cur = conn.cursor()
        cmd = """CREATE TABLE IF NOT EXISTS telemetry( 
        t INTEGER NOT NULL, 
        tlm_val float NOT NULL,
        mnemonic VARCHAR,
        PRIMARY KEY (t, mnemonic));"""
        cur.execute(cmd)
        cmd = """CREATE INDEX IF NOT EXISTS common
                ON telemetry (mnemonic, t);"""
        cur.execute(cmd)
        cur.close()
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        return False

    return True


def insert_into_db(conn, tlm_dict, index_key):
    insert_location = str(int(tlm_dict[index_key]))
    cur = conn.cursor()
    for key, value in tlm_dict.items():
        sql = "INSERT INTO "+key+"(time, tlm_val) VALUES("\
              +insert_location+","+str(value)+") ON CONFLICT (time) DO UPDATE SET tlm_val=excluded.tlm_val;"
        cur.execute(sql)
    conn.commit()


def add_df_to_db(tlm_df, index_key, db, user, password, host, port, stats=Statistics('none')):
    conn = connect_to_db(db, user, password, port, host)
    create_tlm_tables(conn)
    cur = conn.cursor()
    LOGGER.info("Adding data to db")
    bad_inserts = 0
    for column in tlm_df:
        datadf = tlm_df[[index_key, column]]
        data = datadf[(datadf[index_key] > 568085317) & (datadf[index_key] < 789010117)].dropna().values.tolist()
        insert_query = 'INSERT INTO telemetry (t, tlm_val, mnemonic) VALUES %s ON CONFLICT DO NOTHING;'
        try:
            psycopg2.extras.execute_values(
                cur, insert_query, data, template="(%s, %s, '"+column+"')", page_size=1000
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
        stats.add_stat("Had "+str(bad_inserts)+" errors when inserting points into database")

    conn.commit()
    cur.close()
    cluster(conn)
    conn.close()


def cluster(conn):
    cur = conn.cursor()
    cur.execute("""CLUSTER telemetry USING common;""")
    conn.commit()
    cur.close()
    LOGGER.info("Clustered db")


def create_catalog_table(conn):
    try:
        cur = conn.cursor()
        cmd = """CREATE TABLE IF NOT EXISTS telemetry_catalog( 
        menmonic VARCHAR NOT NULL,
        package VARCHAR,
        conversion DOUBLE DEFAULT 1,
        dsize INTEGER,
        state VARCHAR,
        description VARCHAR,
        unit VARCHAR,
        val_max DOUBLE,
        val_min DOUBLE,
        PRIMARY KEY (mnemonic));"""
        cur.execute(cmd)
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        LOGGER.error(error)
        return False

    csv_info = get_csv_info()
    for c in csv_info:
        pointsFile = c['pointsFile']
        tlm_dict = get_tlm_points(pointsFile)
        for point in tlm_dict:
            cmd = """INSERT INTO telemetry_catalog (
                         mnemonic, 
                         package, 
                         conversion, 
                         dsize, 
                         state, 
                         description, 
                         unit, 
                         val_max, 
                         val_min) 
                     VALUES (
                         '"""+point['name']+"""',
                         '"""+point['package']+"""',
                         '"""+point['conversion']+"""',
                         '"""+point['size']+"""',
                         '"""+point['state']+"""',
                         '"""+point['description']+"""',
                         '"""+point['unit']+"""',
                         '"""+point['max']+"""',
                         '"""+point['min']+"""')
                      ON CONFLICT DO NOTHING;"""

            try:
                cur.execute(cmd)

            except psycopg2.DataError as e:
                LOGGER.info("Bad catalog entry, can't insert into db")
                LOGGER.error(e)
                LOGGER.debug(point)
                continue
            except psycopg2.InternalError as e:
                LOGGER.info("Bad catalog entry, can't insert into db")
                LOGGER.error(e)
                LOGGER.debug(point)
                continue
    try:
        conn.commit()
    except psycopg2.DataError as e:
        LOGGER.info("Error committing catalog to db")
        LOGGER.error(e)
    except psycopg2.InternalError as e:
        LOGGER.info("Error committing catalog to db")
        LOGGER.error(e)



