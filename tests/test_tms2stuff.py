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

class TestMain(TestCase):
    """Test generic CLI calls to the tool's executable."""

    def test_help(self):
        m_argv = [
            "rok4_tools/tms2stuff.py",
            "-h",
        ]
        m_stdout = StringIO()

        with patch("sys.argv", m_argv), patch("sys.stdout", m_stdout), \
                self.assertRaises(SystemExit) as cm:
            main()
        
        self.assertEqual(cm.exception.code, 0,
            msg="Executable's exit code was not from 0.")
        self.assertRegex(m_stdout.getvalue(), "^usage:")


class TestBBoxToGetTile(TestCase):
    """Test conversion from BBOX to GetTile parameters"""

    def test_bbox_to_tile(self):
        m_argv = [
            "rok4_tools/tms2stuff.py",
            "--tms", "PM",
            "--level", "15",
            "--from", "BBOX:-5990500.00,487500.00,5822500.00,642500.00",
            "--to", "GETTILE_PARAMS",
        ]

        with patch("sys.argv", m_argv), \
                self.assertRaises(SystemExit) as cm:
            main()
        
        self.assertEqual(cm.exception.code, 0,
            msg="Executable's exit code was not from 0.")

