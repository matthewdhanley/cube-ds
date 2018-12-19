from config import *
from csv_out import *
from postgresql import *
from idl_out import *
from netcdf import *

LOGGER = pylogger.get_logger(__name__)


def save_telemetry(df, stats=Statistics('none')):
    if int(CONFIG_INFO['SAVE']['CSV']) or int(CONFIG_INFO['SAVE']['SUMMARY_CSV']):
        LOGGER.info("Saving telemetry to "+CONFIG_INFO['SAVE']['CSV_FILE'])
        if not int(CONFIG_INFO['SAVE']['CSV']):
            tlm_df_to_csv(df, '', CONFIG_INFO['SAVE']['KEY'],
                          pass_summary=int(CONFIG_INFO['SAVE']['SUMMARY_CSV']))
        else:
            if stats:
                stats.add_stat("Saved telemetry to " + CONFIG_INFO['SAVE']['CSV_FILE'])
            tlm_df_to_csv(df, CONFIG_INFO['SAVE']['CSV_FILE'], CONFIG_INFO['SAVE']['KEY'],
                          pass_summary=int(CONFIG_INFO['SAVE']['SUMMARY_CSV']))

    # if int(CONFIG_INFO['SAVE']['NETCDF']):
    #     LOGGER.info("Saving telemetry to "+CONFIG_INFO['SAVE']['NETCDF_FILE'])
    #     save_to_netcdf(tlm, CONFIG_INFO['SAVE']['NETCDF_FILE'], index_key=CONFIG_INFO['SAVE']['KEY'])
    #     if stats:
    #         stats.add_stat("Saved telemetry to "+CONFIG_INFO['SAVE']['NETCDF_FILE'])

    if int(CONFIG_INFO['SAVE']['POSTGRESQL']):
        LOGGER.info("Saving telemetry to database . . .")
        add_df_to_db(df, CONFIG_INFO['SAVE']['KEY'],
                     CONFIG_INFO['DB']['DBNAME'],
                     CONFIG_INFO['DB']['USER'],
                     CONFIG_INFO['DB']['PASSWORD'],
                     CONFIG_INFO['DB']['HOST'],
                     CONFIG_INFO['DB']['PORT'],
                     stats=stats)
        if stats:
            stats.add_stat("Saved telemetry to database "+CONFIG_INFO['DB']['DBNAME'])

    if int(CONFIG_INFO['SAVE']['IDL']):
        df_to_dict(df, CONFIG_INFO['SAVE']['KEY'])
        if stats:
            stats.add_stat("Didn't save telemetry to IDL because that's not supported yet")
