import unittest
from netcdf import *
from cube_ds_2 import *


class TestTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_nothing(self):
        self.assertEqual(3,3)

    def test_get_netcdf_dtype(self):
        self.assertEqual('i1', get_netcdf_dtype(1, 'state'))
        self.assertEqual('i1', get_netcdf_dtype(7, 'state'))
        self.assertEqual('i1', get_netcdf_dtype(8, 'state'))
        self.assertEqual('i2', get_netcdf_dtype(9, 'state'))
        self.assertEqual('i2', get_netcdf_dtype(16, 'state'))
        self.assertEqual('f4', get_netcdf_dtype(1, ''))
        self.assertEqual('f4', get_netcdf_dtype(7, ''))
        self.assertEqual('f4', get_netcdf_dtype(8, ''))
        self.assertEqual('f4', get_netcdf_dtype(15, ''))
        self.assertEqual('f4', get_netcdf_dtype(16, ''))
        self.assertEqual('f4', get_netcdf_dtype(24, ''))
        self.assertEqual('f4', get_netcdf_dtype(32, ''))
        self.assertEqual('f8', get_netcdf_dtype(33, ''))
        self.assertEqual('f8', get_netcdf_dtype(40, ''))
        self.assertEqual('f8', get_netcdf_dtype(64, ''))
        self.assertEqual('f8', get_netcdf_dtype(65465, ''))

    def test_get_unpack_format(self):
        self.assertEqual('>B', get_unpack_format('dn', 1))
        self.assertEqual('>b', get_unpack_format('sn', 1))
        self.assertEqual('>H', get_unpack_format('dn', 16))
        self.assertEqual('>h', get_unpack_format('sn', 16))
        self.assertEqual('>I', get_unpack_format('dn', 32))
        self.assertEqual('>i', get_unpack_format('sn', 32))
        self.assertEqual('>Q', get_unpack_format('dn', 64))
        self.assertEqual('>q', get_unpack_format('sn', 64))
        self.assertEqual('>1s', get_unpack_format('char', 8))
        self.assertEqual('>2s', get_unpack_format('char', 16))
        self.assertEqual('>4s', get_unpack_format('char', 32))
        self.assertEqual('>d', get_unpack_format('float', 32))
        self.assertEqual('>d', get_unpack_format('double', 32))
        self.assertEqual('<H', get_unpack_format('dn', 16, endian='little'))


if __name__ == "__main__":
    unittest.main()