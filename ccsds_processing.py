from config import *
from helpers import *
LOGGER = pylogger.get_logger(__name__)


def extract_CCSDS_header(packet_data):
    header = packet_data[0:12]
    zeros = bitstring_to_int(extract_bits_from_bytes(bytes([header[0]]), 5, 3))
    secondary_hdr = bitstring_to_int(extract_bits_from_bytes((bytes([header[0]])), 4, 1))
    packet_type = bitstring_to_int(extract_bits_from_bytes(bytes([header[0]]), 3, 1))
    ccsds_version = bitstring_to_int(extract_bits_from_bytes(bytes([header[0]]), 0, 3))
    apid_lsb = struct.unpack('>B', header[1])[0]
    grouping_flags = bitstring_to_int(extract_bits_from_bytes(bytes([header[2]]), 0, 2))
    seq_count = bitstring_to_int(extract_bits_from_bytes(bytes(header[2:4]), 2, 13))
    packet_length = struct.unpack('>H', header[4:6])[0]
    if secondary_hdr:
        header_length = 12
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


def stitch_ccsds_new(packet_parts):
    full_packets = []
    i = 0
    full_df = pd.DataFrame()
    while i in range(0, len(packet_parts)):
        ccsds_header = extract_CCSDS_header(packet_parts[i])
        ccsds_header['index'] = i
        tmp_df = pd.DataFrame([ccsds_header], columns=ccsds_header.keys())
        full_df = full_df.append(tmp_df)
        i += 1

    try:
        unique_seqs = full_df.sequence.unique()
    except AttributeError as e:
        LOGGER.info(e)
        return full_packets

    for seq in unique_seqs:
        parts_df = full_df[full_df['sequence'] == seq]
        packet_beginning_ind = parts_df[parts_df['grouping_flags'] == 1]
        if packet_beginning_ind.empty:
            LOGGER.debug("No start of packet found")
            continue

        packet_middle_inds = parts_df[parts_df['grouping_flags'] == 0]

        packet_end_ind = parts_df[parts_df['grouping_flags'] == 2]

        start_ind = packet_beginning_ind['index'].values
        if len(start_ind) > 1:
            LOGGER.debug("Multiple frame starts at sequence number "+str(seq))
            LOGGER.debug("using the first one.")

        start_ind = start_ind[0]

        length = packet_beginning_ind['length'].values[0] + packet_beginning_ind['header_length'].values[0]-5
        packet = packet_parts[start_ind][0:length]

        if not packet_middle_inds.empty:
            print("APPEND MIDDLE PACKETS")
            exit(1)

        if packet_end_ind.empty:
            LOGGER.debug("No end of packet found for sequence number "+str(seq))
            full_packets.append(packet)
            continue

        end_ind = packet_end_ind['index'].values
        if len(end_ind) > 1:
            LOGGER.debug("Multiple frame ends for sequnce number "+str(seq))
            LOGGER.debug("using the first one.")

        end_ind = end_ind[0]
        length = packet_end_ind['length'].values[0] + packet_end_ind['header_length'].values[0]+1
        packet = np.append(packet, packet_parts[end_ind][packet_end_ind['header_length'].values[0]:length])

        full_packets.append(packet)

    return full_packets


def ccsds_stats(packets, basename):
    """
    Prints ccsds info to csv
    :param packets: list of ccsds raw packets
    :param basename: will append _ccsds_summary.csv to this
    """
    df = pd.DataFrame()
    for packet in packets:
        header = extract_CCSDS_header(packet)
        tmp_df = pd.DataFrame([header], columns=header.keys())
        df = df.append(tmp_df)

    df.to_csv('ccsds_summaries/' + basename+'_ccsds_summary.csv', index='seconds')
    LOGGER.info("Wrote ccsds headers to file.")


def find_ccsds_packets(data):
    # Fetch relevant apids from file
    apids = np.array(get_apids())

    inds = []
    for x in range(1, len(data)):
        for apid in apids:
            if data[x] == apid:
                inds.append(x-1)

    packets = []
    for ind in inds:
        header_dict = extract_CCSDS_header(data[ind:ind+12])
        if check_ccsds_valid(header_dict, sband=True):
            packets.append(data[ind:ind+header_dict['length']+header_dict['header_length']])

    return packets


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






