import cubeds.exceptions
import cubeds.pylogger
import cubeds.decoders.base
import numpy as np


class Decoder(cubeds.decoders.base.Decoder):
    def __init__(self, raw_data, config, stats):
        # ========== Inherit base class =======================
        super().__init__(raw_data, config, stats)

        # ============= INPUT DATA CHECKS =====================
        # Check to make sure data is in the format expected!
        if type(raw_data) != list:
            raise cubeds.exceptions.DecoderDataError

        # ========== CUSTOM INIT STUFF ========================

    def decode(self):
        """
        This is where the magic happens. The cubeds.processor.Processor class will make a call to decode when it is
        looping through the yaml file. If this method is not present, there will be issues. Think of it like
        the main function. THIS FUNCTION SHALL SET `self.out_data' equal to a list with self.in_data.
        """
        self.strip_kiss()

    def strip_kiss(self):
        # KISS_FRAME_ESC 0xDB
        # KISS_TFRAME_END 0xDC
        # KISS_TFRAME_ESC 0xDD
        # KISS_FRAME_END 0xC0
        # KISS_FRAME_DATA 0x00
        for j in range(0, len(self.in_data)):
            len_packet = len(self.in_data[j])
            i = 0
            while i in range(0, len_packet - 1):
                if self.in_data[j][i] == 219:  # 0xDB
                    if self.in_data[j][i + 1] == 220:  # 0xDB 0xDC
                        self.in_data[j][i] = 220
                        self.in_data[j] = np.delete(self.in_data[j], i + 1)
                        len_packet -= 1
                    elif self.in_data[j][i + 1] == 221:  # 0xDB 0xDD
                        self.in_data[j][i] = 221
                        self.in_data[j] = np.delete(self.in_data[j], i + 1)
                        len_packet -= 1
                i += 1
        self.out_data = self.in_data