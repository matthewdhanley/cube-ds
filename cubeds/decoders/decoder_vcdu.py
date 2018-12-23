import cubeds.exceptions
import cubeds.pylogger
import cubeds.helpers
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
        self.vcdu_packets = []

    def decode(self):
        """
        This is where the magic happens. The cubeds.processor.Processor class will make a call to decode when it is
        looping through the yaml file. If this method is not present, there will be issues. Think of it like
        the main function. THIS FUNCTION SHALL SET `self.out_data' equal to a list with packets.
        """
        self.extract_sband_vcdus()
        if len(self.out_data) < 1:
            self._logger.warning("No VCDU packets were found")
            return

    def extract_sband_vcdus(self):
        """
        Extracts VCDU frames from file. Assumed that only VCDU frames exist in data,
        no extra fill data. Also assumed all frames in file are equal to VCDU_LENGTH
        specified in the .cfg file
        :param data: raw vcdu data
        :return: list of packets
        """
        frame_size = self.config.config['decoders'][self.yaml_key]['decoder_vcdu']['frame_size']
        assert type(frame_size) == int
        i = 0
        vcdu_packets = []
        while i + frame_size < len(self.in_data):
            vcdu_packets.append(self.in_data[i:i + frame_size])
            i += frame_size
        self.out_data = vcdu_packets

    def extract_vcdu_header(self, frame):
        """
        Extracts header from VCDU frame
        :param frame: VCDU frame
        :return: dict with header
        """
        byte0 = frame[0]
        version_num = cubeds.helpers.extract_bits_from_bytes(bytes([byte0]), 0, 2)
        version_num = cubeds.helpers.bitstring_to_int(version_num)

        bytes0_1 = frame[0:2]
        scid = cubeds.helpers.extract_bits_from_bytes(bytes(bytes0_1), 2, 10)
        scid = cubeds.helpers.bitstring_to_int(scid)

        byte1 = frame[1]
        vcid = cubeds.helpers.extract_bits_from_bytes(bytes([byte1]), 4, 3)
        vcid = cubeds.helpers.bitstring_to_int(vcid)

        byte4 = frame[4]
        sec_hdr = cubeds.helpers.extract_bits_from_bytes(bytes([byte4]), 0, 1)
        sec_hdr = cubeds.helpers.bitstring_to_int(sec_hdr)
        sync_flag = cubeds.helpers.extract_bits_from_bytes(bytes([byte4]), 1, 1)
        sync_flag = cubeds.helpers.bitstring_to_int(sync_flag)
        frame_order_flag = cubeds.helpers.extract_bits_from_bytes(bytes([byte4]), 2, 1)
        frame_order_flag = cubeds.helpers.bitstring_to_int(frame_order_flag)
        segment_length_id = cubeds.helpers.extract_bits_from_bytes(bytes([byte4]), 3, 2)
        segment_length_id = cubeds.helpers.bitstring_to_int(segment_length_id)

        trailer = frame[-2:]

        out_dict = {
            "version": version_num,
            # This Recommended Standard defines the TM Version 1 Synchronous Transfer
            # Frame whose binary encoded Version Number is ‘00’.

            "sc_id": scid,
            # The Spacecraft Identifier shall provide the identification of the spacecraft which
            # is associated with the data contained in the Transfer Frame.

            "vcid": vcid,
            # The Virtual Channel Identifier provides the identification of the Virtual Channel.

            "master_frame_count": frame[2],
            # The purpose of this field is to provide a running count of the Transfer Frames
            # which have been transmitted through the same Master Channel. If the Master
            # Channel Frame Count is re-set because of an unavoidable re-initialization, then
            # the completeness of a sequence of Transfer Frames in the related Master Channel
            # cannot be determined.

            "vc_frame_count": frame[3],
            # The purpose of this field is to provide individual accountability for each Virtual
            # Channel, primarily to enable systematic Packet extraction from the Transfer
            # Frame Data Field. If the Virtual Channel Frame Count is re-set because of an
            # unavoidable re-initialization, the completeness of a sequence of Transfer Frames
            # in the related Virtual Channel cannot be determined.

            "secondary_hdr_flag": sec_hdr,
            "sync_flag": sync_flag,
            # The Synchronization Flag shall signal the type of data which are inserted into
            # the Transfer Frame Data Field. It shall be ‘0’ if octet-synchronized and forward-ordered
            # Packets or Idle Data are inserted; it shall be ‘1’ if a VCA_SDU is inserted.

            "frame_order_flag": frame_order_flag,
            # If the Synchronization Flag is set to ‘0’, the Packet Order Flag is reserved for
            # future use by the CCSDS and is set to ‘0’. If the Synchronization Flag is set to
            # ‘1’, the use of the Packet Order Flag is undefined.

            "segment_length_id": segment_length_id,
            # If the Synchronization Flag is set to ‘0’, the Segment Length Identifier shall be
            # set to ‘11’

            # This Identifier was required for earlier versions of this Recommended Standard to
            # allow for the use of Source Packet Segments, which are no longer defined. Its value
            # has been set to the value used to denote non-use of Source Packet Segments in
            # previous versions.

            # If the Synchronization Flag is set to ‘1’, then the Segment Length Identifier is
            # undefined.

            "frame_pointer": self.extract_packet_header_pointer(frame),
            # If the Synchronization Flag is set to ‘0’, the First Header Pointer shall contain
            # the position of the first octet of the first Packet that starts in the Transfer Frame Data Field.

            # The locations of the octets in the Transfer Frame Data Field shall be numbered
            # in ascending order. The first octet in this Field is assigned the number 0. The First Header
            # Pointer shall contain the binary representation of the location of the first octet of the first
            # Packet that starts in the Transfer Frame Data Field.

            # If no Packet starts in the Transfer Frame Data Field, the First Header Pointer
            # shall be set to ‘11111111111’.

            # If a Transfer Frame contains only Idle Data in its Transfer Frame Data Field, the
            # First Header Pointer shall be set to ‘11111111110’.

            "trailer": trailer
        }
        return out_dict

    def extract_packet_header_pointer(self, packet):
        """
        Extracts packet header pointer from VCDU frame
        :param packet: packet of VCDU data
        :return: packet header int
        """
        header_bytes = bytes(packet[4:6])
        pointer = cubeds.helpers.extract_bits_from_bytes(header_bytes, 5, 11)
        b = cubeds.helpers.bitstring_to_int(pointer)
        return b