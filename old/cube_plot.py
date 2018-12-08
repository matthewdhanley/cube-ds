import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime as dt
import sys, os
import re
from old.cube_ds import get_logger


# GLOBALS
TAI_EPOCH = dt.datetime(2000,1,1,11,59,27)
YEARMIN = 2017
YEARMAX = 2020

# CHANGE THIS TO WHERE PARENT DIRECTORY OF THE JSON FILES
PACKETS_DIR = "D:\\home\\mhanl\\git\\cube-ds\\test\\xb1"

# CONFIG FILE NOT REQUIRED, DON'T WORRY ABOUT THIS TOO MUCH
CONFIG_FILE = "cube_ds.cfg"

def convert_tlm_time(time_array):
	"""
	Converts TAI to datetime objects

	:param time_array: array of TAI times
	:return: Array of datetime objects
	"""

	# init arrays
	dtTimes = []
	dtMaxDate = dt.datetime(YEARMAX,12,31)
	dtMinDate = dt.datetime(YEARMIN,1,1)

	# loop through values
	for t in time_array:
		# convert time from TAI_EPOCH
		tmpTime = (TAI_EPOCH + dt.timedelta(seconds=t))
		# want to make sure times are valid
		# here we are ASSUMING time is between 2017 and 2020 and will error out if not
		try:
			assert dtMinDate <= tmpTime <= dtMaxDate
		except AssertionError:
			logger.fatal('AssertionError')
			# printing values for debugging
			logger.debug(t)
			logger.debug(tmpTime)
			print("AssertionError: Time is not between years "+str(YEARMIN)+" and "+str(YEARMAX))
			exit(1)
		# append to array
		dtTimes.append(tmpTime)
	return dtTimes


def get_package_item(tlm):
	"""
	Generate package and mnemonic from user input string
	:param tlm: user input string formatted as "package mnemonic" - case insensitive
	:return: package, mnemonic
	"""
	# split the string into individual words
	words = tlm.split()

	# verify user input
	try:
		assert len(words) == 2
	except AssertionError:
		logger.fatal('AssertionError')
		print('\n\n  ERROR!\n\t\"'+tlm+'\"" is not a valid input telmetry.\n\tValid input is \"package tlm_mnemonic\"')
		exit(0)

	# convert to uppercase
	package = words[0].upper()
	mnemonic = words[1].upper()

	return package, mnemonic


def validate_input(input):
	"""
	Validates user input into main function
	:param input: sys.argv array of user input
	:return: none
	"""
	# user input validation
	try:
		assert len(input) >= 4  # program name, tlm, starttime, endtime
	except AssertionError:
		logger.fatal('AssertionError')
		print("\n  Invalid Input.\n  Example:\n\tpython " + input[0] +
			  " \"package tlm_mnemonic\" [YYYY,DOY,HH,MM,SS] [YYYY,DOY,HH,MM,SS]")
		exit(0)


