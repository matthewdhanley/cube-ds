import datetime as dt
from . import exceptions
import cubeds.pylogger
import cubeds.config
import cubeds.processor
import argparse
import re
import os


class CubeDsRunner:
    def __init__(
            self,
            mission=None, debug=False, test=False, verbose=False,
            silent=False, doc_list=None, config=None, regex_positive=None,
            regex_negative=None, config_file=None):
        self.debug = debug
        self.verbose = verbose
        self.silent = silent
        self.mission = mission
        self.doc_list = doc_list
        self.config = config
        self.test = test
        self.rundirs = ''
        self.raw_files = []
        self.process_log = []

        self._get_logger()
        if self.verbose:
            self._logger.setLevel(10)
            self._logger.info("Set logging level to VERBOSE")

        if self.debug:
            self._logger.setLevel(9)
            self._logger.info("Set logging level to DEBUG")

        if self.mission is None:
            self._display_help()
            raise cubeds.exceptions.MissionNotSetError

        if self.config is None:
            self._display_help()
            raise cubeds.exceptions.ConfigNotSetError

        if regex_positive is None:
            self._logger.info("RegEx patterns were not specified, going to look at all files")
            self.regex_positive = ['.*']
        else:
            self.regex_positive = regex_positive

        if regex_negative is None:
            self._logger.info("Look-around RegEx patterns were not specified, going to exclude no files")
            self.regex_negative = ''
        else:
            self.regex_negative = regex_negative

    @staticmethod
    def _display_help():
        print("You need help.")

    def _get_logger(self):
        self._logger = cubeds.pylogger.get_logger(__name__)

    def _get_rundirs(self):
        self._logger.verbose("Fetching rundirs location from config")
        if not self.test:
            self.rundirs = self.config.config['rundirs']['prod']['location']
            self._logger.verbose("Using production rundirs locations: " + ' '.join(self.rundirs))
        else:
            self.rundirs = self.config.config['rundirs']['test']['location']
            self._logger.verbose("Using test rundirs locations: " + ' '.join(self.rundirs))

    def _get_process_log(self):
        self._logger.verbose("Fetching process log")
        if not self.test:
            self.process_log_location = self.config.config['process_log']['prod']['location']
            self._logger.verbose("Using production process_log location "+self.process_log_location)
        else:
            self.process_log_location = self.config.config['process_log']['test']['location']
            self._logger.verbose("Using test process_log location "+self.process_log_location)

        if not os.path.exists(self.process_log_location):
            raise cubeds.exceptions.ProcessLogError

        self._logger.verbose("Reading in process log . . .")
        with open(self.process_log_location, mode='r') as f:
            for line in f:
                self.process_log.append(line)

    def find_files(self):
        """
        Finds files in the rundirs directory
        """
        # If rundirs have not been found yet, find them.
        if not self.rundirs:
            self._get_rundirs()
        if not self.process_log:
            self._get_process_log()
        raw_files = []
        # Recursively look from the root of rundirs.
        for rundir in self.rundirs:
            for root, directories, filenames in os.walk(rundir):
                for filename in filenames:  # Check each filename
                    basename = os.path.split(filename)[-1]
                    found_flag = False  # flag to continue if file is found.
                    # Check each file against all the files in the process log. We don't want to waste time processing
                    # all files every time this code is run.
                    if self.config.config['process_log'][self.config.yaml_key]['enabled']:
                        for done in self.process_log:
                            done = os.path.split(done)[-1]
                            if done.rstrip() == basename.rstrip():
                                self._logger.debug("Continuing. File already processed: "+basename)
                                found_flag = True
                        if found_flag:
                            continue

                    if self.regex_negative:  # if it matches a negative regex, move on.
                        for re_string in self.regex_negative:
                            m = re.search(re_string, filename)
                            if m:
                                found_flag = True
                        if found_flag:
                            continue

                    for re_string in self.regex_positive:  # if it matches a positive regex, add it!
                        m = re.search(re_string, filename)
                        if m:
                            raw_files.append(os.path.join(root, filename))

        if not raw_files:
            self._logger.warning("Didn't find any raw files")
        self.raw_files = raw_files

    def log_processed_file(self, file):
        with open(self.process_log_location, 'a') as f:
            f.write(file+'\n')
        f.close()

    def run(self):
        self._logger.verbose("Finding files . . .")
        self.find_files()
        for file in self.raw_files:
            processor = cubeds.processor.Processor(file, config_file=self.config.file)
            processor.process()
            processor.save()

            if self.config.config['process_log'][self.config.yaml_key]['enabled']:
                self.log_processed_file(file)
