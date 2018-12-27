import cubeds.slack
import cubeds.pylogger


class Statistics:

    # CLASS VARIABLES - Kind of like global log
    num_files_processed = 0
    num_potential_packets = 0
    num_packets_cleaned = 0

    def __init__(self, basefile, config):
        self.basefile = basefile
        self.stats = []
        self.config = config
        self._logger = cubeds.pylogger.get_logger(__name__)

    def __del__(self):
        self._logger.verbose("Writing statistics to file.")
        self.write()

    def add_stat(self, stat):
        self.stats.append(stat)

    def print_stats(self):
        print("==============================================================")
        print("Statistics for "+self.basefile+" processing:")
        for stat in self.stats:
            print(stat)
        print("==============================================================")

    def write_to_file(self):
        with open('text_summaries/'+self.basefile+'.txt', mode='w+') as f:
            f.write("==============================================================")
            f.write("Info from " + self.basefile + " processing:\n")
            for stat in self.stats:
                f.write(stat)
            f.write("==============================================================")
        self._logger.info("Wrote statistics to text_summaries/"+self.basefile+".txt")

    def post_to_slack(self):
        message = "Info from " + self.basefile + " processing:\n"
        for stat in self.stats:
            message += ("\n"+stat)
        cubeds.slack.write_to_slack(message, self.config)
        self._logger.info("Wrote statistics to slack workspace")

    def reset(self):
        self.stats = []

    def write(self):
        if self.config.config['ingest_stats'][self.config.yaml_key]['text_file']:
            self.write_to_file()
        if self.config.config['ingest_stats'][self.config.yaml_key]['std_out']:
            self.print_stats()
        if self.config.config['ingest_stats'][self.config.yaml_key]['slack']:
            self.post_to_slack()
