from config import *
from slack import *
import pylogger

LOGGER = pylogger.get_logger(__name__)


class Statistics:
    def __init__(self, basefile):
        self.basefile = basefile
        self.stats = []

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
        LOGGER.info("Wrote statistics to text_summaries/"+self.basefile+".txt")

    def post_to_slack(self):
        message = "Info from " + self.basefile + " processing:\n"
        for stat in self.stats:
            message += ("\n"+stat)
        write_to_slack(message)
        LOGGER.info("Wrote statistics to slack workspace")

    def reset(self):
        self.stats = []

    def write(self):
        if int(CONFIG_INFO['INGEST_STATS']['TEXT_FILE']):
            self.write_to_file()
        if int(CONFIG_INFO['INGEST_STATS']['STD_OUT']):
            self.print_stats()
        if int(CONFIG_INFO['INGEST_STATS']['SLACK']):
            self.post_to_slack()
