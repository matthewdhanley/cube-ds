from config import *
from helpers import *
# from idlpy import *

LOGGER = pylogger.get_logger(__name__)


def df_to_dict(df, time_index):
    pprint.pprint(df.set_index(time_index).to_dict())