"""Describes unit tests for the rok4_tools.tms2stuff executable module

There is one test class for each tested functionnality.
See internal docstrings for more information.
Each variable prefixed by "m_" is a mock, or part of it.
"""

import math
import pytest
import sys
from unittest import mock, TestCase
from unittest.mock import call, MagicMock, Mock, mock_open, patch

from rok4_tools.tms2stuff import main

class TestMain(TestCase):
    """Test CLI calls to the tool's executable."""


    @patch("rok4_tools.tms2stuff.bbox_to_tile")
    @patch("sys.exit")
    def test_bbox_to_tile(self, m_exit, m_conversion):
        m_argv = [
            "rok4_tools/tms2stuff.py",
            "--tms", "PM",
            "--level", "15",
            "--from", "BBOX:-5990500.00,487500.00,5822500.00,642500.00",
            "--to", "GETTILE_PARAMS",
        ]

        with patch("sys.argv", m_argv):
            main()

        
        m_exit.assert_called_once_with(0)

class TestBBoxToGetTile(TestCase):
    """Test conversion from BBOX to GetTile parameters"""

