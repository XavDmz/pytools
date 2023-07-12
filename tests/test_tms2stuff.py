"""Describes unit tests for the rok4_tools.tms2stuff executable module

There is one test class for each tested functionnality.
See internal docstrings for more information.
Each variable prefixed by "m_" is a mock, or part of it.
"""
from io import StringIO
import json
import re
import os
import sys
from unittest import mock, TestCase, skip
from unittest.mock import call, MagicMock, Mock, mock_open, patch

from rok4_tools import tms2stuff


class TestCLIPArsing(TestCase):
    """Test parsing of CLI calls to the tool's executable."""

    @patch("sys.stderr", new_callable=StringIO)
    @patch("sys.stdout", new_callable=StringIO)
    def test_help(self, m_stdout, m_stderr):
        """Help / usage display options"""
        m_argv = [
            ["rok4_tools/tms2stuff.py", "-h"],
            ["rok4_tools/tms2stuff.py", "--help"],
        ]
        i = 0
        for args in m_argv:
            with patch("sys.argv", args), \
                    self.assertRaises(SystemExit) as cm:
                tms2stuff.parse_cli_args()

            self.assertEqual(cm.exception.code, 0,
                msg=f"exit code should be 0 (option '{args[1]}')")
            self.assertRegex(m_stdout.getvalue(), "\n *optional arguments:",
                msg=f"help message should appear (option '{args[1]}')")
            self.assertEqual(
                m_stderr.getvalue(), "",
                msg=("no error message should appear "
                    + f"(option '{args[1]}')")
            )
            i = i + 1

    @patch("sys.stderr", new_callable=StringIO)
    @patch("sys.stdout", new_callable=StringIO)
    def test_version(self, m_stdout, m_stderr):
        """Version display option"""
        m_argv = ["rok4_tools/tms2stuff.py", "--version"]

        with patch("sys.argv", m_argv), \
                self.assertRaises(SystemExit) as cm:
            tms2stuff.parse_cli_args()

        self.assertEqual(cm.exception.code, 0, msg="exit code should be 0")
        self.assertRegex(m_stdout.getvalue(), "^[0-9]+[.][0-9]+[.][0-9]+")
        self.assertEqual(m_stderr.getvalue(), "",
            msg=f"no error message should appear")

    @patch("sys.stderr", new_callable=StringIO)
    @patch("sys.stdout", new_callable=StringIO)
    def test_nominal_conversion(self, m_stdout, m_stderr):
        """Nominal call to request a conversion"""
        arg_dict = {
            "tms_name": "WGS84G",
            "level": "11",
            "input": "BBOX:2.798552,48.974623,2.860435,50.745681",
            "output": "SLAB_INDICES",
            "slabsize": "16x16",
        }
        m_argv = [
            "rok4_tools/tms2stuff.py",
            arg_dict["tms_name"],
            arg_dict["input"],
            arg_dict["output"],
            "--level", arg_dict["level"],
            "--slabsize", arg_dict["slabsize"],
        ]

        with patch("sys.argv", m_argv):
            result = tms2stuff.parse_cli_args()

        self.assertEqual(result, arg_dict)
        self.assertEqual(m_stdout.getvalue(), "")
        self.assertEqual(m_stderr.getvalue(), "")

    @patch("sys.stderr", new_callable=StringIO)
    @patch("sys.stdout", new_callable=StringIO)
    def test_invalid_conversion(self, m_stdout, m_stderr):
        """Invalid call to request a conversion"""
        m_argv = [
            "rok4_tools/tms2stuff.py",
            "WGS84G",
            "BBOX:2.798552,48.974623,2.860435,50.745681",
            "--level", "11",
            "--unknown", "16x16",
        ]

        with patch("sys.argv", m_argv), \
                self.assertRaises(SystemExit) as cm:
            tms2stuff.parse_cli_args()

        self.assertEqual(cm.exception.code, 2, msg="exit code should be 2")
        self.assertEqual(m_stdout.getvalue(), "")
        self.assertRegex(m_stderr.getvalue(), "usage: (.+\n)+.+py: error:.*")


