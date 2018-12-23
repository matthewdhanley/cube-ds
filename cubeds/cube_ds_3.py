import datetime as dt
import cubeds.exceptions
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

        self.outputFile = "cube_ds_" + mission + "_"
        self.outputFile += str("{}.out".format(dt.datetime.now().strftime('%y%j%H%M%S')))
        self._logger.verbose("Output file: "+self.outputFile)

    @staticmethod
    def _display_help():
        print("You need help.")

    def _get_logger(self):
        self._logger = cubeds.pylogger.get_logger(__name__)

    def _get_rundirs(self):
        self._logger.verbose("Fetching rundirs location from config")
        if not self.test:
            self.rundirs = self.config.config['rundirs']['prod']['location']
            self._logger.verbose("Using production rundirs location "+self.rundirs)
        else:
            self.rundirs = self.config.config['rundirs']['test']['location']
            self._logger.verbose("Using test rundirs location "+self.rundirs)

    def _get_process_log(self):
        self._logger.verbose("Fetching process log")
        if not self.test:
            self.process_log_location = self.config.config['process_log']['prod']['location']
            self._logger.verbose("Using production process_log location "+self.rundirs)
        else:
            self.process_log_location = self.config.config['process_log']['test']['location']
            self._logger.verbose("Using test process_log location "+self.rundirs)

        if not os.path.exists(self.process_log_location):
            raise cubeds.exceptions.ProcessLogError

        self._logger.verbose("Reading in process log . . .")
        with open(self.process_log_location, mode='r') as f:
            for line in f:
                self.process_log.append(line.rstrip())

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
        for root, directories, filenames in os.walk(self.rundirs):
            for filename in filenames:  # Check each filename

                found_flag = False  # flag to continue if file is found.
                # Check each file against all the files in the process log. We don't want to waste time processing
                # all files every time this code is run.
                for done in self.process_log:
                    if done == filename:
                        self._logger.debug("Continuing. File already processed: "+filename)
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
            self._logger.warning("Didn't find any raw files in " + self.rundirs)
        self.raw_files = raw_files

    def run(self):
        self._logger.verbose("Finding files . . .")
        self.find_files()
        for file in self.raw_files:
            processor = cubeds.processor.Processor(file, config_file=self.config.file)


def parse_command_line_args():
    # Parsing command line arguments
    parser = argparse.ArgumentParser(description='Command Line Parser')

    parser.add_argument('-t', '--test', action="store_true", help="If present, program will be run in test mode")
    parser.add_argument('-d', '--debug', action="store_true", help="If present, program will be run in debug mode")
    parser.add_argument('-v', '--verbose', action="store_true", help="If present, program will be run in verbose mode")
    parser.add_argument('-m', '--mission', type=str, help="Specify specific mission using this parameter")
    parser.add_argument('-c', '--config', type=str,
                        help="Specifies what config file to use. If absent, cfg/example.cfg will be used")

    args = parser.parse_args()  # test bool will be stored in args.test
    return args


def main():
    args = parse_command_line_args()

    # Check if user set the config file command line arguement. If so, extract it. This argument should
    # really always be used, unless "example.cfg" is changed to be something else.
    if args.config:
        config_file = args.config  # user specified config file
    else:
        config_file = 'cfg/example.yml'  # example config file

    # Load the config info from the file specified. Will get exception if file does not exist.
    config = cubeds.config.Config(file=config_file)

    # SETUP runtime parameters.
    if int(config.config['runtime']['verbose']):
        verbose = True
    elif args.verbose:
        verbose = True
    else:
        verbose = False

    if int(config.config['runtime']['test']):
        test = True
    elif args.test:
        test = True
    else:
        test = False

    if int(config.config['runtime']['debug']):
        debug = True
    elif args.debug:
        debug = True
    else:
        debug = False

    if config.config['runtime']['mission']:
        mission = config.config['runtime']['mission']
    elif args.mission:
        mission = args.mission
    else:
        mission = None  # gonna get an error!

    runner = CubeDsRunner(mission=mission,
                          verbose=verbose,
                          debug=debug,
                          test=test,
                          config=config,
                          regex_positive=['^raw.*', '.*\.kss', '.*sband.*'],
                          regex_negative=['.*flatsat.*'])

    runner.run()

if __name__ == "__main__":
    main()
