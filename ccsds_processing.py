from config import *
LOGGER = pylogger.get_logger(__name__)


def extract_CCSDS_header(packet_data):
    header = packet_data[0:12]
    source = header[0]
    apid = header[1]
    groups = header[2]
    sequence = header[3]
    length = struct.unpack('>H', header[4:6])
    seconds = struct.unpack('>I', header[5:9])
    subseconds = header[10]
    ccsds_header = {
        'source': source,
        'apid': apid,
        'groups': groups,
        'sequence': sequence,
        'length': length[0],
        'seconds': seconds,
        'subseconds': subseconds}
    return ccsds_header


def stitch_ccsds(packet_parts):
    # APIDs  TODO - MOVE TO SOMEWHERE MORE CONFIGURABLE!!!!!!!!
    playback_soh = [np.array([12, 63]), np.array([4, 63])]
    # playback_fsw_apid = np.array([4, 62])
    rt_soh= [np.array([8, 63]), np.array([0, 63])]
    # fsw_apid = np.array([8, 62])
    packet_types = [playback_soh, rt_soh]
    start_header_length = 12
    partial_header_length = 6
    full_packets = []
    i = 0
    while i in range(0, len(packet_parts)-1):
        first_flag = 0
        break_flag = 0
        current_packet = packet_parts[i]
        current_ccsds = extract_CCSDS_header(current_packet)
        for apid in packet_types:
            if np.all(apid[0] == [current_ccsds['source'], current_ccsds['apid']]):
                first_flag = 1
                current_apid = apid
        if not first_flag:
            i += 1
            continue

        # TODO FIGURE OUT WHY "-5"
        current_packet = current_packet[0:current_ccsds['length']+start_header_length-5]

        for apid in current_apid[1:]:
            next_packet = packet_parts[i+1]
            next_ccsds = extract_CCSDS_header(next_packet)
            # print(str(next_ccsds['sequence']) + ' - ' + str(current_ccsds['sequence']))
            if int(next_ccsds['sequence']) - int(current_ccsds['sequence']) > 1:
                LOGGER.warning('Partial Packet.')
                i += 1
                break_flag = 1
                break
            if np.all(apid == [next_ccsds['source'], next_ccsds['apid']]):
                current_packet = np.append(current_packet, next_packet[partial_header_length:next_ccsds['length']+partial_header_length])
                current_ccsds = next_ccsds
                i += 1
            else:
                i += 1
                break_flag = 1
                break
        if not break_flag:
            full_packets.append(current_packet)

    return full_packets