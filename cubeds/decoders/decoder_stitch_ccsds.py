import cubeds.exceptions
import cubeds.pylogger
import cubeds.shared
import pandas as pd
import numpy as np
import struct
import cubeds.decoders.base


class Decoder(cubeds.decoders.base.Decoder):
    def __init__(self, raw_data, config, stats, basefile):
        # ========== Inherit base class =======================
        super().__init__(raw_data, config, stats, basefile)

        # ========== CUSTOM INIT STUFF ========================
        # None

    def decode(self):
        """
        This is where the magic happens. The cubeds.processor.Processor class will make a call to decode when it is
        looping through the yaml file. If this method is not present, there will be issues. Think of it like
        the main function. THIS FUNCTION SHALL SET `self.out_data' equal to a list with packets.
        """
        self.stitch_ccsds_new()
        self.stats.add_stat("Stitched together "+str(len(self.out_data))+" CCSDS packets")

    def stitch_ccsds_new(self):
        full_packets = []
        i = 0
        full_df = pd.DataFrame()
        while i in range(0, len(self.in_data)):
            try:
                ccsds_header = cubeds.shared.extract_CCSDS_header(self.in_data[i])
            except IndexError:
                i += 1
                continue
            except struct.error:
                i += 1
                continue
            ccsds_header['index'] = i
            tmp_df = pd.DataFrame([ccsds_header], columns=ccsds_header.keys())
            full_df = full_df.append(tmp_df)
            i += 1

        in_packet = False
        cur_seq = -1
        packet = []

        for i, df in full_df.sort_values(by=['sequence']).iterrows():
            # Check is packet is unsegmented, i.e. grouping flag == 3.
            packet_unsegmented = True if df['grouping_flags'] == 3 else False
            if packet_unsegmented:
                length = df['length'] + df['header_length'] - 5
                packet = self.in_data[df['index']][0:length]
                full_packets.append(packet)
                continue

            # the grouping flag 1 means that it is the start of packet
            if df['grouping_flags'] == 1:
                if in_packet:
                    self._logger.verbose("Decoded a partial packet.")
                    full_packets.append(packet)
                in_packet = True
                cur_seq = df['sequence']
                length = df['length'] + df['header_length']-5
                packet = self.in_data[df['index']][0:length]
                continue

            elif df['grouping_flags'] == 0:
                if not in_packet:
                    self._logger.verbose("Missing the first sequence of the frame.")
                    continue
                if df['sequence'] != cur_seq + 1:
                    self._logger.verbose("Missing sequence number: "+str(cur_seq+1))
                    full_packets.append(packet)
                    continue
                cur_seq += 1
                mid_length = df['length'] + df['header_length'] + 1
                if len(packet):
                    packet = np.append(packet, self.in_data[df['index']][df['header_length']:mid_length])
                    continue
                else:
                    self._logger.error("Should have never reached this line of code.")

            elif df['grouping_flags'] == 2:
                if not in_packet:
                    self._logger.verbose("Missing the first sequence of the frame.")
                    continue
                if df['sequence'] != cur_seq + 1:
                    self._logger.verbose("Missing sequence number: " + str(cur_seq + 1))
                    full_packets.append(packet)
                    continue
                in_packet = False
                end_length = df['length'] + df['header_length'] + 1
                if len(packet):
                    packet = np.append(packet, self.in_data[df['index']][df['header_length']:end_length])
                    full_packets.append(packet)
                else:
                    self._logger.error("Should have never reached this line of code.")
    
        self.out_data = full_packets
