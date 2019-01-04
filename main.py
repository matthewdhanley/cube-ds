from cubeds.cube_ds_3 import CubeDsRunner
import cubeds
import argparse

# -------------- HELPER FUNCTIONS FOR THIS MAIN MODULE -----------------------------------------------------------------


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
        config_file = 'cfg/csim.yml'  # example config file

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