def ydnhms_to_datetime(t):
	"""
	Convert YDNHMS array (string) to datetime object
	YDNHMS array is an array that has the following structure - [YYYY,DOY,HH,MM,SS]
	Values DOY, HH, MM, SS can be left blank and will be assumed to be the first time available, i.e. midnight
	:param t: YDNHMS array STRING - MUST BE A STRING
	:return: datetime object
	"""

	# check the format
	m = re.search('(\[[\d, ]+\])', t)
	if not m:
		logger.fatal('Error with regex')
		print('\n  Error with time input: "'+t+'"\n  Format should be YDNHMS - [YYYY,DOY,HH,MM,SS]\n'
											   '  *Note: Fileds left blank will be assumed to be zero')
		exit(0)

	# find the values within the string
	m = re.findall('(\d+)', t)
	if not m:
		logger.fatal('Error with regex')
		print(
			'\n  Error with time input: "' + t + '"\n  Format should be YDNHMS - [YYYY,DOY,HH,MM,SS]\n'
												 '  *Note: Fileds left blank will be assumed to be zero')
		exit(0)

	# grab the year
	year = m[0]
	try:
		assert int(year) in range(YEARMIN, YEARMAX)
	except AssertionError:
		logger.fatal('AssertionError')
		print("\n  ERROR: Year \""+year+"\" is out of range. \n  Should be between "+str(YEARMIN)+" and "+str(YEARMAX))
		exit(0)

	# grab the doy or default to doy 1
	try:
		doy = m[1]
		try:
			assert int(doy) in range(0,366)
		except AssertionError:
			logger.fatal('AssertionError')
			print("\n  ERROR with DOY - Not in range(0,366)")
			exit(0)
	except IndexError:
		doy = '1'

	# grab the hours or default to 0
	try:
		hours = m[2]
		try:
			assert int(hours) in range(0,23)
		except AssertionError:
			logger.fatal('AssertionError')
			print("\n  ERROR with HOURS - Not in range(0,23)")
			exit(0)
	except IndexError:
		hours = '0'

	# grab the minutes or default to 0
	try:
		minutes = m[3]
		try:
			assert int(minutes) in range(0,59)
		except AssertionError:
			logger.fatal('AssertionError')
			print("\n  ERROR with MINUTES - Not in range(0,59)")
			exit(0)
	except IndexError:
		minutes = '0'

	# grab the seconds or default to 0
	try:
		seconds = m[4]
		try:
			assert int(seconds) in range(0,59)
		except AssertionError:
			logger.fatal('AssertionError')
			print("\n  ERROR with SECONDS - Not in range(0,59)")
			exit(0)
	except IndexError:
		seconds = '0'

	# create the timestring
	timeString = make_time_string(year,doy,hours,minutes,seconds)

	# create the datetime object
	dtTime = time_string_to_dt(timeString)

	return dtTime


def make_time_string(y,j,h,m,s):
	"""
	Converts YDNHMS values to a timestring for datetime conversion. All values given should be strings.
	:param y: year string
	:param j: doy string
	:param h: hour string
	:param m: minute string
	:param s: second string
	:return: string with format '%Y,%j,%H,%M,%S'
	"""
	return y + ',' + j + ',' + h + ',' + m + ',' + s


def time_string_to_dt(ts):
	"""
	Convert timestring generated by function make_time_string to datetime
	:param ts: timestring from make_time_string
	:return: datetime object
	"""
	return dt.datetime.strptime(ts, '%Y,%j,%H,%M,%S')


def find_files(st,et,package,tlm):
	"""
	Find files for given package and telemetry point within given timerange. Will include all files with dates within
	timerange as well as the one prior
	:param st: starttime datetime object
	:param et: endtime datetime object
	:param package: package mnemonic (all caps)
	:param tlm: telmetry point mnemonic (all caps)
	:return: array of file paths for relevant files
	"""
	# going to build directory on top of this directory:
	dir = PACKETS_DIR

	# init empty files list
	files = []
	returnFiles = []

	# loop through the immediate subdirs
	for packageDir in next(os.walk(dir))[1]:
		if packageDir == package:
			# append package directory to root dir
			dir = os.path.join(dir, packageDir)
			break

	# loop through directories in the package directory
	for tlmDir in next(os.walk(dir))[1]:
		if tlmDir == tlm:
			# append telemetry point directory to package directory
			dir = os.path.join(dir, tlmDir)
			break

	# loop through the telemetry files
	for file in next(os.walk(dir))[2]:
		# regex the file name for the correct format
		m = re.search('(\d{4})_(\d{1,3})_(\d{1,2})_(\d{1,2})_(\d{1,2})\.json',file)
		if not m:
			logger.warning("Filename: "+file+" does not match format")
			continue

		# extract the time fields
		try:
			year = m.group(1)
			doy = m.group(2)
			hour = m.group(3)
			minute = m.group(4)
			second = m.group(5)
		except IndexError:
			# if for some reason a filed is missing, present a warning and continue on
			logger.warning("Problem parsing filename: "+file)
			continue

		# generate datetime object from file time
		fileTimeString = make_time_string(year,doy,hour,minute,second)
		dtFile = time_string_to_dt(fileTimeString)

		# make a dictionary entry with path and time for later sorting
		fileDict = {"path":os.path.join(dir,file),"time":dtFile}

		# append dictionary to list
		files.append(fileDict)

	# sort the files by date
	files = sorted(files, key=lambda k: k['time'])

	# init number of files found
	numFound = 0

	# loop through files to find ones within timerange
	for i, file in enumerate(files):
		if st <= file['time'] <= et:
			if numFound == 0 and i > 0:
				# previous file could have data within specified time
				returnFiles.append(files[i-1]['path'])
			# append the good file
			returnFiles.append(file['path'])
			# increment the counter
			numFound += 1

	# make sure some files were found
	if numFound == 0:
		logger.error("Did not find any relavent files")
		exit(0)

	return returnFiles


