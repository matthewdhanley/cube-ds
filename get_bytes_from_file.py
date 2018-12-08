def convert_txt_to_bytes(input_file):
    """
    Takes string hex data from txt file and converts it to a binary file
    :param input_file: text file with hex values. Spaces are fine, but don't have '0x' prefix
    :param data_file_name: binary data file name
    :return: binary data file
    """
    infile = open(input_file, 'r')

    f = open('test/data/'+input_file, 'wb')



def binary_to_bytes(input_file):
    with open(input_file, 'rb') as f:
