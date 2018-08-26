import numpy as np
import logging
import logging.config
import struct
import json
import csv
import re
import os
import configparser


decimation = 0.5  # hertz


class HeaderFormat():
	def __init__(self, sync=[53,46,248,83]):
		self.sync = np.array(sync, dtype='>B')  # set the sync frame

		# setup struct.unpack formats for each section of the ccsds header
		self.format = '>BBHHLBx'
		self.size = 12  # not including sync
						# TODO - update to be dynamic


class Header():
	def __init__(self):
		self.apid1 = -1
		self.apid2 = -1
		self.seqCount = -1
		self.length = -1
		self.sec = -1
		self.subSec = -1

	def setFields(self,fieldList):
		self.apid1 = fieldList[0]
		self.apid2 = fieldList[1]
		self.seqCount = fieldList[2]
		self.length = fieldList[3]
		self.sec = fieldList[4]
		self.subSec = fieldList[5]
		# self.checkFields()

	def checkFields(self):
		for obj in dir(self):
			if not callable(getattr(self,obj)) and not obj.startswith("__"):
				if obj == -1:
					logger.error("Invalid Field in Header")

	def serialize(self):
		jDump = json.dumps(["ccsds",self], default=lambda o: o.__dict__,sort_keys=False, indent=4)
		return jDump


class TelemetryFile():
	def __init__(self, filename,packetFileLocation):
		self.filename = filename
		self.packetLoc = packetFileLocation
		# should be formatted packetname_apid1_apid2.csv
		# i.e. fsw_09_3e.csv
		m = re.search('([a-zA-Z]+)_([a-zA-Z\d]{2})_([a-zA-Z\d]{2})\.csv',filename)

		# try to extract the fields
		try:
			self.packetName = m.group(1)
			self.apid1 = m.group(2)
			self.apid2 = m.group(3)
		except AttributeError:
			# throw a custom error
			raise ParseError('CSV telemetry filename incorrectly formatted',filename)

		logger.info('parsing file '+self.filename)

		# create new packet
		self.packet = Packet(self.packetName, [self.apid1,self.apid2])

		self.extractFrames()
		self.packet.generateFormat()


	def extractFrames(self):
		with open(self.filename) as csvfile:
			reader = csv.DictReader(csvfile)
			firstIteration = 1
			for row in reader:
				# create telemetry point object
				tlmPoint = TlmPoint(row)
				if firstIteration:
					firstIteration = 0
					prevPoint = tlmPoint
				byteGap = tlmPoint.byte - prevPoint.byte
				if byteGap > prevPoint.size:
					byteGap -= prevPoint.size
					# we need padding.
					padPoint = PadPoint(byteGap, prevPoint.byte+prevPoint.size)
					self.packet.frames[-1].addPoint(padPoint)

				# init that we haven't found the frame yet
				currentFrame = None

				# loop through the frames
				for frame in self.packet.frames:
					if frame.name == row['packet']:
						# add the tlm point
						tlmPoint.setFrameLoc(frame.frameLoc)
						frame.addPoint(tlmPoint)
						currentFrame = frame
						break

				if not currentFrame:
					currentFrame = Frame(row['packet'],self.packetLoc)
					# add the tlm point
					tlmPoint.setFrameLoc(currentFrame.frameLoc)
					currentFrame.addPoint(tlmPoint)
					self.packet.addFrame(currentFrame)
					# didn't find the frame, so make a new one

				prevPoint = tlmPoint

