"""Convert data to another format using a tile matrix set.

Exit codes:
    0 - regular exit
    1 - regular error code, details logged in stderr
    2 - argument syntax or data value error, details logged in stderr

Print up to date usage message with the following command:
    tms2stuff.py --help
See the project's README and github documentation for more information.
"""
import argparse
import json
import math
import os
from os import path
import re
import sys
from typing import Dict, List, Tuple

from osgeo import ogr

from rok4.TileMatrixSet import TileMatrixSet, TileMatrix
from rok4.Storage import exists, get_data_str
from rok4_tools import __version__

# Enable GDAL/OGR exceptions
ogr.UseExceptions()

# CLI arguments parsing

def parse_cli_args() -> Dict:
    """Parse raw arguments from CLI call.

    Raises:
        SystemExit: two possible cases with different error codes:
            - code == 0: after display of help or version
            - code == 2: after detection of a syntax error in arguments

    Returns:
        Dict: a dictionary of parsed arguments
    """
    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        description="Coordinates conversion tool using Tile Matrix Sets (TMS)"
    )
    parser.add_argument("--version", action="version", version=__version__,
        help="show the executable's version and exit")
    parser.add_argument("tms_name", help="TMS name",)
    parser.add_argument("input", help="input data to convert")
    parser.add_argument("output", help="output format")
    parser.add_argument("--level", help="TMS level, or TM id", dest="level")
    parser.add_argument("--slabsize",
        help="slab '<width>x<height>', expressed in number of tiles")
    args = parser.parse_args()
    args_dict = {
        "tms_name": args.tms_name,
        "input": args.input,
        "output": args.output,
        "level": args.level,
        "slabsize": args.slabsize,
    }
    return args_dict

# Post-parsing arguments transformation functions

def read_bbox(bbox_str: str, error_message: str = None
        ) -> Tuple[float, float, float, float]:
    """Convert a bounding box (BBOX) string to a tuple.

    Args:
        bbox_str (str): BBOX as a string "min_x,min_y,max_x,max_y"
        error_message (str, optional): custom error message

    Raises:
        ValueError: bbox_str isn't a well-formed BBOX string

    Returns:
        Tuple[float, float, float, float]: BBOX as a tuple
            float: abscissa minimum
            float: ordinate minimum
            float: abscissa maximum
            float: ordinate maximum
    """
    if error_message is None:
        error_message = (f"Invalid BBOX: {bbox_str}\nExpected BBOX format is "
            + "<min_axis_1>,<min_axis_2>,<max_axis_1>,<max_axis_2>")
    coord_pattern = "-?[0-9]+(?:[.][0-9]+)?"
    bbox_pattern = (f"^({coord_pattern}),({coord_pattern}),"
                + f"({coord_pattern}),({coord_pattern})$")
    bbox_match = re.search(bbox_pattern, bbox_str)

    if bbox_match is None:
        raise ValueError(error_message)

    bbox = (
        float(bbox_match.group(1)),
        float(bbox_match.group(2)),
        float(bbox_match.group(3)),
        float(bbox_match.group(4)),
    )
    return bbox

# Data processing functions

def bbox_to_gettile(tm: "TileMatrix", bbox: Tuple[float, float, float, float],
        container: ogr.Geometry = None) -> List[str]:
    """Convert a bounding box (BBOX) to excerpts of GetTile queries.

    Args:
        tm (TileMatrix): target GetTile
        bbox (Tuple[float, float, float, float]): BBOX as a tuple
            (min_x, min_y, max_x, max_y)
        container (ogr.Geometry): geometry that tiles have to intersect

    Returns:
        List[str]: List of WMTS GetTile query string excerpts
            str: "TILEMATRIX=<level>&TILECOL=<col>&TILEROW=<row>"
    """
    # tile_range = (min_col, min_row, max_col, max_row)
    tile_range = tm.bbox_to_tiles(bbox)
    query_list = []
    for column in range(tile_range[0], tile_range[2] + 1):
        for row in range(tile_range[1], tile_range[3] + 1):
            add_query = True
            if container is not None:
                tile_bbox = tm.tile_to_bbox(column, row)
                tile_geom = ogr.Geometry(ogr.wkbPolygon)
                ring = ogr.Geometry(ogr.wkbLinearRing)
                ring.AddPoint(tile_bbox[0], tile_bbox[1])
                ring.AddPoint(tile_bbox[2], tile_bbox[1])
                ring.AddPoint(tile_bbox[2], tile_bbox[3])
                ring.AddPoint(tile_bbox[0], tile_bbox[3])
                ring.AddPoint(tile_bbox[0], tile_bbox[1])
                tile_geom.AddGeometry(ring)
                add_query = container.Intersects(tile_geom)
            if add_query:
                query_list.append(f"TILEMATRIX={tm.id}&TILECOL={column}"
                    + f"&TILEROW={row}")
    return query_list

