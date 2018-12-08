from config import *
from netCDF4 import Dataset


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
    """
    TAI Epoch Source:
    Seidelmann, P. K., Ed. (1992). Explanatory Supplement to the Astronomical Almanac. 
        Sausalito, CA: University Science Books. Glossary, s.v. Terrestrial Dynamical Time.
    """
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


# def direct_add_point(timeIndex, point, value, mainGroup):
#     times = mainGroup.variables['time']
#     # length = len(mainGroup.dimensions['time'])
#     tlm_name = point['name']
#
#     if tlm_name in mainGroup.variables.keys():
#         # If it has, retrieve it.
#         datapt = mainGroup.variables[tlm_name]
#     else:
#         # If not, create it.
#         dtype_string = get_netcdf_dtype(point['size'], state=point['state'])
#         datapt = mainGroup.createVariable(tlm_name, dtype_string, ("time",))
#         datapt.setncattr('unit', point['unit'])
#         datapt.setncattr('state', point['state'])
#         datapt.setncattr('description', point['description'])
#     try:
#         timeIndex = int(timeIndex)
#         datapt[timeIndex] = value
#         times[timeIndex] = timeIndex
#     except OverflowError:
#         LOGGER.warning('Overflow Error on '+point['name']+' with value '+str(value))


def netcdf_add_data(tlm_data, mainGroup):
    """
    This version adds using the TAI time as the insert index
    :param tlm_data:
    :param mainGroup:
    :return:
    """
    times = mainGroup.variables['time']

    for timeIndex, packet in tlm_data.items():
        for tlm_name, value in packet.items():
            if tlm_name not in mainGroup.variables.keys():
                LOGGER.fatal("Something went wrong and could not find variable in NetCDF File...")
                exit(1)

            datapt = mainGroup.variables[tlm_name]
            timeIndex = int(timeIndex)
            try:
                datapt[timeIndex] = value
                times[timeIndex] = timeIndex
            except OverflowError:
                LOGGER.warn("Overflow error on NetCDF Insert")
        mainGroup.sync()
        LOGGER.debug(timeIndex)
        LOGGER.debug("Synced NetCDF to disk")
