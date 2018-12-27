import cubeds.exceptions
import cubeds.pylogger
import cubeds.db
import cubeds.csv_out


class TelemetrySaver:
    def __init__(self, data, config, filename=None):
        self._logger = cubeds.pylogger.get_logger(__name__)
        self.data = data
        self.config = config
        if filename is not None:
            self.filename = filename
        else:
            self.filename = None

    def commit_to_db(self):
        db = cubeds.db.Database(self.config)
        db.connect()
        db.add_df_to_db(self.data)
        db.close()

    def save_to_csv(self):
        save_csv = cubeds.csv_out.SaveCsv(self.data, self.config)
        if self.filename is not None:
            save_csv.save(filename=self.filename)
        else:
            save_csv.save()

    def run(self):
        if self.config.config['save']['postgresql'][self.config.yaml_key]['enabled']:
            self._logger.verbose("Adding data to db . . .")
            self.commit_to_db()

        if self.config.config['save']['csv'][self.config.yaml_key]['enabled']:
            self._logger.verbose("Adding data to CSV file . . .")
            self.save_to_csv()