def bbox_to_slab_list(tm: "TileMatrix",
        bbox: Tuple[float, float, float, float],
        slab_size: Tuple[int, int],
        container: ogr.Geometry = None) -> List[str]:
    """Convert a bounding box (BBOX) to excerpts of GetTile queries.

    Args:
        tm (TileMatrix): target GetTile
        bbox (Tuple[float, float, float, float]): BBOX as a tuple
            (min_x, min_y, max_x, max_y)
        slab_size (Tuple[int, int]): slab's number of tiles in width and
            height respectively
        container (ogr.Geometry): geometry that slabs have to intersect

    Returns:
        List[Tuple[int, int]]: List of slab (column, row) tuples
    """
    # tile_range = (min_col, min_row, max_col, max_row)
    tile_range = tm.bbox_to_tiles(bbox)
    # slab_range = (min_col, min_row, max_col, max_row)
    slab_range = (
        math.floor(tile_range[0] / slab_size[0]),
        math.floor(tile_range[1] / slab_size[1]),
        math.floor(tile_range[2] / slab_size[0]),
        math.floor(tile_range[3] / slab_size[1])
    )
    slab_list = []
    for column in range(slab_range[0], slab_range[2] + 1, 1):
        for row in range(slab_range[1], slab_range[3] + 1, 1):
            add_slab = True
            if container is not None:
                tile_col_range = range(column * slab_size[0],
                    (column + 1) * slab_size[0])
                tile_row_range = range(row * slab_size[1],
                    (row + 1) * slab_size[1])
                slab_bbox = []
                for tile_col in tile_col_range:
                    for tile_row in tile_row_range:
                        tile_bbox = tm.tile_to_bbox(column, row)
                        if len(slab_bbox) == 0:
                            slab_bbox = list(tile_bbox)
                        else:
                            if slab_bbox[0] < tile_bbox[0]:
                                slab_bbox[0] = tile_bbox[0]
                            if slab_bbox[1] < tile_bbox[1]:
                                slab_bbox[1] = tile_bbox[1]
                            if slab_bbox[2] > tile_bbox[2]:
                                slab_bbox[2] = tile_bbox[2]
                            if slab_bbox[3] > tile_bbox[3]:
                                slab_bbox[3] = tile_bbox[3]
                slab_geom = ogr.Geometry(ogr.wkbPolygon)
                ring = ogr.Geometry(ogr.wkbLinearRing)
                ring.AddPoint(slab_bbox[0], slab_bbox[1])
                ring.AddPoint(slab_bbox[2], slab_bbox[1])
                ring.AddPoint(slab_bbox[2], slab_bbox[3])
                ring.AddPoint(slab_bbox[0], slab_bbox[3])
                ring.AddPoint(slab_bbox[0], slab_bbox[1])
                slab_geom.AddGeometry(ring)
                add_slab = container.Intersects(slab_geom)
            if add_slab:
                slab_list.append((column, row))
    return slab_list

# Custom exceptions

class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class GeometryError(Error):
    """Raised when a geometry could not be processed.

    Such a case may happen for example when a '.wkt' file contains
    something else than a WKT geometry string,
    or when a geometry is invalid.
    """
    pass

# Main function

