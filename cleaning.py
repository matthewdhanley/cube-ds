from config import *
from helpers import *


def clean_times(tlm_df, time_index, convert_function, stats=Statistics('none')):
    LOGGER.info("Cleaning data with bad times")
    og_size = tlm_df.shape[0]
    tlm_df = tlm_df[(tlm_df[time_index] > convert_function(CONFIG_INFO['CLEANING']['MIN_TIME'])) &
                    (tlm_df[time_index] < now_tai())]
    num_stripped = og_size - tlm_df.shape[0]

    stats.add_stat("Removed "+str(num_stripped)+" corrupted packets with bad timestamps")

    return tlm_df
