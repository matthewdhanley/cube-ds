import cubeds.exceptions
import cubeds.pylogger
import cubeds.helpers
import cubeds.shared
import struct
import pandas as pd
import numpy as np


class Decoder:
    def __init__(self, raw_data, config, stats):
        # ================= DO NOT CHANGE =====================
        self.in_data = raw_data
        self.out_data = []
        self.config = config
        self.yaml_key = self.config.yaml_key
        self._logger = cubeds.pylogger.get_logger(__name__)
        self.stats = stats

        # ============= INPUT DATA CHECKS =====================
        # Check to make sure data is in the format expected!
        if type(self.in_data) != list:
            raise cubeds.exceptions.DecoderDataError

        # ========== CUSTOM INIT STUFF ========================
        self.packets = []
        self.tlm = []
        self.tlm_df = pd.DataFrame()

    def decode(self):
        """
        This is where the magic happens. The cubeds.processor.Processor class will make a call to decode when it is
        looping through the yaml file. If this method is not present, there will be issues. Think of it like
        the main function. THIS FUNCTION SHALL SET `self.out_data' equal to a list with packets.
        """
        self.sort_packets()
        self.extract_tlm_from_sorted_packets()
        self.tlm_to_df()

    def sort_packets(self):
        packets_sorted = {}
        strip_length = 12
        for packet in self.in_data:
            header = cubeds.shared.extract_CCSDS_header(packet)
            try:
                packet_id = str(header['apid'])
            except IndexError:
                self._logger.debug("Packet wayyyyy too short.")
                continue

            if packet_id == '255':
                packet = packet[strip_length:]
                header = cubeds.shared.extract_CCSDS_header(packet)
                packet_id = str(header['apid'])

            if packet_id in packets_sorted:
                packets_sorted[packet_id]['raw_packets'].append(packet)
            else:
                packets_sorted[packet_id] = {}
                packets_sorted[packet_id]['raw_packets'] = [packet]
        self.packets = packets_sorted
        self.assign_csv_info()

    def extract_tlm_from_sorted_packets(self):
        """
        Extracts telemetry from packets that are sorted in a dictionary
        :return: gia
        """
        out_data = []
        bad_packets = 0
        for key in self.packets:
            try:
                csv_info = self.packets[key]['csv_info']
            except KeyError:
                self._logger.info("No packet def found. Continuing")
                continue
            points_file = csv_info['pointsFile']

            # if the file wasn't found, send message to user and exit
            if points_file == '':
                self._logger.error('error finding points definitions for packet ' + csv_info['packetName'])
                raise cubeds.exceptions.TelemetryError(msg='error finding points definitions for packet '
                                                           + csv_info['packetName'])

            # extract the telemetry points from the file
            tlm_points = cubeds.helpers.get_tlm_points(points_file, self.config)
            for data in self.packets[key]['raw_packets']:
                if not len(data):
                    continue
                tmp_data = self.extract_data(data, tlm_points, csv_info)
                if not tmp_data:
                    bad_packets += 1
                    continue
                out_data.append(tmp_data)
        if bad_packets and len(out_data):
            self.stats.add_stat("Removed " + str(bad_packets) + " corrupted packets with out of range data.")
        if len(out_data) == 0:
            self._logger.warning("Did not extract any data from this file")
            self.stats.add_stat("No data extracted.")
        self.tlm = out_data

    def extract_data(self, data, tlm_points, csv_info):
        extracted_data = {}
        for point in tlm_points:
            # get start bit and start byte for data extraction
            startByte = int(point['startByte'])
            startBit = int(point['startBit'])

            extract_bits_length = 0

            # size is needed for selecting the right amount of data
            tlm_length = int(point['size'])

            # need a check to see if the length is less than one byte
            # python can only grab one byte at a time
            if tlm_length < 8:
                extract_bits_length = tlm_length
                tlm_length = 8

            # conver the conversion to a float
            conversion = float(point['conversion'])

            # get the datatype
            dtype = point['dtype']

            header_length = 0
            # TODO | Header length changes for payload packets. Need to extract little endian seconds as the key for below.
            # TODO | This might be tricky . . .
            # TODO | what if we just didn't remove the header and incorporated it into the tlm map? That might make the
            # TODO | most sense. But then the issue arises that the initial apid extraction might not be as robust due
            # TODO | to changing length header fields. Might want to consider decoder config csv files like hydra...

            # get the relavent data from the packet
            tlmData = data[header_length + startByte:header_length + startByte + tlm_length // 8]

            if point['endian']:
                endian = point['endian']
            else:
                endian = 'big'

            # generate a format string for struct.unpack
            unpack_data_format = cubeds.helpers.get_unpack_format(dtype, tlm_length, endian=endian)
            # try to unpack the data (if it's not a char, chars are having issues?)

            if point['dtype'] != 'char':
                try:
                    tlm_value = struct.unpack(unpack_data_format, tlmData)[0] * conversion
                except struct.error as e:
                    # not extracting the right amount of data. Print some debug information and move on
                    self._logger.debug("Packet ended unexpectedly.")
                    self._logger.debug(e)
                    self._logger.debug(point['name']+" is the point it ended on")
                    try:
                        extracted_data['time_index'] = extracted_data[csv_info['time_index']]
                    except KeyError:
                        self._logger.debug("No data found for time index: " + csv_info['time_index'])
                        return []
                    except NameError:
                        self._logger.warn("Something bad may be going on here . . .")
                        return []
                    self._logger.debug("Extracted a partial packet, at least!")
                    return extracted_data
                except TypeError as e:
                    # had an issue with types. Print debug info and exit. This is a more serious issue.
                    print(point)
                    print(tlm_value)
                    print(e)
                    raise cubeds.exceptions.TelemetryError

                if extract_bits_length > 0:
                    tlm_value = cubeds.helpers.extract_bits(int(tlm_value), startBit, length=extract_bits_length)

            else:
                self._logger.error("DTYPE IS CHAR, WHY YOU NOT DECODE?")

            # index into the struct and save the value for the tlm point
            if self.config.clean:
                if point['min'] and float(point['min']) > tlm_value:
                    self._logger.debug("throwing away packet")
                    self._logger.debug("Point: "+point['name'])
                    self._logger.debug("Value: "+str(tlm_value))
                    return []
                if point['max'] and float(point['max']) < tlm_value:
                    self._logger.debug("throwing away packet")
                    self._logger.debug("Point: " + point['name'])
                    self._logger.debug("Value: " + str(tlm_value))
                    return []
            extracted_data[point['name']] = tlm_value

        try:
            extracted_data['time_index'] = extracted_data[csv_info['time_index']]
        except KeyError:
            self._logger.debug("No data found for time index: "+csv_info['time_index'])
            return []
        except NameError:
            self._logger.warn("Something bad may be going on here . . .")
            return []

        return extracted_data

    def tlm_to_df(self):
        """
        Converts telemetry dictionary to a dataframe
        :return:
        """
        if type(self.tlm) != list:
            raise cubeds.exceptions.DecoderError("Input to tlm_to_df is not a list.")

        if self.tlm:
            df = pd.DataFrame(self.tlm).sort_values(by=['time_index'])
        else:
            self._logger.warning("No data found. Returning empty dataframe")
            return pd.DataFrame()
        try:
            df = df.dropna()
            df['time_index'] = df['time_index'].map(lambda x: int(x))
        except ValueError as e:
            self._logger.debug(e)
            self._logger.warning("Returning empty dataframe")
            return pd.DataFrame()
        self.out_data = df

    def assign_csv_info(self):
        # returned a list of dicts
        csv_info = cubeds.helpers.get_csv_info(self.config)
        for key in self.packets:
            for a in csv_info:
                if key == a['apid']:
                    self.packets[key]['csv_info'] = a

