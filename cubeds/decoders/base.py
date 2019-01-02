import cubeds.exceptions
import cubeds.pylogger
import cubeds.statistics


class Decoder:
    def __init__(self, raw_data, config, stats, basefile):
        # ================= DO NOT CHANGE =====================
        self.in_data = raw_data
        self.out_data = []
        self.config = config
        self.yaml_key = self.config.yaml_key
        self._logger = cubeds.pylogger.get_logger(__name__)
        self.stats = stats

