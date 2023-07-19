#!/bin/env python
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

from osgeo import ogr

from rok4_tools import tms2stuff


class TestArgumentsParsing(TestCase):
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


class TestArgumentsTransformation(TestCase):
    """Test post-parsing arguments transformation functions"""

    def test_read_bbox_ok(self):
        """Test valid call to tms2stuff.read_bbox()"""
        bbox = (-12.5, 0, 23, 65.781)
        result = tms2stuff.read_bbox(
            f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}")
        self.assertEqual(result, bbox)

    def test_read_bbox_nok_with_message(self):
        """Test invalid call to tms2stuff.read_bbox()
        Optional error message included
        """
        message = "This is the expected error message."
        with self.assertRaises(ValueError) as cm:
            tms2stuff.read_bbox("('-12.5', '0', '23', '65.781')",
            message)
        self.assertEqual(str(cm.exception), message)

    def test_read_bbox_nok_default(self):
        """Test invalid call to tms2stuff.read_bbox()
        Default error message.
        """
        with self.assertRaises(ValueError) as cm:
            tms2stuff.read_bbox("('-12.5', '0', '23', '65.781')")
        self.assertRegex(str(cm.exception),
            "Invalid BBOX: .*\nExpected BBOX format is .*")

class TestProcessingFunctions(TestCase):
    """Test data processing functions"""

    def setUp(self):
        self.mod = "rok4_tools.tms2stuff"
        self.maxDiff = None
        self.m_tms_i = MagicMock(name="TileMatrixSet")
        self.m_tms_c = MagicMock(name="TileMatrixSet()",
            return_value=self.m_tms_i)
        self.m_tm = MagicMock(name="TileMatrix")
        self.m_tms_i.get_level = MagicMock(return_value=self.m_tm)

    def test_bbox_to_gettile_ok(self):
        """Nominal bbox_to_gettile() call"""
        bbox = (753363.55, 1688952.65, 757025.90, 1692621.45)
        tile_range = (17000, 15000, 17002, 15002)
        m_bbox_to_tiles = MagicMock(
            name="bbox_to_tiles",
            return_value=tile_range
        )
        self.m_tm.id = "13"
        self.m_tm.attach_mock(m_bbox_to_tiles, 'bbox_to_tiles')
        expected = []
        for column in range(tile_range[0], tile_range[2] +1 , 1):
            for row in range(tile_range[1], tile_range[3] +1 , 1):
                expected.append(f"TILEMATRIX={self.m_tm.id}"
                    + f"&TILECOL={column}&TILEROW={row}")

        with patch(f"{self.mod}.TileMatrixSet", self.m_tms_c):
            result = tms2stuff.bbox_to_gettile(self.m_tm, bbox)

        m_bbox_to_tiles.assert_called_once_with(bbox)
        self.assertEqual(result, expected)

    def test_bbox_to_gettile_intersection_ok(self):
        """Nominal bbox_to_gettile() call"""
        bbox = (63125978.43148272, -53356714.7204109, 
            63140654.340913475, -53342038.81098014)
        tile_range = (17000, 15000, 17002, 15002)
        self.m_tm.id = "13"
        m_bbox_to_tiles = MagicMock(
            name="bbox_to_tiles",
            return_value=tile_range
        )
        self.m_tm.attach_mock(m_bbox_to_tiles, 'bbox_to_tiles')
        m_tile_to_bbox = MagicMock(name="tile_to_bbox", return_value=bbox)
        self.m_tm.attach_mock(m_tile_to_bbox, 'tile_to_bbox')
        reference = ogr.Geometry(ogr.wkbPolygon)
        intersect_list = [True, True, True, True, True, False, True, False,
            False]
        m_intersects = MagicMock(
            name="container.Intersects",
            side_effect=intersect_list
        )
        expected = []
        calls_list = []
        for column in range(tile_range[0], tile_range[2] + 1):
            for row in range(tile_range[1], tile_range[3] + 1):
                calls_list.append(call(column, row))
                if (column + row) <= (sum(tile_range)/2):
                    expected.append(f"TILEMATRIX={self.m_tm.id}"
                        + f"&TILECOL={column}&TILEROW={row}")

        with patch(f"{self.mod}.TileMatrixSet", self.m_tms_c), \
                patch('ogr.Geometry.Intersects', m_intersects):
            result = tms2stuff.bbox_to_gettile(self.m_tm, bbox, reference)

        m_bbox_to_tiles.assert_called_once_with(bbox)
        m_tile_to_bbox.assert_has_calls(calls_list)
        self.assertEqual(m_intersects.call_count, 9)
        self.assertEqual(result, expected)

    def test_bbox_to_slab_list_ok(self):
        """Nominal bbox_to_slab_list() call"""
        bbox = (625000.89, 6532000.12, 680000.65, 6650000.25)
        slab_size = (16, 10)
        m_bbox_to_tiles = MagicMock(
            name="bbox_to_tiles",
            return_value=(95, 816, 103, 834)
        )
        self.m_tm.id = "13"
        self.m_tm.attach_mock(m_bbox_to_tiles, 'bbox_to_tiles')
        expected = [
            (5, 81),
            (5, 82),
            (5, 83),
            (6, 81),
            (6, 82),
            (6, 83),
        ]

        with patch(f"{self.mod}.TileMatrixSet", self.m_tms_c):
            result = tms2stuff.bbox_to_slab_list(self.m_tm, bbox, slab_size)

        m_bbox_to_tiles.assert_called_once_with(bbox)
        self.assertEqual(result, expected)

    def test_bbox_to_slab_list_intersection_ok(self):
        """Nominal bbox_to_slab_list() call"""
        bbox = (625000.89, 6532000.12, 680000.65, 6650000.25)
        slab_size = (16, 10)
        self.m_tm.id = "13"
        m_bbox_to_tiles = MagicMock(
            name="bbox_to_tiles",
            return_value=(95, 816, 103, 834)
        )
        self.m_tm.attach_mock(m_bbox_to_tiles, 'bbox_to_tiles')
        m_tile_to_bbox = MagicMock(name="tile_to_bbox", return_value=bbox)
        self.m_tm.attach_mock(m_tile_to_bbox, 'tile_to_bbox')
        reference = ogr.Geometry(ogr.wkbPolygon)
        intersect_list = [True, False, True, True, True, False]
        m_intersects = MagicMock(
            name="container.Intersects",
            side_effect=intersect_list
        )
        calls_list = []
        expected = [
            (5, 81),
            (5, 83),
            (6, 81),
            (6, 82),
        ]

        with patch(f"{self.mod}.TileMatrixSet", self.m_tms_c), \
                patch('ogr.Geometry.Intersects', m_intersects):
            result = tms2stuff.bbox_to_slab_list(self.m_tm, bbox, slab_size,
                reference)

        m_bbox_to_tiles.assert_called_once_with(bbox)
        m_tile_to_bbox.assert_has_calls(calls_list)
        self.assertEqual(m_intersects.call_count, 6)
        self.assertEqual(result, expected)

