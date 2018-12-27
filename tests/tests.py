import unittest
import cubeds.cube_ds_3
import cubeds.exceptions
import cubeds.config


class TestTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_nothing(self):
        """I'm so crazy, I test tests"""
        self.assertEqual(3, 3)

    def test_mission_error(self):
        with self.assertRaises(cubeds.exceptions.MissionNotSetError):
            cubeds.cube_ds_3.CubeDsRunner()
        with self.assertRaises(cubeds.exceptions.MissionNotSetError):
            cubeds.cube_ds_3.CubeDsRunner(mission=None)

    def test_config_not_set_error(self):
        with self.assertRaises(cubeds.exceptions.ConfigNotSetError):
            cubeds.cube_ds_3.CubeDsRunner(mission='testmission')
        with self.assertRaises(cubeds.exceptions.ConfigNotSetError):
            cubeds.cube_ds_3.CubeDsRunner(mission='testmission', config=None)

    def test_config_not_found_error(self):
        with self.assertRaises(cubeds.exceptions.NoConfigFoundError):
            cubeds.config.Config(file='adsf.yml')
        with self.assertRaises(cubeds.exceptions.NoConfigFoundError):
            cubeds.config.Config(file='cfg/adsfeasd.yml')
        self.assertIsNotNone(cubeds.config.Config(file='cfg/example.yml'))

    def test_find_files(self):
        config = cubeds.config.Config(file='cfg/example.yml')
        runner = cubeds.cube_ds_3.CubeDsRunner(mission='doesntmatter', config=config)
        runner.find_files()
        self.assertGreater(len(runner.raw_files), 1)  # make sure some files are found
        runner = cubeds.cube_ds_3.CubeDsRunner(mission='doesntmatter', config=config, regex_positive=['sband'])
        runner.raw_files = []
        runner.find_files()
        self.assertGreater(len(runner.raw_files), 1)  # make sure some files are found
        runner = cubeds.cube_ds_3.CubeDsRunner(mission='doesntmatter', config=config, regex_positive=['sband', '2018'])
        runner.raw_files = []
        runner.find_files()
        len1 = len(runner.raw_files)
        self.assertGreater(len1, 1)  # make sure some files are found
        runner = cubeds.cube_ds_3.CubeDsRunner(mission='doesntmatter', config=config, regex_positive=['sband', '2018'],
                                               regex_negative=['354'])
        runner.raw_files = []
        runner.find_files()
        len2 = len(runner.raw_files)
        self.assertGreater(len2, 1)  # make sure some files are found
        self.assertGreater(len1, len2)  # make sure some files are found

    def test_process_log(self):
        config = cubeds.config.Config(file='cfg/example.yml')
        runner = cubeds.cube_ds_3.CubeDsRunner(mission='doesntmatter', config=config, regex_positive=['sband', '2018'],
                                               regex_negative=['354'])
        runner.find_files()
        self.assertGreater(len(runner.raw_files), 1)  # make sure some files are found

        with self.assertRaises(cubeds.exceptions.ProcessLogError):
            runner.process_log = []
            # make sure it handles incorrect process log locations
            runner.config['process_log']['prod'] = 'somebadlocation/process_file_log.csv'
            runner.find_files()




if __name__ == "__main__":
    unittest.main()
