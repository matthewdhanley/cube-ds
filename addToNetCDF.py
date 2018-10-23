from netCDF4 import Dataset
import os
#import pickle

#Adds telemetry points to net cdf file.
#Srikanth Venkataraman
#Call the addData function with inputs data and filename
#filename is a string containing the name of the existing file or file to be created
# data is a dictionary where the keys are times as a string and the values are dictionaries containing the telemetry points.
#ex: data = {'3':{'tp1':2,'tp2':2.04,'tp3':'hi'},'1':{'tp1':3,'tp2':3.04,'tp3':'hello'},'10':{'tp1':3,'tp2':6.04,'tp3':'no'}}


#Creates netcdf file if none exists
def createFile(filename):
	mainGroup = Dataset(filename, "w", format="NETCDF4")
	time = mainGroup.createDimension("time",None)
	times = mainGroup.createVariable("time", "f8",("time"))
	mainGroup.close()
#Adds each telem point to the file
def addPoint(points,timeIndex,mainGroup):
	#
	times = mainGroup.variables['time']
	length = len(mainGroup.dimensions['time'])

	for key in points:
		#Checks if telem point name has been added
		if key in mainGroup.variables.keys():
			# If it has, retrieve it.
			datapt = mainGroup.variables[key]
		else:
			#If not, create it. 
			if isinstance(points[key], str): 
				datapt = mainGroup.createVariable(key, str,("time"))
			else:
				datapt = mainGroup.createVariable(key, 'f8',("time"))
		#Assign time and data values
		datapt[length] = points[key]
		times[length] = timeIndex
		

# def load_obj(name ):
#     with open(  name + '.pkl', 'rb') as f:
#         return pickle.load(f)


# tdata = load_obj('testdata')
# print(tdata['590147175'])

def addData(data,filename):
	fileExists = os.path.isfile(filename)
	if not fileExists:
		createFile(filename)
	data = {int(key):data[key] for key in data}
	#Sort data chronologically
	sortedData = sorted(data.items())
	#Get dataset
	mainGroup = Dataset(filename, "a", format="NETCDF4")
	for i in range(0,len(sortedData)):

		timeIndex = sortedData[i][0]
		addPoint(sortedData[i][1],timeIndex,mainGroup)
	mainGroup.close()





