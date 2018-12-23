class CubeDsError(Exception):
    """Basic exception for any errors"""

    def __init__(self, msg=None):
        if msg is None:
            msg = "An error occured in the cube-ds program"
        super(CubeDsError, self).__init__(msg)


class CubeDsRunnerError(CubeDsError):
    """Basic exception for errors raised by the runner"""
    def __init__(self, msg=None):
        if msg is None:
            # Set some default useful error message
            msg = "An error occured in the main runner"
        super(CubeDsRunnerError, self).__init__(msg)


class MissionNotSetError(CubeDsRunnerError):
    """When the mission is not set in the runner"""
    def __init__(self, msg=None):
        if msg is None:
            msg = "error with the mission. Either it's not set or set incorrectly"
        super(MissionNotSetError, self).__init__(msg=msg)


class ConfigError(CubeDsRunnerError):
    """When something is wrong with the config"""
    def __init__(self, msg=None):
        if msg is None:
            msg = "Something is wrong with the config file"
        super(ConfigError, self).__init__(msg=msg)


class ConfigNotSetError(ConfigError):
    """When the config file is not set"""
    def __init__(self, msg=None):
        if msg is None:
            msg = "Config file was not set correctly"
        super(ConfigNotSetError, self).__init__(msg=msg)


class NoConfigFoundError(ConfigError):
    """When the config file is not found"""
    def __init__(self, file, msg=None):
        if msg is None:
            msg = "Config file" + file + " was not found"
        super(NoConfigFoundError, self).__init__(msg=msg)


class ProcessLogError(ConfigError):
    """When there is a problem with the process log"""
    def __init__(self, msg=None):
        if msg is None:
            msg = "Had an error with the process log. Check your config file and that the specified log exists."
        super(ProcessLogError, self).__init__(msg=msg)


class ProcessorError(CubeDsRunnerError):
    """When there is a problem with the data processor"""
    def __init__(self, msg=None):
        if msg is None:
            msg = "Had an issue with the data processor"
        super(ProcessorError, self).__init__(msg=msg)


class DataLoadError(ProcessorError):
    """When there is a problem with loading data"""
    def __init__(self, msg=None):
        if msg is None:
            msg = "Had an error loading in raw data from the file"
        super(DataLoadError, self).__init__(msg=msg)


class DecoderError(CubeDsRunnerError):
    """When there is a problem with the decoder"""
    def __init__(self, msg=None):
        if msg is None:
            msg = "Had an issue with the decoder"
        super(DecoderError, self).__init__(msg=msg)


class DecoderDataError(DecoderError):
    """When there is a problem with the decoder data"""
    def __init__(self, msg=None):
        if msg is None:
            msg = "The data provided to the decoder isn't right."
        super(DecoderDataError, self).__init__(msg=msg)


class UnpackFormatError(CubeDsError):
    """Raise when there is an issue with generating the unpack format"""
    def __init__(self, msg=None):
        if msg is None:
            msg = "There was an error generating the unpack format"
        super(UnpackFormatError, self).__init__(msg=msg)


class TelemetryError(CubeDsError):
    """Raise when there is an issue with generating the unpack format"""
    def __init__(self, msg=None):
        if msg is None:
            msg = "There was an error extracting telemetry data"
        super(TelemetryError, self).__init__(msg=msg)