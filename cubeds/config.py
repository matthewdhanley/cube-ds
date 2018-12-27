import yaml
import os
import cubeds.exceptions
import cubeds.pylogger


class Config:
    def __init__(self, file=None):
        self._get_logger()
        self.config = {}

        if file is None:
            self.file = 'cfg/example.yml'
        else:
            self.file = file

        self.get_config(file=self.file)
        if not self.config:
            raise cubeds.exceptions.ConfigError

        if self.config['runtime']['test']:
            self.test = 1
            self.yaml_key = 'test'
        else:
            self.test = 0
            self.yaml_key = 'prod'

        self.mission = self.config['runtime']['mission']

        self.clean = self.config['cleaning'][self.yaml_key]['enabled']

    def get_config(self, file='cfg/example.yml'):
        config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), file)
        if not os.path.exists(config_file):
            raise cubeds.exceptions.NoConfigFoundError(config_file)

        # Parsing the config file.
        with open(config_file, mode='r') as stream:
            self.config = yaml.load(stream)

    def _get_logger(self):
        self._logger = cubeds.pylogger.get_logger(__name__)