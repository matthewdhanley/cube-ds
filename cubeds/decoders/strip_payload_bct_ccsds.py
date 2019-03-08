import cubeds.exceptions
import cubeds.pylogger
import cubeds.decoders.base
import cubeds.shared
import struct


class Decoder(cubeds.decoders.base.Decoder):
    def __init__(self, raw_data, config, stats, basefile):
        # ========== Inherit base class =======================
        super().__init__(raw_data, config, stats, basefile)

        # ============= INPUT DATA CHECKS =====================
        # Check to make sure data is in the format expected!

        # ========== CUSTOM INIT STUFF ========================

    def decode(self):
        """
        This is where the magic happens. The cubeds.processor.Processor class will make a call to decode when it is
        looping through the yaml file. If this method is not present, there will be issues. Think of it like
        the main function. THIS FUNCTION SHALL SET `self.out_data' equal to a list with packets.
        """
        self.strip_ccsds()

    def strip_ccsds(self):
        strip_len = int(self.config.config['decoders'][self.config.yaml_key]['strip_payload_bct_ccsds']['strip_len'])
        for packet in self.in_data:
            try:
                header = cubeds.shared.extract_CCSDS_header(packet[0:20])
            except struct.error as e:
                self._logger.debug(e)
                continue
            except IndexError as e:
                self._logger.debug(e)
                continue

            if header['apid'] == self.config.config['decoders'][self.config.yaml_key]['strip_payload_bct_ccsds']['apid']:
                self.out_data.append(packet[strip_len:-1])
            else:
                self.out_data.append(packet)
