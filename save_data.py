from config import *
from csv_out import *
from postgresql import *
from idl_out import *

LOGGER = pylogger.get_logger(__name__)

def save_telemetry(tlm):
    if int(CONFIG_INFO['SAVE']['CSV']) or int(CONFIG_INFO['SAVE']['SUMMARY_CSV']):
        LOGGER.info("Saving telemetry to "+CONFIG_INFO['SAVE']['CSV_FILE'])
        df = tlm_to_df(tlm, CONFIG_INFO['SAVE']['KEY'])
        if not int(CONFIG_INFO['SAVE']['CSV']):
            tlm_df_to_csv(df, '', CONFIG_INFO['SAVE']['KEY'],
                          pass_summary=int(CONFIG_INFO['SAVE']['SUMMARY_CSV']))
        else:
            tlm_df_to_csv(df, CONFIG_INFO['SAVE']['CSV_FILE'], CONFIG_INFO['SAVE']['KEY'],
                          pass_summary=int(CONFIG_INFO['SAVE']['SUMMARY_CSV']))

    if int(CONFIG_INFO['SAVE']['NETCDF']):
        LOGGER.info("Saving telemetry to "+CONFIG_INFO['SAVE']['NETCDF_FILE'])
        save_to_netcdf(tlm, CONFIG_INFO['SAVE']['NETCDF_FILE'], index_key=CONFIG_INFO['SAVE']['KEY'])

    if int(CONFIG_INFO['SAVE']['POSTGRESQL']):
        LOGGER.info("Saving telemetry to database . . .")
        df = tlm_to_df(tlm, CONFIG_INFO['SAVE']['KEY'])
        add_df_to_db(df, CONFIG_INFO['SAVE']['KEY'],
                     CONFIG_INFO['DB']['DBNAME'],
                     CONFIG_INFO['DB']['USER'],
                     CONFIG_INFO['DB']['PASSWORD'],
                     CONFIG_INFO['DB']['HOST'],
                     CONFIG_INFO['DB']['PORT'])

    if int(CONFIG_INFO['SAVE']['IDL']):
        df = tlm_to_df(tlm, CONFIG_INFO['SAVE']['KEY'])
        df_to_dict(df, CONFIG_INFO['SAVE']['KEY'])