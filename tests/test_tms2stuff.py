"""Describes unit tests for the rok4_tools.tms2stuff executable module

There is one test class for each tested functionnality.
See internal docstrings for more information.
Each variable prefixed by "m_" is a mock, or part of it.
"""
from io import StringIO
import math
import pytest
import sys
from unittest import mock, TestCase
from unittest.mock import call, MagicMock, Mock, mock_open, patch

from rok4_tools.tms2stuff import main

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
                main()
            
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
            main()
        
        self.assertEqual(cm.exception.code, 0, msg="exit code should be 0")
        stdout_content = m_stdout.getvalue()
        self.assertRegex(stdout_content, "^[0-9]+[.][0-9]+[.][0-9]+")


class TestBBoxToGetTile(TestCase):
    """Test conversion from BBOX to GetTile parameters"""

    def test_bbox_to_tile(self):
        m_argv = [
            "rok4_tools/tms2stuff.py",
            "PM",
            "BBOX:-5990500.00,487500.00,5822500.00,642500.00",
            "GETTILE_PARAMS",
            "--level", "15",
        ]
        m_stdout = StringIO()

        with patch("sys.argv", m_argv), patch("sys.stdout", m_stdout), \
                self.assertRaises(SystemExit) as cm:
            main()
        
        self.assertEqual(cm.exception.code, 0, msg="exit code should be 0")
        stdout_content = m_stdout.getvalue()
        self.assertRegex(stdout_content, "^TILEMATRIX=[0-9A-Za-z_-]+&TILECOL=[0-9]+&TILEROW=[0-9]+$")