class TestMain(TestCase):
    """Test main() function"""

    def setUp(self):
        self.mod = "rok4_tools.tms2stuff"
        self.maxDiff = None
        self.m_tms_i = MagicMock(name="TileMatrixSet")
        self.m_tms_c = MagicMock(name="TileMatrixSet()",
            return_value=self.m_tms_i)
        self.m_tm = MagicMock(name="TileMatrix")
        self.m_tms_i.get_level = MagicMock(return_value=self.m_tm)
        self.m_stdout = StringIO()

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
        self.m_tm.id = args["level"]

        with patch("sys.stdout", self.m_stdout), \
                patch(f"{self.mod}.TileMatrixSet", self.m_tms_c):
            tms2stuff.main(args)

        stdout_content = self.m_stdout.getvalue()
        self.m_tms_c.assert_called_once_with(args["tms_name"])
        self.m_tms_i.get_level.assert_called_once_with(args["level"])
        m_bbox_to_tiles.assert_called_once_with(
            (753363.55, 1688952.65, 757025.90, 1692621.45)
        )
        expected_match_list = [
            (17000, 15000),
            (17000, 15001),
            (17000, 15002),
            (17001, 15000),
            (17001, 15001),
            (17001, 15002),
            (17002, 15000),
            (17002, 15001),
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
        bbox = (-19060337.37, 19644927.76, -19057891.39, 19647373.75)
        slab_size = (16, 10)
        slabs_list = [
            (49, 31),
            (49, 32),
            (50, 31),
            (50, 32),
        ]
        m_bbox_to_slab_list = MagicMock(name="bbox_to_slab_list",
            return_value=slabs_list)
        args = {
            "tms_name": "PM",
            "input": f"BBOX:{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
            "output": "SLAB_INDICES",
            "level": "15",
            "slabsize": f"{slab_size[0]}x{slab_size[1]}",
        }

        with patch("sys.stdout", self.m_stdout), \
                patch(f"{self.mod}.TileMatrixSet", self.m_tms_c), \
                patch(f"{self.mod}.bbox_to_slab_list", m_bbox_to_slab_list):
            tms2stuff.main(args)

        stdout_content = self.m_stdout.getvalue()
        self.m_tms_c.assert_called_once_with(args["tms_name"])
        self.m_tms_i.get_level.assert_called_once_with(args["level"])
        m_bbox_to_slab_list.assert_called_once_with(self.m_tm, bbox, slab_size)
        expected_output = ""
        for slab in slabs_list:
            expected_output = expected_output + f"{slab[0]},{slab[1]}\n"
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
        file_path = "s3://temporary/bbox_list.txt"
        slab_size = (16, 10)
        bbox_list = [
            (-19060337.37, 19646150.75, -19059114.38, 19647373.75),
            (-19060337.37, 19644927.76, -19059114.38, 19646150.75),
            (-19060337.37, 19643704.77, -19059114.38, 19644927.76),
            (-19059114.38, 19643704.77, -19057891.38, 19647373.75),
            (-19835714.58, 19736652.19, -19834491.59, 19737875.19),
            (-19827153.64, 19731760.22, -19825930.64, 19732983.22),
        ]
        list_content = ""
        calls_list = []
        for bbox in bbox_list:
            bbox_string = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
            list_content = list_content + bbox_string + "\n"
            calls_list.append(call(self.m_tm, bbox, slab_size))
        m_get_data = MagicMock(name="get_data_str", return_value=list_content)
        m_exists = MagicMock(name="exists", return_value=True)
        args = {
            "tms_name": "PM",
            "input": f"BBOXES_LIST:{file_path}",
            "output": "SLAB_INDICES",
            "level": "15",
            "slabsize": f"{slab_size[0]}x{slab_size[1]}",
        }
        slab_intermediate_list = [
            [(49, 31), (49, 32), (50, 31), (50, 32)],
            [(49, 32), (50, 32)],
            [(49, 32), (50, 32)],
            [(50, 31), (50, 32)],
            [(10, 24)],
            [(10, 24), (10, 25)],
        ]
        m_bbox_to_slab_list = MagicMock(name="bbox_to_slab_list",
            side_effect=slab_intermediate_list)

        with patch("sys.stdout", self.m_stdout), \
                patch(f"{self.mod}.TileMatrixSet", self.m_tms_c), \
                patch(f"{self.mod}.exists", m_exists), \
                patch(f"{self.mod}.get_data_str", m_get_data), \
                patch(f"{self.mod}.bbox_to_slab_list", m_bbox_to_slab_list):
            tms2stuff.main(args)

        stdout_content = self.m_stdout.getvalue()
        self.m_tms_c.assert_called_once_with(args["tms_name"])
        self.m_tms_i.get_level.assert_called_once_with(args["level"])
        m_exists.assert_called_once_with(file_path)
        m_get_data.assert_called_once_with(file_path)
        m_bbox_to_slab_list.assert_has_calls(calls_list)
        slabs_list = [
            (10,24),
            (10,25),
            (49,31),
            (49,32),
            (50,31),
            (50,32),
        ]
        expected_output = ""
        for slab in slabs_list:
            expected_output = expected_output + f"{slab[0]},{slab[1]}\n"
        self.assertEqual(stdout_content, expected_output,
            "unexpected console output")

    def test_wkt_file_to_gettile_l93_ok(self):
        """Test conversion from a WKT geometry file to
            WMTS GetTile query parameters in the LAMB93_5cm TMS.

        Characteristics:
            TMS: LAMB93_5cm
            Input: path to a existing file or object describing
                a WKT geometry
            Output: WMTS GetTile query parameters
        """
        file_path = "file:///tmp/geom.wkt"
        args = {
            "tms_name": "LAMB93_5cm",
            "input": f"GEOM_FILE:{file_path}",
            "output": "GETTILE_PARAMS",
            "level": "13",
        }
        bbox = (625000.00, 6532000.00, 645000.00, 6545000.00)
        file_content = ("POLYGON(("
            + f"{bbox[0]} {bbox[1]},"
            + f"{bbox[2]} {bbox[1]},"
            + f"{bbox[2]} {bbox[3]},"
            + f"{bbox[0]} {bbox[3]},"
            + f"{bbox[0]} {bbox[1]}"
            + "))")
        m_get_data = MagicMock(name="get_data_str", return_value=file_content)
        m_exists = MagicMock(name="exists", return_value=True)
        query_list = [
            "TILEMATRIX=13&TILECOL=95&TILEROW=832",
            "TILEMATRIX=13&TILECOL=95&TILEROW=833",
            "TILEMATRIX=13&TILECOL=95&TILEROW=834",
            "TILEMATRIX=13&TILECOL=96&TILEROW=832",
            "TILEMATRIX=13&TILECOL=96&TILEROW=833",
            "TILEMATRIX=13&TILECOL=96&TILEROW=834",
            "TILEMATRIX=13&TILECOL=97&TILEROW=832",
            "TILEMATRIX=13&TILECOL=97&TILEROW=833",
            "TILEMATRIX=13&TILECOL=97&TILEROW=834",
            "TILEMATRIX=13&TILECOL=98&TILEROW=832",
            "TILEMATRIX=13&TILECOL=98&TILEROW=833",
            "TILEMATRIX=13&TILECOL=98&TILEROW=834",
        ]
        m_bbox_to_gettile = MagicMock(name="bbox_to_gettile",
            return_value=query_list)
        expected_output = "\n".join(query_list) + "\n"

        with patch("sys.stdout", self.m_stdout), \
                patch(f"{self.mod}.TileMatrixSet", self.m_tms_c), \
                patch(f"{self.mod}.exists", m_exists), \
                patch(f"{self.mod}.get_data_str", m_get_data), \
                patch(f"{self.mod}.bbox_to_gettile", m_bbox_to_gettile):
            tms2stuff.main(args)

        stdout_content = self.m_stdout.getvalue()
        self.m_tms_c.assert_called_once_with(args["tms_name"])
        self.m_tms_i.get_level.assert_called_once_with(args["level"])
        m_exists.assert_called_once_with(file_path)
        m_get_data.assert_called_once_with(file_path)
        m_bbox_to_gettile.assert_called_once()
        self.assertEqual(
            m_bbox_to_gettile.call_args.args[0:2], (self.m_tm, bbox),
            f"Unexpected arguments for call to bbox_to_gettile."
        )
        self.assertEqual(stdout_content, expected_output,
            "unexpected console output")

    def test_gml_file_to_gettile_l93_ok(self):
        """Test conversion from a GML geometry file to
            WMTS GetTile query parameters in the LAMB93_5cm TMS.

        Characteristics:
            TMS: LAMB93_5cm
            Input: path to a existing file or object describing
                a GML geometry
            Output: WMTS GetTile query parameters
        """
        file_path = "file:///tmp/geom.gml"
        args = {
            "tms_name": "LAMB93_5cm",
            "input": f"GEOM_FILE:{file_path}",
            "output": "GETTILE_PARAMS",
            "level": "13",
        }
        bbox = (625000.00, 6532000.00, 645000.00, 6545000.00)
        file_content = (
            "<gml:Polygon><gml:outerBoundaryIs>"
            + "<gml:LinearRing><gml:coordinates>"
            + f"{bbox[0]},{bbox[1]} "
            + f"{bbox[2]},{bbox[1]} "
            + f"{bbox[2]},{bbox[3]} "
            + f"{bbox[0]},{bbox[3]} "
            + f"{bbox[0]},{bbox[1]}"
            + "</gml:coordinates></gml:LinearRing>"
            + "</gml:outerBoundaryIs></gml:Polygon>"
        )
        m_get_data = MagicMock(name="get_data_str", return_value=file_content)
        m_exists = MagicMock(name="exists", return_value=True)
        query_list = [
            "TILEMATRIX=13&TILECOL=95&TILEROW=832",
            "TILEMATRIX=13&TILECOL=95&TILEROW=833",
            "TILEMATRIX=13&TILECOL=95&TILEROW=834",
            "TILEMATRIX=13&TILECOL=96&TILEROW=832",
            "TILEMATRIX=13&TILECOL=96&TILEROW=833",
            "TILEMATRIX=13&TILECOL=96&TILEROW=834",
            "TILEMATRIX=13&TILECOL=97&TILEROW=832",
            "TILEMATRIX=13&TILECOL=97&TILEROW=833",
            "TILEMATRIX=13&TILECOL=97&TILEROW=834",
            "TILEMATRIX=13&TILECOL=98&TILEROW=832",
            "TILEMATRIX=13&TILECOL=98&TILEROW=833",
            "TILEMATRIX=13&TILECOL=98&TILEROW=834",
        ]
        m_bbox_to_gettile = MagicMock(name="bbox_to_gettile",
            return_value=query_list)
        expected_output = "\n".join(query_list) + "\n"

        with patch("sys.stdout", self.m_stdout), \
                patch(f"{self.mod}.TileMatrixSet", self.m_tms_c), \
                patch(f"{self.mod}.exists", m_exists), \
                patch(f"{self.mod}.get_data_str", m_get_data), \
                patch(f"{self.mod}.bbox_to_gettile", m_bbox_to_gettile):
            tms2stuff.main(args)

        stdout_content = self.m_stdout.getvalue()
        self.m_tms_c.assert_called_once_with(args["tms_name"])
        self.m_tms_i.get_level.assert_called_once_with(args["level"])
        m_exists.assert_called_once_with(file_path)
        m_get_data.assert_called_once_with(file_path)
        m_bbox_to_gettile.assert_called_once()
        self.assertEqual(
            m_bbox_to_gettile.call_args.args[0:2], (self.m_tm, bbox),
            f"Unexpected arguments for call to bbox_to_gettile."
        )
        self.assertEqual(stdout_content, expected_output,
            "unexpected console output")

    def test_geojson_file_to_gettile_l93_ok(self):
        """Test conversion from a GeoJSON geometry file to
            WMTS GetTile query parameters in the LAMB93_5cm TMS.

        Characteristics:
            TMS: LAMB93_5cm
            Input: path to a existing file or object describing
                a GeoJSON geometry
            Output: WMTS GetTile query parameters
        """
        file_path = "file:///tmp/geom.geojson"
        args = {
            "tms_name": "LAMB93_5cm",
            "input": f"GEOM_FILE:{file_path}",
            "output": "GETTILE_PARAMS",
            "level": "13",
        }
        bbox = (625000.00, 6532000.00, 645000.00, 6545000.00)
        file_content = json.dumps({
            "type": "Polygon",
            "coordinates": [[
                [bbox[0], bbox[1]],
                [bbox[2], bbox[1]],
                [bbox[2], bbox[3]],
                [bbox[0], bbox[3]],
                [bbox[0], bbox[1]],
            ]]
        })
        m_get_data = MagicMock(name="get_data_str", return_value=file_content)
        m_exists = MagicMock(name="exists", return_value=True)
        query_list = [
            "TILEMATRIX=13&TILECOL=95&TILEROW=832",
            "TILEMATRIX=13&TILECOL=95&TILEROW=833",
            "TILEMATRIX=13&TILECOL=95&TILEROW=834",
            "TILEMATRIX=13&TILECOL=96&TILEROW=832",
            "TILEMATRIX=13&TILECOL=96&TILEROW=833",
            "TILEMATRIX=13&TILECOL=96&TILEROW=834",
            "TILEMATRIX=13&TILECOL=97&TILEROW=832",
            "TILEMATRIX=13&TILECOL=97&TILEROW=833",
            "TILEMATRIX=13&TILECOL=97&TILEROW=834",
            "TILEMATRIX=13&TILECOL=98&TILEROW=832",
            "TILEMATRIX=13&TILECOL=98&TILEROW=833",
            "TILEMATRIX=13&TILECOL=98&TILEROW=834",
        ]
        m_bbox_to_gettile = MagicMock(name="bbox_to_gettile",
            return_value=query_list)
        expected_output = "\n".join(query_list) + "\n"

        with patch("sys.stdout", self.m_stdout), \
                patch(f"{self.mod}.TileMatrixSet", self.m_tms_c), \
                patch(f"{self.mod}.exists", m_exists), \
                patch(f"{self.mod}.get_data_str", m_get_data), \
                patch(f"{self.mod}.bbox_to_gettile", m_bbox_to_gettile):
            tms2stuff.main(args)

        stdout_content = self.m_stdout.getvalue()
        self.m_tms_c.assert_called_once_with(args["tms_name"])
        self.m_tms_i.get_level.assert_called_once_with(args["level"])
        m_exists.assert_called_once_with(file_path)
        m_get_data.assert_called_once_with(file_path)
        m_bbox_to_gettile.assert_called_once()
        self.assertEqual(
            m_bbox_to_gettile.call_args.args[0:2], (self.m_tm, bbox),
            f"Unexpected arguments for call to bbox_to_gettile."
        )
        self.assertEqual(stdout_content, expected_output,
            "unexpected console output")

    def test_wkb_file_to_gettile_l93_ok(self):
        """Test conversion from a WKB geometry file to
            WMTS GetTile query parameters in the LAMB93_5cm TMS.

        Characteristics:
            TMS: LAMB93_5cm
            Input: path to a existing file or object describing
                a WKB geometry
            Output: WMTS GetTile query parameters
        """
        file_path = "file:///tmp/geom.wkb"
        args = {
            "tms_name": "LAMB93_5cm",
            "input": f"GEOM_FILE:{file_path}",
            "output": "GETTILE_PARAMS",
            "level": "13",
        }
        bbox = (625000.00, 6532000.00, 645000.00, 6545000.00)
        file_content = b"\x00\x00\x00\x00\x03\x00\x00\x00\x01\x00\x00\x00\x05A#\x12\xd0\x00\x00\x00\x00AX\xea\xe8\x00\x00\x00\x00A#\xaf\x10\x00\x00\x00\x00AX\xea\xe8\x00\x00\x00\x00A#\xaf\x10\x00\x00\x00\x00AX\xf7\x9a\x00\x00\x00\x00A#\x12\xd0\x00\x00\x00\x00AX\xf7\x9a\x00\x00\x00\x00A#\x12\xd0\x00\x00\x00\x00AX\xea\xe8\x00\x00\x00\x00"
        m_get_data = MagicMock(name="get_data_str", return_value=file_content)
        m_exists = MagicMock(name="exists", return_value=True)
        query_list = [
            "TILEMATRIX=13&TILECOL=95&TILEROW=832",
            "TILEMATRIX=13&TILECOL=95&TILEROW=833",
            "TILEMATRIX=13&TILECOL=95&TILEROW=834",
            "TILEMATRIX=13&TILECOL=96&TILEROW=832",
            "TILEMATRIX=13&TILECOL=96&TILEROW=833",
            "TILEMATRIX=13&TILECOL=96&TILEROW=834",
            "TILEMATRIX=13&TILECOL=97&TILEROW=832",
            "TILEMATRIX=13&TILECOL=97&TILEROW=833",
            "TILEMATRIX=13&TILECOL=97&TILEROW=834",
            "TILEMATRIX=13&TILECOL=98&TILEROW=832",
            "TILEMATRIX=13&TILECOL=98&TILEROW=833",
            "TILEMATRIX=13&TILECOL=98&TILEROW=834",
        ]
        m_bbox_to_gettile = MagicMock(name="bbox_to_gettile",
            return_value=query_list)
        expected_output = "\n".join(query_list) + "\n"

        with patch("sys.stdout", self.m_stdout), \
                patch(f"{self.mod}.TileMatrixSet", self.m_tms_c), \
                patch(f"{self.mod}.exists", m_exists), \
                patch(f"{self.mod}.get_data_str", m_get_data), \
                patch(f"{self.mod}.bbox_to_gettile", m_bbox_to_gettile):
            tms2stuff.main(args)

        stdout_content = self.m_stdout.getvalue()
        self.m_tms_c.assert_called_once_with(args["tms_name"])
        self.m_tms_i.get_level.assert_called_once_with(args["level"])
        m_exists.assert_called_once_with(file_path)
        m_get_data.assert_called_once_with(file_path)
        m_bbox_to_gettile.assert_called_once()
        self.assertEqual(
            m_bbox_to_gettile.call_args.args[0:2], (self.m_tm, bbox),
            f"Unexpected arguments for call to bbox_to_gettile."
        )
        self.assertEqual(stdout_content, expected_output,
            "unexpected console output")

    def test_wkt_file_to_gettile_l93_nok(self):
        """Test conversion from an invalid WKT geometry file to
            WMTS GetTile query parameters in the LAMB93_5cm TMS.

        Characteristics:
            TMS: LAMB93_5cm
            Input: path to a existing file or object describing
                a WKT geometry
            Output: WMTS GetTile query parameters
        """
        file_path = "file:///tmp/geom.wkt"
        args = {
            "tms_name": "LAMB93_5cm",
            "input": f"GEOM_FILE:{file_path}",
            "output": "GETTILE_PARAMS",
            "level": "13",
        }
        bbox = (625000.00, 6532000.00, 645000.00, 6545000.00)
        file_content = ("POLYGON("
            + f"{bbox[0]} {bbox[1]},"
            + f"{bbox[2]} {bbox[1]},"
            + f"{bbox[2]} {bbox[3]},"
            + f"{bbox[0]} {bbox[3]},"
            + f"{bbox[0]} {bbox[1]}"
            + ")")
        m_get_data = MagicMock(name="get_data_str", return_value=file_content)
        m_exists = MagicMock(name="exists", return_value=True)
        m_bbox_to_gettile = MagicMock(name="bbox_to_gettile")

        with patch("sys.stdout", self.m_stdout), \
                patch(f"{self.mod}.TileMatrixSet", self.m_tms_c), \
                patch(f"{self.mod}.exists", m_exists), \
                patch(f"{self.mod}.get_data_str", m_get_data), \
                patch(f"{self.mod}.bbox_to_gettile", m_bbox_to_gettile), \
                self.assertRaises(tms2stuff.GeometryError) as cm:
            tms2stuff.main(args)

        stdout_content = self.m_stdout.getvalue()
        self.m_tms_c.assert_called_once_with(args["tms_name"])
        self.m_tms_i.get_level.assert_called_once_with(args["level"])
        m_exists.assert_called_once_with(file_path)
        m_get_data.assert_called_once_with(file_path)
        m_bbox_to_gettile.assert_not_called()
        self.assertEqual(stdout_content, "", "unexpected console output")
        self.assertRegex(str(cm.exception), "^Input geometry error in file.*",
            "unexpected error message")

    def test_geom_file_to_gettile_l93_nok(self):
        """Test conversion from an unidentified geometry file to
            WMTS GetTile query parameters in the LAMB93_5cm TMS.

        Characteristics:
            TMS: LAMB93_5cm
            Input: path to a existing file or object describing
                a WKT geometry
            Output: WMTS GetTile query parameters
        """
        file_path = "file:///tmp/geom.unknown"
        args = {
            "tms_name": "LAMB93_5cm",
            "input": f"GEOM_FILE:{file_path}",
            "output": "GETTILE_PARAMS",
            "level": "13",
        }
        bbox = (625000.00, 6532000.00, 645000.00, 6545000.00)
        file_content = str(bbox)
        m_get_data = MagicMock(name="get_data_str", return_value=file_content)
        m_exists = MagicMock(name="exists", return_value=True)
        m_bbox_to_gettile = MagicMock(name="bbox_to_gettile")

        with patch("sys.stdout", self.m_stdout), \
                patch(f"{self.mod}.TileMatrixSet", self.m_tms_c), \
                patch(f"{self.mod}.exists", m_exists), \
                patch(f"{self.mod}.get_data_str", m_get_data), \
                patch(f"{self.mod}.bbox_to_gettile", m_bbox_to_gettile), \
                self.assertRaises(tms2stuff.GeometryError) as cm:
            tms2stuff.main(args)

        stdout_content = self.m_stdout.getvalue()
        self.m_tms_c.assert_called_once_with(args["tms_name"])
        self.m_tms_i.get_level.assert_called_once_with(args["level"])
        m_exists.assert_called_once_with(file_path)
        m_get_data.assert_called_once_with(file_path)
        m_bbox_to_gettile.assert_not_called()
        self.assertEqual(stdout_content, "", "unexpected console output")
        self.assertRegex(str(cm.exception), "^Input geometry error in file.*",
            "unexpected error message")

    def test_wkt_multi_to_gettile_pm_ok(self):
        """Test conversion from a WKT multiple geometry file to
            WMTS GetTile query parameters in the PM TMS.

        Characteristics:
            TMS: PM
            Input: path to a existing file or object describing
                a WKT multiple geometry
            Output: WMTS GetTile query parameters
        """
        bbox_list = [
            (-19059114.37, 19643704.77, -19057891.38, 19647373.75),
            (-19060337.37, 19646150.75, -19059114.38, 19647373.75),
            (-19060337.37, 19644927.76, -19059114.38, 19646150.74),
            (-19060337.37, 19643704.77, -19059114.38, 19644927.75),
            (-19835714.58, 19736652.19, -19834491.59, 19737875.19),
            (-19827153.64, 19731760.22, -19825930.64, 19732983.22),
        ]
        file_path = "file:///tmp/geom.wkt"
        args = {
            "tms_name": "PM",
            "input": f"GEOM_FILE:{file_path}",
            "output": "GETTILE_PARAMS",
            "level": "15",
        }
        calls_list = []
        polygon_list = []
        for i in range(len(bbox_list)):
            bbox = bbox_list[i]
            polygon = (
                f"(({bbox[0]} {bbox[1]},"
                + f"{bbox[2]} {bbox[1]},"
                + f"{bbox[2]} {bbox[3]},"
                + f"{bbox[0]} {bbox[3]},"
                + f"{bbox[0]} {bbox[1]})"
            )
            if i == 0:
                hole_bbox = (
                    bbox[0] + 10.0,
                    bbox[1] + 10.0,
                    bbox[2] - 10.0,
                    bbox[3] - 10.0
                )
                polygon = (
                    polygon
                    + f",({hole_bbox[0]} {hole_bbox[1]},"
                    + f"{hole_bbox[2]} {hole_bbox[1]},"
                    + f"{hole_bbox[2]} {hole_bbox[3]},"
                    + f"{hole_bbox[0]} {hole_bbox[3]},"
                    + f"{hole_bbox[0]} {hole_bbox[1]}))"
                )
            else:
                polygon = polygon + ")"
            polygon_list.append(polygon)
            calls_list.append(call(self.m_tm, bbox))
        file_content = "MULTIPOLYGON(" + ",".join(polygon_list) + ")"
        m_get_data = MagicMock(name="get_data_str", return_value=file_content)
        m_exists = MagicMock(name="exists", return_value=True)
        tile_range_list = [
            (800, 319, 801, 322),
            (799, 319, 800, 320),
            (799, 320, 800, 321),
            (799, 321, 800, 322),
            (165, 245, 166, 246),
            (172, 249, 173, 250)
        ]
        query_group_list = []
        query_output_list = []
        query_base = "TILEMATRIX=" + args["level"]
        for tile_range in tile_range_list:
            query_list = []
            for column in range(tile_range[0], tile_range[2] + 1):
                for row in range(tile_range[1], tile_range[3] + 1):
                    query = (f"{query_base}&TILECOL={column}&TILEROW={row}")
                    query_list.append(query)
                    if query not in query_output_list:
                        query_output_list.append(query)
            query_group_list.append(query_list)
        query_output_list.sort()
        m_bbox_to_gettile = MagicMock(name="bbox_to_gettile",
            side_effect=query_group_list)
        expected_output = "\n".join(query_output_list) + "\n"

        with patch("sys.stdout", self.m_stdout), \
                patch(f"{self.mod}.TileMatrixSet", self.m_tms_c), \
                patch(f"{self.mod}.exists", m_exists), \
                patch(f"{self.mod}.get_data_str", m_get_data), \
                patch(f"{self.mod}.bbox_to_gettile", m_bbox_to_gettile):
            tms2stuff.main(args)

        stdout_content = self.m_stdout.getvalue()
        query_group_string = ""
        for query_group in query_group_list:
            query_group_string = query_group_string + "\n".join(query_group) + "\n\n"
        self.m_tms_c.assert_called_once_with(args["tms_name"])
        self.m_tms_i.get_level.assert_called_once_with(args["level"])
        m_exists.assert_called_once_with(file_path)
        m_get_data.assert_called_once_with(file_path)
        self.assertEqual(m_bbox_to_gettile.call_count, len(calls_list),
            "Unexpected number of calls to bbox_to_gettile.")
        for i in range(len(calls_list)):
            self.assertEqual(
                m_bbox_to_gettile.call_args_list[i].args[0:2],
                calls_list[i].args[0:2],
                f"Unexpected arguments for call {str(i)} to bbox_to_gettile."
            )
        self.assertEqual(stdout_content, expected_output,
            "unexpected console output")

    def test_wkt_file_to_slabs_l93_ok(self):
        """Test conversion from a WKT geometry file to slab indices
        in the LAMB93_5cm TMS.

        Characteristics:
            TMS: LAMB93_5cm
            Input: path to a existing file or object describing
                a WKT geometry
            Output: slab indices
        """
        file_path = "file:///tmp/geom.wkt"
        slab_size = (16, 10)
        args = {
            "tms_name": "LAMB93_5cm",
            "input": f"GEOM_FILE:{file_path}",
            "output": "SLAB_INDICES",
            "level": "13",
            "slabsize": f"{slab_size[0]}x{slab_size[1]}",
        }
        bbox = (625000.89, 6532000.12, 680000.65, 6650000.25)
        file_content = ("POLYGON(("
            + f"{bbox[0]} {bbox[1]},"
            + f"{bbox[2]} {bbox[1]},"
            + f"{bbox[2]} {bbox[3]},"
            + f"{bbox[0]} {bbox[3]},"
            + f"{bbox[0]} {bbox[1]}"
            + "))")
        m_get_data = MagicMock(name="get_data_str", return_value=file_content)
        m_exists = MagicMock(name="exists", return_value=True)
        slabs_list = [
            (5, 81),
            (5, 82),
            (5, 83),
            (6, 81),
            (6, 82),
            (6, 83),
        ]
        m_bbox_to_slab_list = MagicMock(name="bbox_to_slab_list",
            return_value=slabs_list)
        expected_output = ""
        for slab in slabs_list:
            expected_output = expected_output + f"{slab[0]},{slab[1]}\n"

        with patch("sys.stdout", self.m_stdout), \
                patch(f"{self.mod}.TileMatrixSet", self.m_tms_c), \
                patch(f"{self.mod}.exists", m_exists), \
                patch(f"{self.mod}.get_data_str", m_get_data), \
                patch(f"{self.mod}.bbox_to_slab_list", m_bbox_to_slab_list):
            tms2stuff.main(args)

        stdout_content = self.m_stdout.getvalue()
        self.m_tms_c.assert_called_once_with(args["tms_name"])
        self.m_tms_i.get_level.assert_called_once_with(args["level"])
        m_exists.assert_called_once_with(file_path)
        m_get_data.assert_called_once_with(file_path)
        m_bbox_to_slab_list.assert_called_once()
        self.assertEqual(m_bbox_to_slab_list.call_args.args[0:3],
            (self.m_tm, bbox, slab_size))
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
                patch(f"{self.mod}.TileMatrixSet", self.m_tms_c):
            tms2stuff.main(args)

        stdout_content = self.m_stdout.getvalue()
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

