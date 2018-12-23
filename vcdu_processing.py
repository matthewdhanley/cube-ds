import numpy as np
from config import *
from helpers import *
from ccsds_processing import *
import pylogger

LOGGER = pylogger.get_logger(__name__)


def extract_sband_vcdus(data):
    """
    Extracts VCDU frames from file. Assumed that only VCDU frames exist in data,
    no extra fill data. Also assumed all frames in file are equal to VCDU_LENGTH
    specified in the .cfg file
    :param data: raw vcdu data
    :return: list of packets
    """
    header_length = int(CONFIG_INFO['SBAND']['VCDU_LENGTH'])
    i = 0
    sband_packets = []
    while i + header_length < len(data):
        sband_packets.append(data[i:i+header_length])
        i += 2048
    return sband_packets


def extract_packet_header_pointer(packet):
    """
    Extracts packet header pointer from VCDU frame
    :param packet: packet of VCDU data
    :return: packet header int
    """
    header_bytes = bytes(packet[4:6])
    pointer = extract_bits_from_bytes(header_bytes, 5, 11)
    b = bitstring_to_int(pointer)
    return b


def extract_vcdu_header(packet):
    """
    Extracts header from VCDU frame
    :param packet: VCDU frame
    :return: dict with header
    """
    byte0 = packet[0]
    version_num = extract_bits_from_bytes(bytes([byte0]), 0, 2)
    version_num = bitstring_to_int(version_num)

    bytes0_1 = packet[0:2]
    scid = extract_bits_from_bytes(bytes(bytes0_1), 2, 10)
    scid = bitstring_to_int(scid)

    byte1 = packet[1]
    vcid = extract_bits_from_bytes(bytes([byte1]), 4, 3)
    vcid = bitstring_to_int(vcid)

    byte4 = packet[4]
    sec_hdr = extract_bits_from_bytes(bytes([byte4]), 0, 1)
    sec_hdr = bitstring_to_int(sec_hdr)
    sync_flag = extract_bits_from_bytes(bytes([byte4]), 1, 1)
    sync_flag = bitstring_to_int(sync_flag)
    packet_order_flag = extract_bits_from_bytes(bytes([byte4]), 2, 1)
    packet_order_flag = bitstring_to_int(packet_order_flag)
    segment_length_id = extract_bits_from_bytes(bytes([byte4]), 3, 2)
    segment_length_id = bitstring_to_int(segment_length_id)

    trailer = packet[-2:]

    out_dict = {
        "version": version_num,
        # This Recommended Standard defines the TM Version 1 Synchronous Transfer
        # Frame whose binary encoded Version Number is ‘00’.

        "sc_id": scid,
        # The Spacecraft Identifier shall provide the identification of the spacecraft which
        # is associated with the data contained in the Transfer Frame.

        "vcid": vcid,
        # The Virtual Channel Identifier provides the identification of the Virtual Channel.

        "master_frame_count": packet[2],
        # The purpose of this field is to provide a running count of the Transfer Frames
        # which have been transmitted through the same Master Channel. If the Master
        # Channel Frame Count is re-set because of an unavoidable re-initialization, then
        # the completeness of a sequence of Transfer Frames in the related Master Channel
        # cannot be determined.

        "vc_frame_count": packet[3],
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

        "packet_order_flag": packet_order_flag,
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

        "packet_pointer": extract_packet_header_pointer(packet),
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


def vcdu_stats(packets, basefile):
    columns = ["version", "sc_id", "vcid", "master_frame_count", "vc_frame_count", "secondary_hdr_flag",
               "sync_flag", "packet_order_flag", "segment_length_id", "packet_pointer", "trailer"]
    header_df = pd.DataFrame(columns=columns)
    for packet in packets:
        header = extract_vcdu_header(packet)
        tmpdf = pd.DataFrame([header], columns=columns)
        header_df = header_df.append(tmpdf)

    header_df.to_csv('vcdu_summaries/'+basefile+'_vcdu_summery.csv', index=False)
    LOGGER.info("Wrote vcdu headers to file.")

    return header_df


def extract_ccsds_packets(packets):
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
    LOGGER.info("Extracting CCSDS packets from "+str(len(packets))+" VCDU frames")
    header_len = 6
    ccsds_packets = []
    last_vc_frame_count = extract_vcdu_header(packets[0])['vc_frame_count']
    for packet in packets:
        vcdu_header = extract_vcdu_header(packet)
        if vcdu_header['vc_frame_count'] - last_vc_frame_count % 255 != 0:
            LOGGER.debug("Missing VCDU Frame " + str(vcdu_header['vc_frame_count']))

        else:
            LOGGER.debug("Continuous vcdu frames!")

        last_vc_frame_count = vcdu_header['vc_frame_count']
        # todo - move to config
        if vcdu_header['version'] != 0 or \
                vcdu_header['sc_id'] != 1 or \
                vcdu_header['secondary_hdr_flag'] != 0 or \
                vcdu_header['sync_flag'] != 0 or \
                vcdu_header['packet_order_flag'] != 0 or \
                vcdu_header['vcid'] != 0:
            LOGGER.debug("Bad VCDU frame. Skipping.")
            LOGGER.debug(vcdu_header)
            continue

        ccsds_start = header_len + vcdu_header['packet_pointer']
        ccsds_header = extract_CCSDS_header(packet[ccsds_start:ccsds_start + 13])
        if not check_ccsds_valid(ccsds_header, sband=True):
            continue

        last_ccsds_frame_count = ccsds_header['sequence']

        while ccsds_start + ccsds_header['length'] + 12 < len(packet):
            new_packet = packet[ccsds_start:ccsds_start + ccsds_header['length']+12]
            ccsds_packets.append(new_packet)
            ccsds_start += ccsds_header['length'] + 12
            try:
                ccsds_header = extract_CCSDS_header(packet[ccsds_start:ccsds_start + 14])
            except struct.error:
                LOGGER.debug("not enough for another frame. bailing.")
                return ccsds_packets
            if abs(ccsds_header['sequence'] - last_ccsds_frame_count % 255) > 1:
                LOGGER.debug("Missing CCSDS Packets "+str(last_ccsds_frame_count)+" to " +
                            str(ccsds_header['sequence']))
            last_ccsds_frame_count = ccsds_header['sequence']

    return ccsds_packets


def process_vcdu(data, stats=Statistics('none')):
    # SBAND CASE
    stats.add_stat("Interpreted as SBand File")
    LOGGER.info("Extracting SBAND data from " + stats.basefile)

    packets = extract_sband_vcdus(data)
    stats.add_stat("Potentially " + str(len(packets)) + " VCDU Frames")

    if DEBUG:
        write_to_pickle(packets, 'debug/vcdu_raw_packets_' + stats.basefile + '.pickle')

    if CONFIG_INFO['SAVE']['VCDU_STATS']:
        vcdu_stats(packets, stats.basefile)

    packets = extract_ccsds_packets(packets)
    stats.add_stat("Found " + str(len(packets)) + " Potential CCSDS Packets")

    if CONFIG_INFO['SAVE']['CCSDS_STATS']:
        ccsds_stats(packets, stats.basefile)

    if DEBUG:
        write_to_pickle(packets, "debug/vcdu_ccsds_packets_" + stats.basefile + ".pickle")

    return packets

