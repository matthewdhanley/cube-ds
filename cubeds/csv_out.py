import cubeds.exceptions
import cubeds.pylogger
import cubeds.helpers
import cubeds.config
import datetime as dt
import os


class SaveCsv:
    def __init__(self, data, config):
        self.data = data
        self.config = config
        self.save_index = 'time_index'
        self.save_dir = 'summaries'
        self._logger = cubeds.pylogger.get_logger(__name__)
        self.mission = self.config.mission
        self.filename = ''

    def set_filename(self, filename=None):
        if self.data.empty:
            self._logger.warning("No data found to write to CSV")
        if filename is not None:
            self._logger.info("Writing data to CSV file " + self.save_dir + '/' + filename)
            basename, file_extension = os.path.splitext(filename)
            if file_extension != '.csv':
                filename = basename + '.csv'
            output_file = filename
        else:
            output_file = "cube_ds_" + self.mission + "_"
            output_file += str("{}.out".format(dt.datetime.now().strftime('%y%j%H%M%S')))
            self._logger.warning("No filename was specified to save CSV telemetry file.")
            self._logger.info("Defaulting to " + self.save_dir + '/' + output_file)

        self.filename = self.save_dir + '/' + output_file

    def add_utc(self):
        self.data = cubeds.helpers.add_utc_to_df(self.data, self.save_index, cubeds.helpers.tai_to_utc)
        self.data = self.data.set_index('UTC')

    def write_csv(self):
        if not os.path.isdir(self.save_dir):
            self._logger.info("Making new directory for CSV files called "+self.save_dir)
            os.makedirs(self.save_dir)
        self.data.to_csv(self.filename)

    def save(self, filename=None):
        if not len(self.data):
            self._logger.info("No data to save to CSV. Returning.")
            return
        if filename is not None:
            self.set_filename(filename=filename)
        else:
            self.set_filename()

        self.add_utc()
        self.write_csv()



