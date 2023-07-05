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
from unittest import mock, TestCase
from unittest.mock import call, MagicMock, Mock, mock_open, patch

from rok4_tools import tms2stuff

class TestGenericOptions(TestCase):
    """Test generic CLI calls to the tool's executable."""

    def test_help(self):
        """Help / usage display options"""
        m_argv = [
            ["rok4_tools/tms2stuff.py", "-h"],
            ["rok4_tools/tms2stuff.py", "--help"],
        ]
        i = 0
        for args in m_argv:
            m_stdout = StringIO()
            with patch("sys.argv", args), patch("sys.stdout", m_stdout), \
                    self.assertRaises(SystemExit) as cm:
                tms2stuff.main()

            self.assertEqual(cm.exception.code, 0,
                msg=f"exit code should be 0 (option '{args[1]}')")
            stdout_content = m_stdout.getvalue()
            self.assertRegex(stdout_content, "\n *optional arguments:",
                msg=f"help message should appear (option '{args[1]}')")
            i = i + 1

    def test_version(self):
        """Version display option"""
        m_argv = ["rok4_tools/tms2stuff.py", "--version"]
        m_stdout = StringIO()

        with patch("sys.argv", m_argv), patch("sys.stdout", m_stdout), \
                self.assertRaises(SystemExit) as cm:
            tms2stuff.main()

        self.assertEqual(cm.exception.code, 0, msg="exit code should be 0")
        stdout_content = m_stdout.getvalue()
        self.assertRegex(stdout_content, "^[0-9]+[.][0-9]+[.][0-9]+")


class TestBBoxToGetTile(TestCase):
    """Test conversion from BBOX to GetTile parameters"""

    def setUp(self):
        self.maxDiff = None

    def test_ok_PM(self):
        m_tms_dir = "/opt/tile_matrix_set"
        m_env = {
            "ROK4_TMS_DIRECTORY": m_tms_dir
        }
        level_id = "15"
        m_argv = [
            "rok4_tools/tms2stuff.py",
            "PM",
            "BBOX:753363.55,1688952.65,757025.90,1692621.45",
            "GETTILE_PARAMS",
            "--level", level_id,
        ]
        m_stdout = StringIO()
        m_tms_def = {
            "tileMatrices" : [
                {
                    "id" : "14",
                    "cellSize" : 9.55462853564703,
                    "matrixHeight" : 16384,
                    "pointOfOrigin" : [
                        -20037508.3427892,
                        20037508.3427892
                    ],
                    "tileHeight" : 256,
                    "tileWidth" : 256,
                    "scaleDenominator" : 34123.6733415965,
                    "matrixWidth" : 16384
                },
                {
                    "tileWidth" : 256,
                    "scaleDenominator" : 17061.8366707983,
                    "matrixWidth" : 32768,
                    "cellSize" : 4.77731426782352,
                    "matrixHeight" : 32768,
                    "tileHeight" : 256,
                    "pointOfOrigin" : [
                        -20037508.3427892,
                        20037508.3427892
                    ],
                    "id" : "15"
                },
                {
                    "tileHeight" : 256,
                    "pointOfOrigin" : [
                        -20037508.3427892,
                        20037508.3427892
                    ],
                    "matrixHeight" : 65536,
                    "cellSize" : 2.38865713391176,
                    "matrixWidth" : 65536,
                    "scaleDenominator" : 8530.91833539914,
                    "tileWidth" : 256,
                    "id" : "16"
                }
            ],
            "crs" : "EPSG:3857",
            "orderedAxes" : [
                "X",
                "Y"
            ],
            "id" : "PM"
        }


        m_open = mock_open(read_data=json.dumps(m_tms_def))
        with patch("sys.argv", m_argv), patch("sys.stdout", m_stdout), \
                patch("os.environ", m_env), patch("builtins.open", m_open), \
                self.assertRaises(SystemExit) as cm:
            tms2stuff.main()

        self.assertEqual(cm.exception.code, 0, msg="exit code should be 0")
        m_open.assert_called_once_with(f"{m_tms_dir}/PM.json", "r")
        stdout_content = m_stdout.getvalue()
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
        self.assertEqual(stdout_content, expected_output, "unexpected console output")