class RawFile():
	def __init__(self, filename, packets):
		self.filename = filename
		self.rawData = np.fromfile(filename, dtype='>B')
		# consider adding exception here for files that don't exist
		self.fileSize = self.rawData.__sizeof__
		self.packets = packets
		logger.info('parsing file '+self.filename)
		self.header = HeaderFormat()
		self.syncSize = len(self.header.sync)
		self.syncPossible = np.where(self.rawData == self.header.sync[0])[0]
		self.Packets = []
		self.frames = []
		self.headerList = []
		self.parseFile()

	def parseFile(self):
		lastLogTime = 0
		firstFlag = 1
		for syncInd in self.syncPossible:
			check = self.rawData[syncInd:syncInd+self.syncSize]
			if np.all(check == self.header.sync):
				# we've found a frame
				self.unpackHeader(syncInd)
				for packet in self.packets:
					if self.headerList[-1].apid1 == packet.apid1[0] and self.headerList[-1].apid2 == packet.apid2[0]:
						if self.headerList[-1].sec - lastLogTime < 1.0/decimation:
							continue
						lastLogTime = self.headerList[-1].sec
						offset = syncInd+self.header.size+4
						# TODO - figure out why buffer size is not matching format size.
						packetDataList = struct.unpack(packet.format, self.rawData[offset:offset+packet.size])
						for i,point in enumerate(packet.points):
							tmpJSON = tlmJSON(point,self.headerList[-1].sec,packetDataList[i])
							if not firstFlag:
								point.file.write(',\n')
							point.file.write(json.dumps(tmpJSON, indent=4))
						if firstFlag:
							firstFlag = 0

	def unpackHeader(self, syncInd):
		newHeader = Header()
		# newHeader.syncFrame = self.rawData[syncInd:syncInd+self.syncSize]
		syncInd += self.syncSize
		testlist = []
		# newHeader.apid1, newHeader.apid2, newHeader.seqCount, new, _, _  = struct.unpack(self.header.format,self.rawData[syncInd:syncInd+self.header.size])
		fieldList = struct.unpack(self.header.format,self.rawData[syncInd:syncInd+self.header.size])
		newHeader.setFields(fieldList)
		self.headerList.append(newHeader)
				

def tlmJSON(point,time,value):
	return {"t":time,"val":value*point.conversion}

class Packet():
	def __init__(self, name, id):
		# set the packet ID
		self.apid1 = bytearray.fromhex(id[0])
		self.apid2 = bytearray.fromhex(id[1])

		# set packet name
		self.name = name
		
		# create the header
		# todo - make generic 
		self.header = Header()

		self.headerFormat = HeaderFormat()

		# list of frames - start with the header!
		self.frameFormats = [self.headerFormat.format]
		self.frameSizes = [self.headerFormat.size]  # might not need this. Can gather from frame format
		self.frames = []
		self.points = []


		# packet raw size in bytes
		self.size = 0

	def addFrame(self, frame):
		self.frames.append(frame)
		self.generateFormat()

	def genFileNames(self,suffix):
		for point in self.points:
			point.genFileName(suffix)

	def closeFiles(self):
		for point in self.points:
			point.file.truncate()
			point.file.write(']')  # terminate the json
			point.file.close()

	def generateFormat(self):
		format = '>'
		size = 0
		points = []
		for frame in self.frames:
			format += frame.format
			size += frame.size
			for point in frame.points:
				if point.index >= 0:
					points.append(point)
		self.points = points
		self.format = format
		self.size = size


class Frame():
	def __init__(self, name, packetLoc):
		self.name = name
		self.size = 0
		self.points = []
		self.packetLoc = packetLoc
		self.frameLoc = self.packetLoc+'\{0}'.format(self.name)
		if not os.path.exists(self.frameLoc):
			os.makedirs(self.frameLoc)

	# add a tlm point to the frame.
	def addPoint(self,point):
		self.points.append(point)
		self.generateFormat()

	def generateFormat(self):
		format = ''
		prevByte = -1
		prevValidByte = 0
		prevValidSize = 0
		frameBytes = []
		frameEnd = 0
		index = 0
		for point in self.points:
			# no repeat bytes
			frameBytes.append(point.byte)
			if point.byte-prevByte > 0 and point.byte - prevValidByte - prevValidSize >= 0:
				format += point.format
				point.index = index
				index += 1
				prevValidByte = point.byte
				prevValidSize = point.size
			else:
				point.index = -1
			if point.name == 'padding':
				point.index = -1
			prevByte = point.byte
			pointEnd = point.byte + point.size
			if pointEnd > frameEnd:
				frameEnd = pointEnd
			
		self.format = format
		self.size = frameEnd - min(frameBytes)
			

class PadPoint():
	def __init__(self,size,byte):
		self.name = 'padding'
		self.byte = byte
		self.bit = 0
		self.conversion = 1
		self.tlmType = 'int-1'  # uint8, float, etc.
		self.format = str(size)+'x'
		self.size = size
		self.index = -1