def get_time_data(st,et,files):
	"""
	Gets the time and data from files within specified timerange
	:param st: start time datetime object
	:param et: end time datetime object
	:param files: array of file paths
	:return: time from files, data from files within timerange
	"""

	# init empty arrays
	returnData = []
	returnTime = []
	times = []
	data = []

	# loop through list of files
	for file in files:
		# open it for reading
		with open(file,'r') as f:
			# load the json data
			jsonData = json.load(f)
			# create list of values and time
			[data.append(x['val']) for x in jsonData]
			[times.append(x['t']) for x in jsonData]

	# convert times to datetime objects
	times = convert_tlm_time(times)

	# save data within timerange
	for i in range(0,len(times)):
		if st <= times[i] <= et:
			returnTime.append(times[i])
			returnData.append(data[i])

	return returnTime, returnData


def plot_data(tlm, t, d):
	"""
	Plots data and time
	:param tlm: telemetry mnemonic for the title
	:param t: datetime object array
	:param d: data
	:return: figure object
	"""
	# convert from datetime to matplotlib readable
	dates = mdates.date2num(t)

	# create the figure
	fig = plt.figure()

	# open one subplot spanning figure
	ax = fig.add_subplot(111)

	# Configure x-ticks
	ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y/%j - %H:%M:%S'))  # set x axis format
	ax.grid(True)  # turn on the grid

	# plot the data
	plt.plot_date(dates, d,
				  ls='--',
				  color='gray',
				  marker='.',
				  markerfacecolor='green',
				  markeredgecolor='green',
				  markersize=5)

	fig.autofmt_xdate(rotation=50)  # rotate the tick labels

	ax.set_title(tlm)  # sets the title of the plot

	fig.tight_layout()  # makes it so labels/ticks are not cut off
	logger.info("Showing Plot of "+tlm)

	# show the plot
	plt.show()

	return fig


def usage():
	"""
	Prints usage statement.
	:return: None.
	"""
	print("\n\npython "+sys.argv[0]+" \"package mnemonic\" [YYYY,DOY,HH,MM,SS] [YYYY,DOY,HH,MM,SS]")
	print("Required packages: matplotlib, json, re, datetime, os, sys, and logging")


def main():

	# global LOGGER
	global logger
	logger = get_logger()

	# input arguments
	try:
		tlm = sys.argv[1]
		st = sys.argv[2]
		et = sys.argv[3]
	except IndexError:
		usage()
		exit(0)

	# extract the package and mnemonic from input string
	package, mnemonic = get_package_item(tlm)

	# convert times to datetime objects
	st = ydnhms_to_datetime(st)
	et = ydnhms_to_datetime(et)

	# make sure st is less than et
	try:
		assert st < et
	except AssertionError:
		logger.fatal("Start time is greater than end time")
		print("\n  ERROR: Start time is greater than end time")
		exit(0)

	# get relavent files
	files = find_files(st,et,package,mnemonic)

	# get time and data from files within range
	t, data = get_time_data(st,et,files)

	# plot the data!
	plot_data(package+' '+mnemonic, t, data)

	logger.info(sys.argv[0]+" complete.")


if __name__ == "__main__":
	main()