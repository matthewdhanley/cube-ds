from config import *
from helpers import *
LOGGER = pylogger.get_logger(__name__)


def tlm_df_to_csv(df, filename, index, pass_summary=0):
    if df.empty:
        LOGGER.error("No data found to write to CSV")
        return(1)
    LOGGER.info("Writing data to CSV file "+filename)
    df = add_utc_to_df(df, index, tai_to_utc)
    df = df.set_index('UTC')
    df.to_csv(filename)
    if pass_summary:
        new_filename = make_csv_summary_filename()
        tlm_df_to_csv(df, new_filename, index)
    return 0


def make_csv_summary_filename():
    now = dt.datetime.now().strftime('%Y_%j_%H_%M_%S.csv')
    return now
