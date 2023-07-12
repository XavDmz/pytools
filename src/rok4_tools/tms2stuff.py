import argparse
import json
import math
import os
from os import path
import re
import sys
from typing import Dict, List, Tuple

from rok4 import TileMatrixSet
from rok4 import Storage
from rok4_tools import __version__

def main(args: Dict):
    slab_size = None
    if "slabsize" in args and args["slabsize"]:
        slab_size_match = re.match("^([0-9]+)x([0-9]+)$", args["slabsize"])
        if slab_size_match:
            slab_size = (
                int(slab_size_match.group(1)),
                int(slab_size_match.group(2))
            )
        else:
            error_message = (f"{sys.argv[0]}: error: argument --slabsize: "
                + f"invalid value: {args['slabsize']}\n"
                + "Value format must be '<int>x<int>' (Example: '16x12')")
            cli_syntax_error(error_message)

    tms = TileMatrixSet.TileMatrixSet(args["tms_name"])
    input_parts = re.match("^([A-Z_]+)(?::(.*))?$", args["input"]).groups()
    output_parts = re.match("^([A-Z_]+)(?::(.*))?$", args["output"]).groups()
    tm = None
    if "level" in args and args["level"]:
        tm = tms.get_level(args["level"])

    if input_parts[0] == "BBOX":
        input_error_message = (
            f"Invalid input: expected BBOX format is "
            + "BBOX:<min_axis_1>,<min_axis_2>,<max_axis_1>,<max_axis_2>"
        )
        if input_parts[1] is None:
            cli_syntax_error(input_error_message)
        bbox = read_bbox(input_parts[1], input_error_message)

        if output_parts[0] == "GETTILE_PARAMS":
            # input = BBOX, output = WMTS GetTile query parameters
            (col_min, row_min, col_max, row_max) = tm.bbox_to_tiles(bbox)

            for tile_row in range(row_min, row_max + 1, 1):
                for tile_col in range(col_min, col_max + 1, 1):
                    print(
                        f"TILEMATRIX={args['level']}&TILECOL={tile_col}"
                        + f"&TILEROW={tile_row}"
                    )

        elif output_parts[0] == "SLAB_INDICES":
            # input = BBOX, output = slab indices
            if slab_size is None:
                cli_syntax_error(f"For output type {output_parts[0]}, "
                    + "the parameter '--slabsize' is mandatory.")
            # tile_box = (min_col, min_row, max_col, max_row)
            tile_box = tm.bbox_to_tiles(bbox)
            # slab_box = (min_col, min_row, max_col, max_row)
            slab_box = (
                math.floor(tile_box[0] / slab_size[0]),
                math.floor(tile_box[1] / slab_size[1]),
                math.floor(tile_box[2] / slab_size[0]),
                math.floor(tile_box[3] / slab_size[1])
            )
            for slab_col in range(slab_box[0], slab_box[2] + 1, 1):
                for slab_row in range(slab_box[1], slab_box[3] + 1, 1):
                    print(slab_col, slab_row, sep=',')
        else:
            unknown_conversion(input_parts[0], output_parts[0])

    elif input_parts[0] == "BBOXES_LIST" and output_parts[0] == "SLAB_INDICES":
        # input = BBOX list file or object, output = slab indices
        if input_parts[1] is None:
            cli_syntax_error(input_format_error_messsage)
        if slab_size is None:
            cli_syntax_error(f"For output type {output_parts[0]}, "
                + "the parameter '--slabsize' is mandatory.")
        if not Storage.exists(input_parts[1]):
            print(f"File or object not found: {input_parts[1]}",
                file=sys.stderr)
            sys.exit(1)
        list_data = Storage.get_data_str(input_parts[1])
        bbox_list = list_data.splitlines()
        slabs_list = []
        for bbox_string in bbox_list:
            bbox = read_bbox(bbox_string)
            bbox_tiles = tm.bbox_to_tiles(bbox)
            for tile_col in range(bbox_tiles[0], bbox_tiles[2] + 1, 1):
                for tile_row in range(bbox_tiles[1], bbox_tiles[3] + 1, 1):
                    slab = (math.floor(tile_col / slab_size[0]),
                        math.floor(tile_row / slab_size[1]))
                    if slab not in slabs_list:
                        slabs_list.append(slab)
        slabs_list.sort()
        for slab in slabs_list:
            print(slab[0], slab[1], sep=',')
            


    elif input_parts[0] == "TILE_INDICE" and output_parts[0] == "GETMAP_PARAMS":
        # input = tile indices, output = WMS GetMap query parameters
        if input_parts[1] is None:
            cli_syntax_error(input_format_error_messsage)
        indices_pattern = "^([0-9]+),([0-9]+)$"
        indices_match = re.match(indices_pattern, input_parts[1])
        tile_col = int(indices_match.group(1))
        tile_row = int(indices_match.group(2))
        bbox = tm.tile_to_bbox(tile_col=tile_col, tile_row=tile_row)
        query_string = (f"WIDTH={tm.tile_size[0]}"
            + f"&HEIGHT={tm.tile_size[1]}"
            + f"&BBOX={bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
            + f"&CRS={tms.srs}")
        print(query_string)

    else:
        unknown_conversion(input_parts[0], output_parts[0])     

    sys.exit(0)

def cli_syntax_error(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(2)

def read_bbox(bbox_str: str,
        error_message: str = None) -> Tuple[float, float, float, float]:
    if error_message is None:
        error_message = (f"Invalid BBOX: {bbox_str}\nExpected BBOX format is "
            + "<min_axis_1>,<min_axis_2>,<max_axis_1>,<max_axis_2>")
    coord_pattern = "-?[0-9]+(?:[.][0-9]+)?"
    bbox_pattern = (f"^({coord_pattern}),({coord_pattern}),"
                + f"({coord_pattern}),({coord_pattern})$")
    bbox_match = re.match(bbox_pattern, bbox_str)

    if bbox_match is None:
        cli_syntax_error(error_message)
    else:
        bbox = (
            float(bbox_match.group(1)),
            float(bbox_match.group(2)),
            float(bbox_match.group(3)),
            float(bbox_match.group(4)),
        )
        return bbox
    return

def unknown_conversion(input_type: str, output_type: str) -> None:
    print("No implemented conversion from",
        f"'{input_type}' to '{output_type}'.",
        sep=" ",
        file=sys.stderr)
    sys.exit(1)

def parse_cli_args() -> Dict:
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

if __name__ == "__main__":
    main(parse_cli_args())
