from config import *
from netCDF4 import Dataset
from helpers import *

LOGGER = pylogger.get_logger()


def save_to_netcdf(data, file, index_key):
    mainGroup = get_main_group(file)

    csv_file = CONFIG_INFO['csv']['location']
    csv_info = get_csv_info(csv_file)
    for info in csv_info:
        tlm_points = get_tlm_points(info['pointsFile'])
        netcdf_setup(tlm_points, mainGroup)

    netcdf_add_data(data, mainGroup, index_key)
    mainGroup.close()


def createFile(filename):
    """
    Creates netCDF File
    :param filename: name of the file, default extension is .nc
    :return: void
    """
    mainGroup = Dataset(filename, "w", format="NETCDF4")
    time = mainGroup.createDimension("time", None)  # None sets the dimension size to unlimited.
    times = mainGroup.createVariable("time", "f8", ("time",))
    times.setncattr('unit', 'seconds since 2018/001 - 00:00:00')
    mainGroup.close()


def get_netcdf_dtype(size, state=''):
    """
    Gets netCDF variable type. States will be stored as ints.
    :param size: size in bits of variable
    :param state: state string. state='' if no state present
    :return:
    """
    # Determine if it's a state or not. If it is, store it as an int.
    if state != '':
        type_str = 'i'
    else:
        type_str = 'f'

    size = int(size) / 8
    if size <= 1 and type_str == 'i':
        size_str = '1'
    elif size <= 2 and type_str == 'i':
        size_str = '2'
    elif size <= 4:
        size_str = '4'
    elif size <= 8:
        size_str = '8'
    else:
        format_str = 'f8'
        LOGGER.warning('Using default f8 value for NetCDF because the size didn\'t match anything expected')
        return format_str

    format_str = type_str + size_str
    return format_str


def get_main_group(filename):
    """
    Retrieves NetCDF main group from given filename. If can't find the filename, makes the file.
    :param filename: name of NetCDF File
    :return: main group object
    """
    LOGGER.info("Opening NetCDF file " + filename)
    if not os.path.isfile(filename):
        LOGGER.warning("Could not find netCDF file " + filename + ", creating it.")
        createFile(filename)
    mainGroup = Dataset(filename, "a", format="NETCDF4")
    return mainGroup


def netcdf_add_data(tlm_data, mainGroup, index_key):
    """
    This version adds using the TAI time as the insert index
    :param tlm_data:
    :param mainGroup:
    :return:
    """
    times = mainGroup.variables['time']

    for packet in tlm_data:
        timeIndex = int(packet[index_key])
        timeIndex = get_time_index(timeIndex)
        print(timeIndex)
        for tlm_name, value in packet.items():
            if tlm_name not in mainGroup.variables.keys():
                LOGGER.fatal("Something went wrong and could not find variable in NetCDF File...")
                exit(1)
            datapt = mainGroup.variables[tlm_name]
            if timeIndex < 0:
                LOGGER.warn("Bad time index of "+str(timeIndex)+". Skipping it.")
                break
            try:
                datapt[timeIndex] = value
                times[timeIndex] = timeIndex
            except OverflowError:
                LOGGER.warn("Overflow error on NetCDF Insert")
            except IndexError:
                LOGGER.error("Index error.")
                exit(1)
        # mainGroup.sync()
        LOGGER.debug(timeIndex)
        LOGGER.debug("Synced NetCDF to disk")


def get_time_index(index):
    first_time = TAI_EPOCH + dt.timedelta(seconds=index)
    out_index = (first_time - NETCDF_EPOCH).total_seconds()
    return int(out_index)


def netcdf_setup(tlm_points, mainGroup):
    for point in tlm_points:
        if point['name'] not in mainGroup.variables.keys():
            # If not, create it.
            dtype_string = get_netcdf_dtype(point['size'], state=point['state'])
            datapt = mainGroup.createVariable(point['name'], dtype_string, ("time",))
            datapt.setncattr('unit', point['unit'])
            datapt.setncattr('state', point['state'])
            datapt.setncattr('description', point['description'])