class TestGeneralProcessing(TestCase):
    """Test general processing functions (not conversion themselves)"""

    @patch("sys.exit")
    @patch("sys.stderr", new_callable=StringIO)
    @patch("sys.stdout", new_callable=StringIO)
    def test_unknown_conversion(self, m_stdout, m_stderr, m_exit):
        """Test simple call to tms2stuff.unknown_conversion()"""
        tms2stuff.unknown_conversion("GEOJSON", "GML")
        self.assertEqual(m_stdout.getvalue(), "")
        self.assertRegex(m_stderr.getvalue(),
            ".*No implemented conversion from.+GEOJSON.+to.+GML.*")
        m_exit.assert_called_once_with(1)

    @patch("sys.exit")
    @patch("sys.stderr", new_callable=StringIO)
    @patch("sys.stdout", new_callable=StringIO)
    def test_cli_syntax_error(self, m_stdout, m_stderr, m_exit):
        """Test simple call to tms2stuff.cli_syntax_error()"""
        tms2stuff.cli_syntax_error("Appropriate message.")
        self.assertEqual(m_stdout.getvalue(), "")
        self.assertEqual(m_stderr.getvalue(), "Appropriate message.\n")
        m_exit.assert_called_once_with(2)

    @patch("rok4_tools.tms2stuff.cli_syntax_error")
    def test_read_bbox_ok(self, m_error):
        """Test valid call to tms2stuff.read_bbox()"""
        bbox = (-12.5, 0, 23, 65.781)
        result = tms2stuff.read_bbox(
            f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}")
        m_error.assert_not_called()
        self.assertEqual(result, bbox)

    @patch("rok4_tools.tms2stuff.cli_syntax_error")
    def test_read_bbox_nok_with_message(self, m_error):
        """Test invalid call to tms2stuff.read_bbox()
        Optional error message included
        """
        message = "This is the expected error message."
        result = tms2stuff.read_bbox("('-12.5', '0', '23', '65.781')",
            message)
        m_error.assert_called_once_with(message)
        self.assertIsNone(result)

    @patch("rok4_tools.tms2stuff.cli_syntax_error")
    def test_read_bbox_nok_default(self, m_error):
        """Test invalid call to tms2stuff.read_bbox()
        Default error message.
        """
        result = tms2stuff.read_bbox("('-12.5', '0', '23', '65.781')")
        m_error.assert_called_once()
        self.assertRegex(m_error.call_args.args[0],
            "Invalid BBOX: .*\nExpected BBOX format is .*")
        self.assertIsNone(result)