class TlmPoint():
	def __init__(self,tlmDict,size=0):
		self.name = tlmDict['point']
		self.frameLoc = None
		self.tlmLoc = None
		self.file = None
		self.index = -1
		self.byte = int(tlmDict['byte'])
		self.bit = int(tlmDict['bit'])  # will default to 0
		self.frame = tlmDict['packet']
		self.conversion = float(tlmDict['conversion'])
		self.tlmType = tlmDict['type']  # uint8, float, etc.
		self.conversion = float(tlmDict['conversion'])
		self.format = ''
		self.size = size
		self.generateFormat()
		self.endByte = self.byte + self.size # need 


	def setFrameLoc(self,frameLoc):
		self.frameLoc = frameLoc
		self.tlmLoc = self.frameLoc + '\{0}_no_date'.format(self.name)

	def genFileName(self,suffix):
		if not self.frameLoc:
			logger.fatal("fatal error :(")
			exit(1)
		self.tlmLoc = self.frameLoc + '\{0}'.format(self.name)
		self.tlmLocFile = self.tlmLoc + '\\'+suffix+'.json'
		if not os.path.exists(self.tlmLoc):
			os.makedirs(self.tlmLoc)
		self.file = open(self.tlmLocFile,'w')
		self.file.write('[')  # start the json

	def generateFormat(self):
		m = re.search('([a-zA-Z]+)(\-*\d+)', self.tlmType)
		try:
			dataType = m.group(1)
			dataSize = int(m.group(2))
		except AttributeError:
			raise ParseError('Error parsing data type while using regex', dtype)
		
		size = 0
		
		if dataSize == 1:
			# bit
			letter = 'b'
			size = 1
		elif dataSize == 3:
			# for some reason there is a datapoint that is 3 bits...
			letter = 'b'
			dataType = 'uint' # spoof next part
			size = 1
		elif dataSize == 8:
			# char
			letter = 'b'
			size = 1
		elif dataSize == 16:
			# short
			letter = 'h'
			size = 2
		elif dataSize == 32:
			# int
			letter = 'i'
			size = 4
		elif dataSize == 64:
			# long long
			letter = 'q'
			size = 8
		elif dataSize == -1:
			# padding
			letter = str(self.size)+'x'  # want self.size bytes of padding
			dataType = 'int'
			size = 1
		else:
			raise ParseError('Error parsing data type size', dtype)

		if dataType == 'uint':
			letter = letter.upper()
		elif dataType == 'int':
			letter = letter.lower()
		elif dataType == 'string':
			
			letter = str(int(dataSize/8)) + 's'
		elif dataType == 'float':
			letter = 'd'
		else:
			raise ParseError('Error parsing data type', dtype)

		# going to take care of this in Packet object
		# letter = '>' + letter  # for big endian

		self.format = letter
		if self.size == 0:
			self.size = size


def getLogger():
	# set up logger
	logging.config.fileConfig('cube_ds.cfg')
	logger = logging.getLogger('cube_ds')

	logger.info('Logger started.')
	return logger


class Error(Exception):
    pass


class ParseError(Error):
    """Exception raised for errors in the input.

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """

    def __init__(self, message, expression):
        self.expression = expression
        self.message = message


def main():
	# global logger
	global logger
	logger = getLogger()
	config = configparser.ConfigParser()
	config.read('cube_ds.cfg')
	# get filename from user, auto, or hard coded
	# hardcode:
	#rawFiles = ["D:\\bct_2018_229_08_32_19"]
	#rawFiles = ["D:\\bct_2018_228_13_32_43"]
	rawFiles = []

	for root, directories, filenames in os.walk(config['rundirs']['location']):
		for filename in filenames:
			m = re.search('bct_\d{4}.*',filename)
			if m:
				rawFiles.append(os.path.join(root,filename))

	tlmFiles = ["D:\\fsw_08_3e.csv"]
	packetFileLocation = config['telemetry']['location']
	if not os.path.exists(packetFileLocation):
		os.makedirs(packetFileLocation)

	packets = []

	for tlmFile in tlmFiles:
		# open the file and read in the frames/points
		f = TelemetryFile(tlmFile,packetFileLocation)
		packets.append(f.packet)

	processLog = config['process_log']['location']

	# loop through the files
	for rawFile in rawFiles:
		# don't process file twice.
		fileReadLog = open(processLog, mode='r')
		foundFlag = 0
		for line in fileReadLog:
			if line.rstrip() == rawFile:
				foundFlag = 1
		fileReadLog.close()
		if foundFlag:
			continue

		# open the files
		m = re.search('bct_(\d{4}.*)',rawFile)
		suffix = m.group(1)
		for packet in packets:
			packet.genFileNames(suffix)
		file = RawFile(rawFile, packets)
		for packet in packets:
			packet.closeFiles()

		# log the file as processed
		fileLog = open(processLog, mode='a')
		fileLog.write(rawFile+'\n')
		fileLog.close()

	logger.info('Done!')

if __name__=="__main__":
	main()