import cubeds.exceptions
import cubeds.pylogger


class Decoder:
    def __init__(self, raw_data, config, stats):
        # ========== Inherit base class =======================
        super().__init__(raw_data, config, stats)

        # ============= INPUT DATA CHECKS =====================
        # Check to make sure data is in the format expected!

        # ========== CUSTOM INIT STUFF ========================


    def decode(self):
        """
        This is where the magic happens. The cubeds.processor.Processor class will make a call to decode when it is
        looping through the yaml file. If this method is not present, there will be issues. Think of it like
        the main function. THIS FUNCTION SHALL SET `self.out_data' equal to a list with packets.
        """
        pass