class TestConversion(TestCase):
    """Test conversions"""

    def setUp(self):
        self.maxDiff = None
        self.tms_module = "rok4_tools.tms2stuff.TileMatrixSet"
        self.storage_module = "rok4_tools.tms2stuff.Storage"
        self.m_tms_i = MagicMock(name="TileMatrixSet")
        self.m_tms_c = MagicMock(return_value=self.m_tms_i)
        self.m_tm = MagicMock(name="TileMatrix")
        self.m_tms_i.get_level = MagicMock(return_value=self.m_tm)
        self.m_stdout = StringIO()
        self.m_stderr = StringIO()

    def test_bbox_to_tiles_pm_ok(self):
        """Test BBOX to GetTile conversion in the PM TMS.

        Characteristics:
            TMS: PM
            Input: EPSG:3857 bounding box
            Output: WMTS GetTile parameters
        """
        args = {
            "tms_name": "PM",
            "input": "BBOX:753363.55,1688952.65,757025.90,1692621.45",
            "output": "GETTILE_PARAMS",
            "level": "15",
        }
        m_bbox_to_tiles = MagicMock(
            name="bbox_to_tiles",
            return_value=(17000, 15000, 17002, 15002)
        )
        self.m_tm.attach_mock(m_bbox_to_tiles, 'bbox_to_tiles')

        with patch("sys.stdout", self.m_stdout), \
                patch("sys.stderr", self.m_stderr), \
                patch(f"{self.tms_module}.TileMatrixSet", self.m_tms_c), \
                self.assertRaises(SystemExit) as cm:
            tms2stuff.main(args)

        stdout_content = self.m_stdout.getvalue()
        stderr_content = self.m_stderr.getvalue()
        self.assertEqual(cm.exception.code, 0, msg="exit code should be 0")
        self.assertEqual(stderr_content, "",
            msg=f"no error message should appear")
        self.m_tms_c.assert_called_once_with(args["tms_name"])
        self.m_tms_i.get_level.assert_called_once_with(args["level"])
        m_bbox_to_tiles.assert_called_once_with(
            (753363.55, 1688952.65, 757025.90, 1692621.45)
        )
        expected_match_list = [
            (17000, 15000),
            (17001, 15000),
            (17002, 15000),
            (17000, 15001),
            (17001, 15001),
            (17002, 15001),
            (17000, 15002),
            (17001, 15002),
            (17002, 15002),
        ]
        expected_output = ""
        for item in expected_match_list:
            expected_output = (f"{expected_output}TILEMATRIX={args['level']}"
                + f"&TILECOL={item[0]}&TILEROW={item[1]}\n")
        self.assertEqual(stdout_content, expected_output, 
            "unexpected console output")

    def test_bbox_to_slab_indices_pm_ok(self):
        """Test conversion from a BBOX to slab indices in the PM TMS.

        Characteristics:
            TMS: PM
            Input: EPSG:3857 bounding box
            Output: slab indices
        """
        level_id = "15"
        m_bbox = (-19060337.37, 19644927.76, -19057891.39, 19647373.75)
        m_bbox_to_tiles = MagicMock(
            name="bbox_to_tiles",
            return_value=(799, 319, 800, 321)
        )
        self.m_tm.attach_mock(m_bbox_to_tiles, 'bbox_to_tiles')
        args = {
            "tms_name": "PM",
            "input": f"BBOX:{m_bbox[0]},{m_bbox[1]},{m_bbox[2]},{m_bbox[3]}",
            "output": "SLAB_INDICES",
            "level": "15",
            "slabsize": "16x10",
        }

        with patch("sys.stdout", self.m_stdout), \
                patch("sys.stderr", self.m_stderr), \
                patch(f"{self.tms_module}.TileMatrixSet", self.m_tms_c), \
                self.assertRaises(SystemExit) as cm:
            tms2stuff.main(args)

        stdout_content = self.m_stdout.getvalue()
        stderr_content = self.m_stderr.getvalue()
        self.assertEqual(cm.exception.code, 0, msg="exit code should be 0")
        self.assertEqual(stderr_content, "",
            msg=f"no error message should appear")
        self.m_tms_c.assert_called_once_with(args["tms_name"])
        self.m_tms_i.get_level.assert_called_once_with(args["level"])
        expected_output = ""
        slabs_list = [
            (49, 31),
            (49, 32),
            (50, 31),
            (50, 32),
        ]
        for pair in slabs_list:
            pair_string = f"{pair[0]},{pair[1]}"
            expected_output = expected_output + pair_string + "\n"
        self.assertEqual(stdout_content, expected_output, 
            "unexpected console output")

    def test_bbox_list_to_slab_indices_pm_ok(self):
        """Test conversion from a list of BBOX to slab indices 
            in the PM TMS.

        Characteristics:
            TMS: PM
            Input: path to a existing file or object describing
                a list of EPSG:3857 bounding boxes
            Output: slab indices
        """
        list_path = "s3://temporary/bbox_list.txt"
        bbox_list = [
            (-19060337.37, 19646150.75, -19059114.38, 19647373.75),
            (-19060337.37, 19644927.76, -19059114.38, 19646150.75),
            (-19060337.37, 19643704.77, -19059114.38, 19644927.76),
            (-19059114.38, 19643704.77, -19057891.38, 19647373.75),
            (-19835714.58, 19736652.19, -19834491.59, 19737875.19),
            (-19827153.64, 19731760.22, -19825930.64, 19732983.22),
        ]
        list_content = ""
        bbox_calls_list = []
        for bbox in bbox_list:
            bbox_string = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
            list_content = list_content + bbox_string + "\n"
            bbox_calls_list.append(call(bbox))
        m_get_data = MagicMock(name="get_data_str", return_value=list_content)
        m_exists = MagicMock(name="exists", return_value=True)
        tiles_list = [
            (799, 319, 800, 320),
            (799, 320, 800, 321),
            (799, 321, 800, 322),
            (800, 319, 801, 322),
            (165, 245, 166, 246),
            (172, 249, 173, 250)
        ]
        m_bbox_to_tiles = MagicMock(name="bbox_to_tiles",
            side_effect=tiles_list)
        self.m_tm.attach_mock(m_bbox_to_tiles, 'bbox_to_tiles')
        args = {
            "tms_name": "PM",
            "input": f"BBOXES_LIST:{list_path}",
            "output": "SLAB_INDICES",
            "level": "15",
            "slabsize": "16x10",
        }

        with patch("sys.stdout", self.m_stdout), \
                patch("sys.stderr", self.m_stderr), \
                patch(f"{self.tms_module}.TileMatrixSet", self.m_tms_c), \
                self.assertRaises(SystemExit) as cm, \
                patch(f"{self.storage_module}.exists", m_exists), \
                patch(f"{self.storage_module}.get_data_str", m_get_data):
            tms2stuff.main(args)

        stdout_content = self.m_stdout.getvalue()
        stderr_content = self.m_stderr.getvalue()
        self.assertEqual(cm.exception.code, 0, msg="exit code should be 0")
        self.assertEqual(stderr_content, "",
            msg=f"no error message should appear")
        self.m_tms_c.assert_called_once_with(args["tms_name"])
        self.m_tms_i.get_level.assert_called_once_with(args["level"])
        m_exists.assert_called_once_with(list_path)
        m_get_data.assert_called_once_with(list_path)
        self.assertEqual(m_bbox_to_tiles.call_args_list, bbox_calls_list,
            msg="Wrong calls to TileMatrix.bbox_to_tiles(bbox)")
        slabs_list = [
            (10,24),
            (10,25),
            (49,31),
            (49,32),
            (50,31),
            (50,32),
        ]
        expected_output = ""
        for pair in slabs_list:
            pair_string = f"{pair[0]},{pair[1]}"
            expected_output = expected_output + pair_string + "\n"
        self.assertEqual(stdout_content, expected_output, 
            "unexpected console output")



    def test_tile_to_getmap_pm_ok(self):
        """Test tile indices to GetMap conversion in the PM TMS.

        Characteristics:
            TMS: PM
            Input: tile indices
            Output: WMS GetMap parameters
        """
        args = {
            "tms_name": "PM",
            "input": "TILE_INDICE:17000,15000",
            "output": "GETMAP_PARAMS",
            "level": "15",
        }
        m_bbox = (753363.3507787623, 10936117.94367338,
                754586.3432313241, 10936724.662585393)
        m_projection = "EPSG:3857"
        m_tile_to_bbox = MagicMock(
            name="tile_to_bbox",
            return_value=m_bbox
        )
        self.m_tm.attach_mock(m_tile_to_bbox, 'tile_to_bbox')
        m_tile_size = (256, 127)
        self.m_tms_i.srs = m_projection
        self.m_tm.tile_size = m_tile_size

        with patch("sys.stdout", self.m_stdout), \
                patch("sys.stderr", self.m_stderr), \
                patch(f"{self.tms_module}.TileMatrixSet", self.m_tms_c), \
                self.assertRaises(SystemExit) as cm:
            tms2stuff.main(args)

        stdout_content = self.m_stdout.getvalue()
        stderr_content = self.m_stderr.getvalue()
        self.assertEqual(cm.exception.code, 0, msg="exit code should be 0")
        self.assertEqual(stderr_content, "",
            msg=f"no error message should appear")
        self.m_tms_c.assert_called_once_with(args["tms_name"])
        self.m_tms_i.get_level.assert_called_once_with(args["level"])
        m_tile_to_bbox.assert_called_once_with(tile_col=17000, tile_row=15000)
        expected_output = (
            f"WIDTH={m_tile_size[0]}"
            + f"&HEIGHT={m_tile_size[1]}"
            + f"&BBOX={m_bbox[0]},{m_bbox[1]},{m_bbox[2]},{m_bbox[3]}"
            + f"&CRS={m_projection}\n"
        )
        self.assertEqual(stdout_content, expected_output, 
            "unexpected console output")

