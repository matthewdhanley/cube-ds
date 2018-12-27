import cubeds.exceptions
import cubeds.pylogger
import cubeds.shared
import pandas as pd
import numpy as np
import cubeds.decoders.base


class Decoder(cubeds.decoders.base.Decoder):
    def __init__(self, raw_data, config, stats):
        # ==========Inherit the base class ====================
        super().__init__(raw_data, config, stats)

        # ========== CUSTOM INIT STUFF ========================
        # None

    def decode(self):
        """
        This is where the magic happens. The cubeds.processor.Processor class will make a call to decode when it is
        looping through the yaml file. If this method is not present, there will be issues. Think of it like
        the main function. THIS FUNCTION SHALL SET `self.out_data' equal to a list with packets.
        """
        self.stitch_ccsds_new()

    def stitch_ccsds_new(self):
        full_packets = []
        i = 0
        full_df = pd.DataFrame()
        while i in range(0, len(self.in_data)):
            ccsds_header = cubeds.shared.extract_CCSDS_header(self.in_data[i])
            ccsds_header['index'] = i
            tmp_df = pd.DataFrame([ccsds_header], columns=ccsds_header.keys())
            full_df = full_df.append(tmp_df)
            i += 1
    
        try:
            unique_seqs = full_df.sequence.unique()
        except AttributeError as e:
            self._logger.info(e)
            return full_packets
    
        for seq in unique_seqs:
            parts_df = full_df[full_df['sequence'] == seq]
            packet_beginning_ind = parts_df[parts_df['grouping_flags'] == 1]
            if packet_beginning_ind.empty:
                self._logger.debug("No start of packet found")
                continue
    
            packet_middle_inds = parts_df[parts_df['grouping_flags'] == 0]
    
            packet_end_ind = parts_df[parts_df['grouping_flags'] == 2]
    
            start_ind = packet_beginning_ind['index'].values
            if len(start_ind) > 1:
                self._logger.debug("Multiple frame starts at sequence number "+str(seq))
                self._logger.debug("using the first one.")
    
            start_ind = start_ind[0]
    
            length = packet_beginning_ind['length'].values[0] + packet_beginning_ind['header_length'].values[0]-5
            packet = self.in_data[start_ind][0:length]
    
            if not packet_middle_inds.empty:
                print("APPEND MIDDLE PACKETS")
                exit(1)
    
            if packet_end_ind.empty:
                self._logger.debug("No end of packet found for sequence number "+str(seq))
                full_packets.append(packet)
                continue
    
            end_ind = packet_end_ind['index'].values
            if len(end_ind) > 1:
                self._logger.debug("Multiple frame ends for sequnce number "+str(seq))
                self._logger.debug("using the first one.")
    
            end_ind = end_ind[0]
            length = packet_end_ind['length'].values[0] + packet_end_ind['header_length'].values[0]+1
            packet = np.append(packet, self.in_data[end_ind][packet_end_ind['header_length'].values[0]:length])
    
            full_packets.append(packet)
    
        self.out_data = full_packets