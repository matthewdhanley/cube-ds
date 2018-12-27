import yaml
import cubeds.exceptions
import cubeds.config
import cubeds.pylogger
import cubeds.statistics
import cubeds.telemetry_saver
from cubeds.decoders import *
import re
import os
import numpy as np


class Processor:
    """
    This class will take in a file, then determine which decoders it needs to pass the file to.
    """
    def __init__(self, file, config_file=None, endian='big'):
        self._get_logger()
        self._logger.info("Processing "+file+" . . .")
        self.file = file
        self.file_basename = os.path.split(file)[-1]
        if config_file is None:
            raise cubeds.exceptions.ConfigNotSetError

        self.endian = endian

        self.config_file = config_file
        self.config = cubeds.config.Config(self.config_file)
        self.test = self.config.test

        if self.test:
            self.yaml_key = 'test'
        else:
            self.yaml_key = 'prod'

        self.decoders = self.config.config['decoders'][self.yaml_key]
        self.max_priority = self.config.config['decoders']['max_priority']
        self.data = None
        self._load_data()
        self.stats = cubeds.statistics.Statistics(self.file_basename, self.config)

    def process(self):
        for i in range(1, self.max_priority):
            for decoder in self.decoders:
                done_flag = False
                if self.decoders[decoder]['priority'] == i:
                    for r in self.decoders[decoder]['regex']:
                        if re.search(r, self.file_basename):
                            self._logger.verbose("Applying "+decoder+" decoder module . . .")
                            exec_cmd = decoder+'.Decoder(self.data, self.config, '+self.file_basename+')'
                            self._logger.debug(exec_cmd)
                            d = eval(exec_cmd)
                            d.decode()
                            self.data = d.out_data
                            self.stats = d.stats
                            done_flag = True
                        if done_flag:
                            break
        if type(self.data) == list:
            self._logger.warning("Output was a list, could be an issue. It's likely that there was no data found in the"
                                 "file. Continuing . . .")
            return

    def save(self):
        telemetry_saver = cubeds.telemetry_saver.TelemetrySaver(self.data, self.config, filename=self.file_basename)
        telemetry_saver.run()

    def _get_logger(self):
        self._logger = cubeds.pylogger.get_logger(__name__)

    def _load_data(self):
        """
        reads in raw data
        """
        self._logger.debug("Telemetry file -  " + self.file)
        self._logger.verbose("Reading in data to be processed . . .")
        # check that the file exists
        if not os.path.exists(self.file):
            self._logger.debug(self.file)
            self._logger.fatal("Cannot find specified file " + self.file)
            raise cubeds.exceptions.DataLoadError

        # read the data into a numpy array
        self._logger.debug("reading data into numpy byte array")
        if self.endian == "big":
            raw_data = np.fromfile(self.file, dtype='>B')
        elif self.endian == "little":
            raw_data = np.fromfile(self.file, dtype='<B')
        else:
            self._logger.fatal("DID NOT specify correct endian")
            raise cubeds.exceptions.DataLoadError

        self.data = raw_data
        self._logger.verbose("Raw file length - "+str(len(raw_data)))




