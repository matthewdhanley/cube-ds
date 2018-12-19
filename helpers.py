from config import *
import pickle
LOGGER = pylogger.get_logger(__name__)


def extract_bits_from_bytes(data, start_bit, num_bits):
    """
    Extracts bits from a group of bytes
    :param data: byte data
    :param start_bit: starting bit to begin extraction
    :param num_bits: number of bits to extract
    :return: bitarray of requested bits
    """
    b = bitarray(endian='big')
    b.frombytes(data)
    out = b[start_bit:start_bit+num_bits]
    return out


def extract_bits(data, bit, length=1):
    """
    Extracts bits given data, start bit, and length
    :param data: data to extract bits from
    :param bit: starting position for extraction
    :param length: number of bits to extract, default=1
    :return: resulting integer of extracted bits
    """
    bits = bitarray(data, endian='big')
    if length > 1:
        out = bits[bit:bit+length]
        out = struct.unpack('>B', out.tobytes())[0]
    else:
        try:
            out = bits[bit]
        except IndexError:
            out = 0
    return int(out)


def bitstring_to_int(bitstr):
    b_list = bitstr.tolist()
    mystring = ''
    for s in b_list:
        if s:
            mystring += '1'
        else:
            mystring += '0'
    b = int(mystring, 2)
    return b


def tlm_to_df(tlm, time_index):
    """
    Converts telemetry dictionary to a dataframe
    :param tlm: telemetry dictionary
    :param time_index: desired time index
    :return:
    """
    if tlm:
        df = pd.DataFrame().from_dict(tlm).sort_values(by=[time_index])
    else:
        LOGGER.warning("No data found. Returning empty dataframe")
        return pd.DataFrame()
    try:
        df = df.dropna()
        df[time_index] = df[time_index].map(lambda x: int(x))
    except ValueError as e:
        LOGGER.debug(e)
        LOGGER.warning("Returning empty dataframe")
        return pd.DataFrame()
    return df


def add_utc_to_df(df, time_index, conversion_function):
    """
    Adds a utc column to dataframe
    :param df: dataframe that needs utc column
    :param time_index: column to convert to utc
    :param conversion_function: function to convert values in time_index function to utc
    :return: updated dataframe
    """
    df['UTC'] = df[time_index].map(lambda x: conversion_function(x))
    return df


def get_tlm_time_dt(taiTime, epoch=TAI_EPOCH):
    """
    Convert seconds since epoch to datetime object
    :param taiTime: seconds since TAI_EPOCH variable
    :return: datetime object
    """
    tlm_dt = epoch + dt.timedelta(seconds=taiTime)
    return tlm_dt


def get_unpack_format(in_dtype, dsize, endian='big'):
    """
    Given data type and size, generate a format for struct.unpack.
    ASSUMES BIG ENDIAN for the data that will be unpacked. can specifiy by using endian="little"
    :param in_dtype: Type of data. Valid types are dn (unsigned), sn (signed), char, float, or double
    :param dsize: size of data in BITS!!!!
    :param endian: endianess of the data
    :return:
    """
    if dsize <= 8:
        # bits
        letter = 'b'
    elif dsize == 16:
        # short
        letter = 'h'
    elif dsize == 32:
        # int
        letter = 'i'
    elif dsize == 64:
        # long long
        letter = 'q'
    elif dsize == -1:
        # padding
        letter = str(dsize//8)+'x'  # want self.size bytes of padding
        in_dtype = 'int'
        dsize = 1
    else:
        LOGGER.fatal("parsing error for datatype size")
        exit(1)

    if in_dtype == 'dn':
        letter = letter.upper()
    elif in_dtype == 'sn':
        letter = letter.lower()
    elif in_dtype == 'char':
        letter = str(int(dsize/8)) + 's'
    elif in_dtype == 'float' or in_dtype == 'double':
        letter = 'd'
    else:
        LOGGER.fatal("parsing error for datatype \"" + in_dtype + "\" with size \"" + str(dsize) + "\"")
        exit(1)

    if endian == 'big':
        letter = '>' + letter
    elif endian == 'little':
        letter = '<' + letter
    else:
        LOGGER.warning("DID NOT SPECIFY ENDIANNESS CORRECTLY")
    return letter


def get_csv_info(csv_filename):
    """
    Reads in CSV info from top level file
    :param csv_filename: csv file name
    :return: dictionary of csv lines
    """
    # make sure file exists
    assert os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), csv_filename))

    csv_encoding = get_csv_encoding()

    with open(csv_filename, mode='r', encoding=csv_encoding) as csv_f:
        reader = csv.DictReader(csv_f)
        csv_dict_list = []
        for row in reader:
            csv_dict_list.append(row)
    return csv_dict_list


def get_tlm_data(raw_file, endian="big"):
    """
    reads in raw data
    :param raw_file: binary data file.
    :param endian: either "big" or "little"
    :return: large endian numpy byte array
    """
    LOGGER.debug("Telemetry file -  " + raw_file)

    # check that the file exists
    if not os.path.exists(raw_file):
        LOGGER.debug(raw_file)
        LOGGER.fatal("Cannot find specified file "+raw_file)
        exit(1)

    # read the data into a numpy array
    LOGGER.debug("reading data into numpy byte array")
    if endian == "big":
        raw_data = np.fromfile(raw_file, dtype='>B')
    elif endian == "little":
        raw_data = np.fromfile(raw_file, dtype='<B')
    else:
        LOGGER.fatal("DID NOT specify correct endian")
        exit(1)
    return raw_data


def get_header_dict(headerfile):
    """
    Generates a header dictionary list from the header csv file
    :param headerfile: CSV Header File
    :return: list of dictionaries of components of the header
    """
    # make sure file exists
    try:
        assert os.path.exists(headerfile)
    except AssertionError:
        LOGGER.error("Can't find file "+headerfile)

    csv_encoding = get_csv_encoding()

    with open(headerfile, mode='r', encoding=csv_encoding) as csv_f:
        reader = csv.DictReader(csv_f)
        header_dict_list = []
        for row in reader:
            header_dict_list.append(dict(row))
    return header_dict_list


def get_csv_encoding():
    """
    Grabs the CSV encoding type form the config file, csv section, encoding variable.
    :return: csv encoding type string
    """

    if TEST:
        config_param = 'csv_test'
    else:
        config_param = 'csv'

    try:
        csv_encoding = CONFIG_INFO[config_param]['encoding']
    except KeyError:
        csv_encoding = 'utf-8'
        LOGGER.debug('Using utf-8 encoding because couldn\'t find encoding type in config file')

    return csv_encoding


def get_tlm_points(pointsFile):
    """
    This function will get all the points from the points file input to the function
    :param pointsFile: csv file with all the points.
    :return: List of dictionaries of points.
    """
    # make sure file exists
    assert os.path.exists(pointsFile)

    csv_encoding = get_csv_encoding()

    with open(pointsFile, mode='r', encoding=csv_encoding) as csv_f:
        # create a dictionary from the top level csv file
        reader = csv.DictReader(csv_f)

        # init list for saving the points dict
        points_dict_list = []
        for row in reader:
            # if the "state" column includes a "/", that means that there is a properly formatted state pair,
            # i.e. "0/ON 1/OFF"
            # ALL PAIRS SHOULD BE SEPERATED BY A SPACE AND FORMATTED AS FOLLOWS: VAL/STR VAL/STR
            if '/' in row['state']:
                row['unit'] = ''

                # Seperate pairs and strip whitespace
                stateArray = [x.strip() for x in row['state'].split(' ')]

                # init empty dictionary
                state_dict = {}

                # loop through the pairs and stor them in the dictionary with the integer as the key and the string as
                # the value
                for keyStrPair in stateArray:
                    # extract the "key/str" pair
                    stateVal, stateStr = keyStrPair.split('/')
                    state_dict[stateVal] = stateStr

                row['state'] = json.dumps(state_dict)
            else:
                row['state'] = ''

            # append the new dictionary to the list
            points_dict_list.append(dict(row))
    return points_dict_list


def write_to_pickle(data, filename):
    """
    writes data to a pickle file with given filename
    :param data: data to write to file
    :param filename: i.e. mydata.pkl
    :return:
    """
    LOGGER.info("Writing data to pickle file "+filename)
    with open('obj/'+filename, 'wb') as f:
        pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)


def find_files(re_strings, rootdir, exclude=''):
    """
    Finds files given array of regex strings
    :param re_strings: array of regex strings
    :param rootdir: directory to search for file (recursively)
    :param exclude: array of regex strings to exclude
    :return: list of matching files
    """
    raw_files = []
    for root, directories, filenames in os.walk(rootdir):
        for filename in filenames:
            if exclude:
                found_flag = False
                for re_string in exclude:
                    m = re.search(re_string, filename)
                    if m:
                        found_flag = True
                if found_flag:
                    continue
            for re_string in re_strings:
                m = re.search(re_string, filename)
                if m:
                    raw_files.append(os.path.join(root, filename))
    if not raw_files:
        LOGGER.warning("Didn't find any raw files in " + rootdir)
    return raw_files


def tai_to_utc(tai, time_format="%Y/%j-%H:%M:%S", epoch=TAI_EPOCH):
    """
    Converts TAI time to UTC time
    :param tai: TAI time
    :param time_format: Format of output UTC time
    :return: UTC time string
    """
    try:
        utc = epoch + dt.timedelta(seconds=int(tai))
    except OverflowError:
        utc = epoch
    return utc.strftime(time_format)


def utc_to_tai(utc, time_format='%m/%d/%Y-%H:%M:%S', epoch=TAI_EPOCH):
    """
    Converts UTC to TAI
    :param utc: UTC time string
    :param time_format: Format of input string
    :param epoch: epoch of time
    :return: Seconds since epoch of given utc time
    """
    in_date = dt.datetime.strptime(utc, time_format)
    tai = (in_date - epoch).total_seconds()
    return tai


def now_tai(epoch=TAI_EPOCH):
    """
    Converts current time to tai
    :param epoch: epoch of time
    :return: tai from now since epoch
    """
    tai = (dt.datetime.now() - epoch).total_seconds()
    return tai


def get_apids():
    """
    Returns list of apids from file specified in cfg file
    :return: list of apids
    """
    csv_file = CONFIG_INFO['csv']['location']
    csv_info = get_csv_info(csv_file)
    apids = []
    for line in csv_info:
        if int(line['apid']) not in apids:
            apids.append(int(line['apid']))
    return apids
