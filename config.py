import datetime as dt
import pylogger
import configparser
import os
import struct
import pprint
import numpy as np
import csv
import re
import json

# GLOBALS ==================================================================================
TAI_EPOCH = dt.datetime(1999, 12, 31, 23, 59, 23)  # Epoch time for incoming time stamps
MAX_TIME = dt.datetime(2020, 1, 1, 12, 0, 0)  # max allowable time for naive filtering
MIN_TIME = dt.datetime(2018, 1, 1, 12, 0, 0)  # minimum allowable time for naive filtering
NETCDF_EPOCH = dt.datetime(2000, 1, 1)  # Epoch for netCDF file.

CONFIG_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "cube_ds_2.cfg")  # defines config file for configparser
# Parsing the config file.
CONFIG_INFO = configparser.ConfigParser()
CONFIG_INFO.read(CONFIG_FILE)

# Setup for TEST mode
TEST = int(CONFIG_INFO['TEST']['TEST'])  # check if TEST mode is set in config file

