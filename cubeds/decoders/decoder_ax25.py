import cubeds.exceptions
import cubeds.pylogger
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
        if type(self.in_data) != np.ndarray:
            raise cubeds.exceptions.DecoderDataError

        # ========== CUSTOM INIT STUFF ========================
        self.packets = []

    def decode(self):
        """
        This is where the magic happens. The cubeds.processor.Processor class will make a call to decode when it is
        looping through the yaml file. If this method is not present, there will be issues. Think of it like
        the main function. THIS FUNCTION SHALL SET `self.out_data' equal to a list with packets.
        """
        self.extract_ax25_packets()
        self.strip_ax25()

    def extract_ax25_packets(self):
        header = np.array(bytearray.fromhex(self.config.config['decoders'][self.yaml_key]['decoder_ax25']['frame']))
        header_len = len(header)
        inds = []
        ax25_packets = []
        data = self.in_data

        for x in range(0, len(data-header_len)):
            if np.all(data[x:x+header_len] == header):
                inds.append(x)

        for x in range(0, len(inds)-1):
            ax25_packets.append(data[inds[x]:inds[x+1]])
        self.packets = ax25_packets

    def strip_ax25(self):
        header_len = self.config.config['decoders'][self.yaml_key]['decoder_ax25']['header_length']
        for i in range(0, len(self.packets)):
            self.packets[i] = self.packets[i][header_len:]

        self.out_data = self.packets
