import cubeds.exceptions
import cubeds.pylogger
import cubeds.helpers
import cubeds.shared
import struct


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
        self.local_config = self.config.config['decoders'][self.yaml_key]['decoder_vcdu_to_ccsds']

    def decode(self):
        """
        This is where the magic happens. The cubeds.processor.Processor class will make a call to decode when it is
        looping through the yaml file. If this method is not present, there will be issues. Think of it like
        the main function. THIS FUNCTION SHALL SET `self.out_data' equal to a list with packets.
        """
        self.extract_ccsds_packets()

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

    def extract_ccsds_packets(self):
        """
        Extracts ccsds packets from VCDU frames
        TODO add partial packet stitching w/ continuous vc00 counters

        USEFUL INFORMATION FROM CCSDS TM SPACE DATA LINK PROTOCOL
        The first and last Packets of the Transfer Frame Data Field are not necessarily
        complete, since the first Packet may be a continuation of a Packet begun in the
        previous Transfer Frame, and the last Packet may continue in the subsequent
        Transfer Frame of the same Virtual Channel.

        :param packets: list of vcdu frames, assumed in order of recipt
        :return: list of ccsds packets
        """
        self._logger.info("Extracting CCSDS packets from " + str(len(self.packets)) + " VCDU frames")
        header_len = self.local_config['header_length']
        ccsds_packets = []
        last_vc_frame_count = self.extract_vcdu_header(self.in_data[0])['vc_frame_count']
        for packet in self.in_data:
            vcdu_header = self.extract_vcdu_header(packet)
            if vcdu_header['vc_frame_count'] - last_vc_frame_count % 255 != 0:
                self._logger.debug("Missing VCDU Frame " + str(vcdu_header['vc_frame_count']))

            else:
                self._logger.debug("Continuous vcdu frames!")

            last_vc_frame_count = vcdu_header['vc_frame_count']
            # todo - move to config
            if vcdu_header['version'] != 0 or \
                    vcdu_header['sc_id'] != 1 or \
                    vcdu_header['secondary_hdr_flag'] != 0 or \
                    vcdu_header['sync_flag'] != 0 or \
                    vcdu_header['frame_order_flag'] != 0 or \
                    vcdu_header['vcid'] != 0:
                self._logger.debug("Bad VCDU frame. Skipping.")
                self._logger.debug(vcdu_header)
                continue

            ccsds_start = header_len + vcdu_header['frame_pointer']
            ccsds_header = cubeds.shared.extract_CCSDS_header(packet[ccsds_start:ccsds_start + 13])
            if not cubeds.shared.check_ccsds_valid(ccsds_header, sband=True):
                continue

            last_ccsds_frame_count = ccsds_header['sequence']

            while ccsds_start + ccsds_header['length'] + 12 < len(packet):
                new_packet = packet[ccsds_start:ccsds_start + ccsds_header['length'] + 12]
                ccsds_packets.append(new_packet)
                ccsds_start += ccsds_header['length'] + 12
                try:
                    ccsds_header = cubeds.shared.extract_CCSDS_header(packet[ccsds_start:ccsds_start + 14])
                except struct.error:
                    self._logger.debug("not enough for another frame. bailing.")
                    self.out_data = ccsds_packets
                    return
                if abs(ccsds_header['sequence'] - last_ccsds_frame_count % 255) > 1:
                    self._logger.debug("Missing CCSDS Packets " + str(last_ccsds_frame_count) + " to " +
                                 str(ccsds_header['sequence']))
                last_ccsds_frame_count = ccsds_header['sequence']

        self.out_data = ccsds_packets