def main(args: Dict) -> None:
    """Execute the conversion matching the specified input and output.

    Args:
        args (Dict): arguments dictionary returned by parse_cli_args()

    Raises:
        FileNotFoundError: a specified file was not found
        GeometryError: geometry couldn't be processed
        RuntimeError: no conversion matching requested input and output
        ValueError: incorrect syntax for an argument value
    """
    implemented = {
        "BBOX": [
            "GETTILE_PARAMS",
            "SLAB_INDICES",
        ],
        "BBOXES_LIST": [
            "SLAB_INDICES",
        ],
        "GEOM_FILE": [
            "GETTILE_PARAMS",
            "SLAB_INDICES",
        ],
        "TILE_INDICE": [
            "GETMAP_PARAMS",
        ],
    }

    slab_size = None
    if "slabsize" in args and args["slabsize"]:
        slab_size_match = re.search("^([0-9]+)x([0-9]+)$", args["slabsize"])
        if slab_size_match:
            slab_size = (
                int(slab_size_match.group(1)),
                int(slab_size_match.group(2))
            )
        else:
            error_message = (f"{sys.argv[0]}: error: argument --slabsize: "
                + f"invalid value: {args['slabsize']}\n"
                + "Value format must be '<int>x<int>' (Example: '16x12')")
            raise ValueError(error_message)

    try:
        tms = TileMatrixSet(args["tms_name"])
        format_pattern = "^([A-Z_]+)(?::(.*))?$"
        input_parts = re.search(format_pattern, args["input"]).groups()
        output_parts = re.search(format_pattern, args["output"]).groups()
    except:
        positional = " ".join([
            args["tms_name"],
            args["input"],
            args["output"]
        ])
        raise ValueError("Unrecognised positional arguments : " + positional)
    tm = None
    if "level" in args and args["level"]:
        tm = tms.get_level(args["level"])

    if (not input_parts[0] in implemented
                or not output_parts[0] in implemented[input_parts[0]]):
        raise RuntimeError("No implemented conversion from "
            + f"'{input_parts[0]}' to '{output_parts[0]}'.")

    if input_parts[0] == "BBOX":
        input_error_message = (
            f"Invalid input: expected BBOX format is "
            + "BBOX:<min_axis_1>,<min_axis_2>,<max_axis_1>,<max_axis_2>"
        )
        if input_parts[1] is None:
            raise ValueError(input_error_message)
        bbox = read_bbox(input_parts[1], input_error_message)

        if output_parts[0] == "GETTILE_PARAMS":
            # input = BBOX, output = WMTS GetTile query parameters
            gettile_list = bbox_to_gettile(tm, bbox)
            print("\n".join(gettile_list), end="\n")

        elif output_parts[0] == "SLAB_INDICES":
            # input = BBOX, output = slab indices
            if slab_size is None:
                raise ValueError(f"For output type {output_parts[0]}, "
                    + "the parameter '--slabsize' is mandatory.")
            slab_list = bbox_to_slab_list(tm, bbox, slab_size)
            for slab in slab_list:
                print(f"{slab[0]},{slab[1]}", end="\n")

    elif input_parts[0] == "BBOXES_LIST" and output_parts[0] == "SLAB_INDICES":
        # input = BBOX list file or object, output = slab indices
        if input_parts[1] is None:
            raise ValueError("Syntax for BBOX list input is: "
            + "'BBOXES_LIST:<path_to_list>'")
        if slab_size is None:
            raise ValueError(f"For output type {output_parts[0]}, "
                + "the parameter '--slabsize' is mandatory.")
        if not exists(input_parts[1]):
            raise FileNotFoundError(
                f"File or object not found: {input_parts[1]}")
        list_data = get_data_str(input_parts[1])
        bbox_list = list_data.splitlines()
        slabs_list = []
        for bbox_string in bbox_list:
            bbox = read_bbox(bbox_string)
            temp_slabs_list = bbox_to_slab_list(tm, bbox, slab_size)
            for slab in temp_slabs_list:
                if slab not in slabs_list:
                    slabs_list.append(slab)
        slabs_list.sort()
        for slab in slabs_list:
            print(slab[0], slab[1], sep=',')

    elif input_parts[0] == "GEOM_FILE":
        if input_parts[1] is None:
            raise ValueError("Syntax for geometry file input is: "
                + "'GEOM_FILE:<path_to_file>'")
        if not exists(input_parts[1]):
            raise FileNotFoundError(
                f"File or object not found: {input_parts[1]}")
        geometry_str = get_data_str(input_parts[1])
        try:
            geometry_full = ogr.CreateGeometryFromGML(geometry_str)
        except (RuntimeError, TypeError):
            try:
                geometry_full = ogr.CreateGeometryFromJson(geometry_str)
            except (RuntimeError, TypeError):
                try:
                    geometry_full = ogr.CreateGeometryFromWkb(geometry_str)
                except (RuntimeError, TypeError):
                    try:
                        geometry_full = ogr.CreateGeometryFromWkt(geometry_str)
                    except (RuntimeError, TypeError):
                        raise GeometryError(
                            "Input geometry error in file '"
                            + input_parts[1]
                            + "': unhandled format or invalid data. "
                            + "Handled formats are: "
                            + "GML, GeoJSON, WKB, WKT."
                        )
        if not geometry_full.IsValid():
            raise GeometryError("Invalid input geometry. WKT description: '"
                + geometry_full.ExportToWkt() + "'")
        bbox_list = []
        for part_index in range(geometry_full.GetGeometryCount()):
            geometry_part = geometry_full.GetGeometryRef(part_index)
            (min_x, max_x, min_y, max_y) = geometry_part.GetEnvelope()
            bbox_list.append((min_x, min_y, max_x, max_y))
        final_list = []
        if output_parts[0] == "GETTILE_PARAMS":
            # input = GEOM_FILE, output = WMTS GetTile query parameters
            for bbox in bbox_list:
                gettile_list = bbox_to_gettile(tm, bbox, geometry_full)
                for gettile in gettile_list:
                    if gettile not in final_list:
                        final_list.append(gettile)
        elif output_parts[0] == "SLAB_INDICES":
            # input = GEOM_FILE, output = slab indices
            if slab_size is None:
                raise ValueError(f"For output type {output_parts[0]}, "
                    + "the parameter '--slabsize' is mandatory.")
            for bbox in bbox_list:
                slab_list = bbox_to_slab_list(tm, bbox, slab_size,
                    geometry_full)
                for slab in slab_list:
                    slab_string = f"{slab[0]},{slab[1]}"
                    if slab_string not in final_list:
                        final_list.append(slab_string)
        final_list.sort()
        print("\n".join(final_list), end="\n")

    elif input_parts[0] == "TILE_INDICE":
        input_error_message = ("Syntax for tile indices input is: "
            + "'TILE_INDICE:<column>,<row>'")
        if input_parts[1] is None:
            raise ValueError(input_error_message)
        indices_pattern = "^([0-9]+),([0-9]+)$"
        indices_match = re.search(indices_pattern, input_parts[1])
        if indices_match is None:
            raise ValueError(input_error_message)
        tile_col = int(indices_match.group(1))
        tile_row = int(indices_match.group(2))

        if output_parts[0] == "GETMAP_PARAMS":
            # input = tile indices, output = WMS GetMap query parameters
            bbox = tm.tile_to_bbox(tile_col=tile_col, tile_row=tile_row)
            query_string = (f"WIDTH={tm.tile_size[0]}"
                + f"&HEIGHT={tm.tile_size[1]}"
                + f"&BBOX={bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
                + f"&CRS={tms.srs}")
            print(query_string)

# If called as a script (nominal use case)

if __name__ == "__main__":
    exit_code = 0
    try:
        main(parse_cli_args())
    except SystemExit as sys_exit:
        exit_code = sys_exit.code
    except ValueError as err:
        print(f"ValueError: {str(err)}", file=sys.stderr)
        exit_code = 2
    except (Exception) as err:
        print(f"Error: {str(err)}", file=sys.stderr)
        exit_code = 1
    sys.exit(exit_code)
