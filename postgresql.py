from config import *
import psycopg2
import psycopg2.extras

# LOGGER = pylogger.get_logger(__name__)


def connect_to_db(dbname, user, password):
    LOGGER.info("Connecting to DB . . .")
    auth_string = "dbname="+dbname+" user="+user+" password="+password
    conn = psycopg2.connect(auth_string)
    return conn


def print_version(conn):
    cur = conn.cursor()
    print('PostgreSQL database version:')
    cur.execute('SELECT version()')
    db_version = cur.fetchone()
    print(db_version)


def create_tlm_tables(conn, tlm_names):
    try:
        cur = conn.cursor()
        for tlm_name in tlm_names:
            cmd = "CREATE TABLE IF NOT EXISTS " + tlm_name + "( time INTEGER PRIMARY KEY NOT NULL, tlm_val float NOT NULL);"
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
        sql = "INSERT INTO "+key+"(time, tlm_val) VALUES("+insert_location+","+str(value)+") ON CONFLICT (time) DO UPDATE SET tlm_val=excluded.tlm_val;"
        cur.execute(sql)
    conn.commit()


def add_df_to_db(tlm_df, index_key, db, user, password):
    conn = connect_to_db(db, user, password)
    cur = conn.cursor()
    for column in tlm_df:
        data = tlm_df[[index_key, column]].values.tolist()
        insert_query = 'INSERT INTO ' + column + ' (time, tlm_val) VALUES %s ON CONFLICT (time) DO NOTHING;'
        psycopg2.extras.execute_values(
            cur, insert_query, data, template=None, page_size=1000
        )


def add_to_db(tlm, index_key, db, user, password):
    if len(tlm) == 0:
        LOGGER.error("No data to add to db.")
        exit(1)
    first_pt = tlm[0]
    conn = connect_to_db(db, user, password)
    create_tlm_tables(conn, first_pt.keys())
    for t in tlm:
        insert_into_db(conn, t, index_key)
    conn.close()


