import struct
import cubeds.helpers


def extract_CCSDS_header(packet_data):
    header = packet_data[0:12]
    # Sorry this looks terrible. Love, Matt.
    ccsds_version = cubeds.helpers.bitstring_to_int(cubeds.helpers.extract_bits_from_bytes(bytes([header[0]]), 0, 3))
    packet_type = cubeds.helpers.bitstring_to_int(cubeds.helpers.extract_bits_from_bytes(bytes([header[0]]), 3, 1))
    secondary_hdr = cubeds.helpers.bitstring_to_int(cubeds.helpers.extract_bits_from_bytes((bytes([header[0]])), 4, 1))
    zeros = cubeds.helpers.bitstring_to_int(cubeds.helpers.extract_bits_from_bytes(bytes([header[0]]), 5, 3))
    apid_lsb = struct.unpack('>B', header[1])[0]
    grouping_flags = cubeds.helpers.bitstring_to_int(cubeds.helpers.extract_bits_from_bytes(bytes([header[2]]), 0, 2))
    seq_count = cubeds.helpers.bitstring_to_int(cubeds.helpers.extract_bits_from_bytes(bytes(header[2:4]), 2, 15))
    packet_length = struct.unpack('>H', header[4:6])[0]
    if secondary_hdr:
        header_length = 12  # this isn't necessarily true ...
        time_stamp = struct.unpack('>I', header[6:10])[0]
        sub_seconds = struct.unpack('>B', header[10])[0]
        reserved = struct.unpack('>B', header[11])[0]

    else:
        time_stamp = -1
        sub_seconds = -1
        reserved = -1
        header_length = 6

    ccsds_header = {
        'ccsds_version': ccsds_version,
        # Should always be zero

        'packet_type': packet_type,
        'secondary_header': secondary_hdr,
        'zeros': zeros,
        # 'source': struct.unpack('>B', header[0]),
        'apid': apid_lsb,
        'grouping_flags': grouping_flags,
        # a) ‘00’ (0) if the Space Packet contains a continuation segment of User Data;
        # b) ‘01’ (1) if the Space Packet contains the first segment of User Data;
        # c) ‘10’ (2) if the Space Packet contains the last segment of User Data;
        # d) ‘11’ (3) if the Space Packet contains unsegmented User Data.

        'sequence': seq_count,
        'length': packet_length,
        'seconds': time_stamp,
        'subseconds': sub_seconds,
        'reserved': reserved,
        'header_length': header_length}

    return ccsds_header


def check_ccsds_valid(header_dict, sband=False):
    if header_dict['ccsds_version'] != 0:
        return False
    if header_dict['length'] < 50:
        return False
    if header_dict['length'] > 1800:
        return False
    if sband:
        if header_dict['grouping_flags'] != 3:
            return False
    if header_dict['packet_type'] != 0:
        return False
    if header_dict['reserved'] != 0:
        return False
    if header_dict['subseconds'] > 4:
        return False
    if header_dict['subseconds'] < 0:
        return False
    if header_dict['secondary_header'] == 1:
        if header_dict['seconds'] < 500000000:
            return False
        if header_dict['seconds'] > 9000000000:
            return False
    return True