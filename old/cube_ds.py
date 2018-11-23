import numpy as np
import logging
import logging.config
import struct
import json
import csv
import re
import os
import configparser
import pprint

CONFIG_FILE = "cube_ds.cfg"
decimation = 100  # hertz

class HeaderFormat():
    def __init__(self):
        # setup struct.unpack formats for each section of the ccsds header
        self.format = '>BBHHIBx'
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
        m = re.search('([a-zA-Z]+)_([a-zA-Z\d]{2})_([a-zA-Z\d]{2})\.csv', filename)

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
        logger.info('parsing file '+self.filename+'...')

        # read in the file as big endian binary
        self.rawData = np.fromfile(filename, dtype='>B')
        # todo consider adding exception here for files that don't exist

        # get the size of the file
        self.fileSize = os.stat(filename).st_size
        self.packets = packets
        self.header = HeaderFormat()

        # no longer any sync frames!!!!!!!! todo use length field instead?
        # self.syncSize = len(self.header.sync)
        # self.syncPossible = np.where(self.rawData == self.header.sync[0])[0]

        self.Packets = []
        self.frames = []
        self.headerList = []
        self.parseFile()

    def parseFile(self):
        lastLogTime = 0
        firstFlag = 1

        # the first data in the file should be the beginning of a CCSDS File. It should be spaced as follows
        '''
        Byte 0  - Tlm APID           - Size: 2 bytes.
        Byte 2  - Tlm Sequence Count - Size 2 bytes.
        Byte 4  - Tlm Length         - Size 2 Bytes.
        Byte 6  - Tlm Time Sec       - Size 4 Bytes.
        Byte 10 - Tlm Time Sub Sec   - Size 1 byte.
        Byte 11 - Tlm Reserved       - Size 1 Byte.
        '''

        size_flag = 0
        current_location = 0
        offset_into_packet = 8
        while current_location < self.fileSize and not size_flag:
            newHeader = self.unpackHeader(current_location)
            tmp_location = current_location + newHeader.length + offset_into_packet - 1
            if tmp_location + self.header.size > self.fileSize:
                size_flag = 1
                break
            tmpHeader = self.unpackHeader(tmp_location)
            good_frame = 0
            for packet in self.packets:
                if tmpHeader.apid1 == packet.apid1[0] and tmpHeader.apid2 == packet.apid2[0]:
                    good_frame = 1
                    continue
            while good_frame == 0 and not size_flag:
                current_location += 1
                newHeader = self.unpackHeader(current_location)
                for packet in self.packets:
                    if newHeader.apid1 == packet.apid1[0] and newHeader.apid2 == packet.apid2[0]:
                        tmp_location = current_location + newHeader.length + offset_into_packet - 1
                        if tmp_location > self.fileSize:
                            size_flag = 1
                            break
                        tmpHeader = self.unpackHeader(tmp_location)
                        for packet in self.packets:
                            if tmpHeader.apid1 == packet.apid1[0] and tmpHeader.apid2 == packet.apid2[0]:
                                good_frame = 1
                                continue
            if good_frame:
                self.headerList.append(newHeader)
                current_location += self.headerList[-1].length + offset_into_packet - 1
                if current_location > self.fileSize:
                    size_flag = 1

                for packet in self.packets:
                    if self.headerList[-1].apid1 == packet.apid1[0] and self.headerList[-1].apid2 == packet.apid2[0]:
                        if self.headerList[-1].sec - lastLogTime < 1.0/decimation:
                            continue
                        lastLogTime = self.headerList[-1].sec
                        offset = current_location + self.header.size+4
                        # TODO - figure out why buffer size is not matching format size.
                        if offset+packet.size > self.fileSize:
                            size_flag = 1
                            break
                        packetDataList = struct.unpack(packet.format, self.rawData[offset:offset+packet.size])
                        for i, point in enumerate(packet.points):
                            tmpJSON = tlmJSON(point,self.headerList[-1].sec,packetDataList[i], self.headerList[-1].apid1, self.headerList[-1].apid2)
                            if not firstFlag:
                                point.file.write(',\n')
                            point.file.write(json.dumps(tmpJSON, indent=4))
                        if firstFlag:
                            firstFlag = 0

            else:
                logger.error("Couldn't find any more good frames.")

    def unpackHeader(self, syncInd):
        newHeader = Header()
        fieldList = struct.unpack(self.header.format, self.rawData[syncInd:syncInd+self.header.size])
        newHeader.setFields(fieldList)
        return newHeader


def tlmJSON(point,time,value,apid1,apid2):
    return {"t": time, "val": value*point.conversion, "apid1": apid1, "apid2": apid2}

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


def get_logger():
    """
    Create a logging object for easy logging
    :return: logging object
    """
    # set up LOGGER from config file
    if os.path.isfile(CONFIG_FILE):
        logging.config.fileConfig(CONFIG_FILE)
        logger = logging.getLogger('cube_ds')
    else:
        # use defaults if no config file
        format = '%(asctime)s - %(filename)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s'
        logging.basicConfig(format=format)
        logger = logging.getLogger('cube_ds')
        logger.warning(CONFIG_FILE+' not found. Using defaults for logging.')

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
    # global LOGGER
    global logger
    logger = get_logger()
    config = configparser.ConfigParser()
    config.read('cube_ds.cfg')
    # get filename from user, auto, or hard coded
    # hardcode:
    #rawFiles = ["D:\\bct_2018_229_08_32_19"]
    #rawFiles = ["D:\\bct_2018_228_13_32_43"]
    rawFiles = []

    logger.debug(config)

    for root, directories, filenames in os.walk(config['rundirs']['location']):
        for filename in filenames:
            m = re.search('bct_\d{4}.*',filename)
            if m:
                rawFiles.append(os.path.join(root,filename))


    definitionLocaiton = config['tlm_defs']['location']
    if not os.path.exists(definitionLocaiton):
        logger.fatal("Telemetry Definition Directory does not exits. Check config file.")
        exit(0)

    tlmFiles = []
    for root, directories, filenames in os.walk(config['tlm_defs']['location']):
        for filename in filenames:
            m = re.search('[A-Za-z]+_[0-9a-zA-Z]{2}_[0-9a-zA-Z]{2}\.csv', filename)
            if m:
                tlmFiles.append(os.path.join(root, filename))

    if not tlmFiles:
        logger.fatal("Could not find any definition files.")
        exit(0)

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
        m = re.search('bct_(\d{4}.*)', rawFile)
        suffix = m.group(1)
        for packet in packets:
            packet.genFileNames(suffix)
        file = RawFile(rawFile, packets)
        for packet in packets:
            packet.closeFiles()

        # log the file as processed
        fileLog = open(processLog, mode='a')
        # fileLog.write(rawFile+'\n')
        fileLog.close()

    logger.info('Done!')

if __name__=="__main__":
    main()