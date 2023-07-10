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


class TestGenericOptions(TestCase):
    """Test generic CLI calls to the tool's executable."""
    def setUp(self):
        self.m_stdout = StringIO()
        self.m_stderr = StringIO()


    def test_help(self):
        """Help / usage display options"""
        m_argv = [
            ["rok4_tools/tms2stuff.py", "-h"],
            ["rok4_tools/tms2stuff.py", "--help"],
        ]
        i = 0
        for args in m_argv:
            m_stdout = StringIO()
            m_stderr = StringIO()
            with patch("sys.argv", args), \
                    self.assertRaises(SystemExit) as cm, \
                    patch("sys.stdout", self.m_stdout), \
                    patch("sys.stderr", self.m_stderr):
                tms2stuff.main()

            self.assertEqual(cm.exception.code, 0,
                msg=f"exit code should be 0 (option '{args[1]}')")
            stdout_content = self.m_stdout.getvalue()
            self.assertRegex(stdout_content, "\n *optional arguments:",
                msg=f"help message should appear (option '{args[1]}')")
            stderr_content = self.m_stderr.getvalue()
            self.assertEqual(
                stderr_content, "",
                msg=("no error message should appear "
                    + f"(option '{args[1]}')")
            )
            i = i + 1

    def test_version(self):
        """Version display option"""
        m_argv = ["rok4_tools/tms2stuff.py", "--version"]
        m_stdout = StringIO()
        m_stderr = StringIO()

        with patch("sys.argv", m_argv), \
                self.assertRaises(SystemExit) as cm, \
                patch("sys.stdout", self.m_stdout), \
                patch("sys.stderr", self.m_stderr):
            tms2stuff.main()

        self.assertEqual(cm.exception.code, 0, msg="exit code should be 0")
        stdout_content = self.m_stdout.getvalue()
        self.assertRegex(stdout_content, "^[0-9]+[.][0-9]+[.][0-9]+")
        stderr_content = self.m_stderr.getvalue()
        self.assertEqual(stderr_content, "",
            msg=f"no error message should appear")


class TestConversion(TestCase):
    """Test conversions"""

    def setUp(self):
        self.maxDiff = None
        self.tms_module = "rok4_tools.tms2stuff.TileMatrixSet"
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
        level_id = "15"
        m_argv = [
            "rok4_tools/tms2stuff.py",
            "PM",
            "BBOX:753363.55,1688952.65,757025.90,1692621.45",
            "GETTILE_PARAMS",
            "--level", level_id,
        ]
        m_bbox_to_tiles = MagicMock(
            name="bbox_to_tiles",
            return_value=(17000, 15000, 17002, 15002)
        )
        self.m_tm.attach_mock(m_bbox_to_tiles, 'bbox_to_tiles')

        with patch("sys.argv", m_argv), \
                patch("sys.stdout", self.m_stdout), \
                patch("sys.stderr", self.m_stderr), \
                patch(f"{self.tms_module}.TileMatrixSet", self.m_tms_c), \
                self.assertRaises(SystemExit) as cm:
            tms2stuff.main()

        stdout_content = self.m_stdout.getvalue()
        stderr_content = self.m_stderr.getvalue()
        self.assertEqual(cm.exception.code, 0, msg="exit code should be 0")
        self.assertEqual(stderr_content, "",
            msg=f"no error message should appear")
        self.m_tms_c.assert_called_once_with(m_argv[1])
        self.m_tms_i.get_level.assert_called_once_with(level_id)
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
            expected_output = (f"{expected_output}TILEMATRIX={level_id}"
                + f"&TILECOL={item[0]}&TILEROW={item[1]}\n")
        self.assertEqual(stdout_content, expected_output, 
            "unexpected console output")

    def test_tile_to_getmap_pm_ok(self):
        """Test tile indices to GetMap conversion in the PM TMS.

        Characteristics:
            TMS: PM
            Input: tile indices
            Output: WMS GetMap parameters
        """
        level_id = "15"
        m_argv = [
            "rok4_tools/tms2stuff.py",
            "PM",
            "TILE_INDICE:17000,15000",
            "GETMAP_PARAMS",
            "--level", level_id,
        ]
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

        with patch("sys.argv", m_argv), \
                patch("sys.stdout", self.m_stdout), \
                patch("sys.stderr", self.m_stderr), \
                patch(f"{self.tms_module}.TileMatrixSet", self.m_tms_c), \
                self.assertRaises(SystemExit) as cm:
            tms2stuff.main()

        stdout_content = self.m_stdout.getvalue()
        stderr_content = self.m_stderr.getvalue()
        self.assertEqual(cm.exception.code, 0, msg="exit code should be 0")
        self.assertEqual(stderr_content, "",
            msg=f"no error message should appear")
        self.m_tms_c.assert_called_once_with(m_argv[1])
        self.m_tms_i.get_level.assert_called_once_with(level_id)
        m_tile_to_bbox.assert_called_once_with(tile_col=17000, tile_row=15000)
        expected_output = (
            f"WIDTH={m_tile_size[0]}"
            + f"&HEIGHT={m_tile_size[1]}"
            + f"&BBOX={m_bbox[0]},{m_bbox[1]},{m_bbox[2]},{m_bbox[3]}"
            + f"&CRS={m_projection}\n"
        )
        self.assertEqual(stdout_content, expected_output, 
            "unexpected console output")


    def test_bbox_to_slab_indices_pm_ok(self):
        """Test BBOX to GetTile conversion in the PM TMS.

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
        m_argv = [
            "rok4_tools/tms2stuff.py",
            "PM",
            f"BBOX:{m_bbox[0]},{m_bbox[1]},{m_bbox[2]},{m_bbox[3]}",
            "SLAB_INDICES",
            "--level", level_id,
            "--slabsize", "16x10",
        ]

        with patch("sys.argv", m_argv), \
                patch("sys.stdout", self.m_stdout), \
                patch("sys.stderr", self.m_stderr), \
                patch(f"{self.tms_module}.TileMatrixSet", self.m_tms_c), \
                self.assertRaises(SystemExit) as cm:
            tms2stuff.main()

        stdout_content = self.m_stdout.getvalue()
        stderr_content = self.m_stderr.getvalue()
        self.assertEqual(cm.exception.code, 0, msg="exit code should be 0")
        self.assertEqual(stderr_content, "",
            msg=f"no error message should appear")
        self.m_tms_c.assert_called_once_with(m_argv[1])
        self.m_tms_i.get_level.assert_called_once_with(level_id)
        expected_output = "49,31\n49,32\n50,31\n50,32\n"
        self.assertEqual(stdout_content, expected_output, 
            "unexpected console output")

