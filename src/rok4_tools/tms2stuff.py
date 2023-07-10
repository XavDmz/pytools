import argparse
import json
import math
import os
from os import path
import re
import sys

from rok4 import TileMatrixSet
from rok4_tools import __version__

def main():

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
        help="slab dimensions, expressed in number of tiles")
    args = parser.parse_args()
    slab_size = None
    if args.slabsize:
        slab_size_match = re.match("^([0-9]+)x([0-9]+)$", args.slabsize)
        if slab_size_match:
            slab_size = (
                int(slab_size_match.group(1)),
                int(slab_size_match.group(2))
            )
        else:
            error_message = (f"{sys.argv[0]}: error: argument --slabsize: "
                + f"invalid value: '{args.slabsize}'\n"
                + "Value format must be '<int>x<int>' (Example: '16x12')")
            print(error_message, file=sys.stderr)
            sys.exit(2)

    tms = TileMatrixSet.TileMatrixSet(args.tms_name)

    if re.match("^BBOX:", args.input) and args.output == "GETTILE_PARAMS":
        # input = BBOX, output = WMTS GetTile query parameters
        tm = tms.get_level(args.level)
        coord_pattern = "-?[0-9]+([.][0-9]+)?"
        bbox_pattern = (f"^BBOX:({coord_pattern}),({coord_pattern}),"
                    + f"({coord_pattern}),({coord_pattern})$")
        bbox_match = re.match(bbox_pattern, args.input)
        bbox = (
            float(bbox_match.group(1)),
            float(bbox_match.group(3)),
            float(bbox_match.group(5)),
            float(bbox_match.group(7)),
        )
        (col_min, row_min, col_max, row_max) = tm.bbox_to_tiles(bbox)

        for tile_row in range(row_min, row_max + 1, 1):
            for tile_col in range(col_min, col_max + 1, 1):
                print(
                    f"TILEMATRIX={args.level}&TILECOL={tile_col}"
                    + f"&TILEROW={tile_row}"
                )

    elif re.match("^TILE_INDICE:", args.input) and args.output == "GETMAP_PARAMS":
        # input = tile indices, output = WMS GetMap query parameters
        tm = tms.get_level(args.level)
        indices_pattern = "^TILE_INDICE:([0-9]+),([0-9]+)$"
        indices_match = re.match(indices_pattern, args.input)
        tile_col = int(indices_match.group(1))
        tile_row = int(indices_match.group(2))
        bbox = tm.tile_to_bbox(tile_col=tile_col, tile_row=tile_row)
        query_string = (f"WIDTH={tm.tile_size[0]}"
            + f"&HEIGHT={tm.tile_size[1]}"
            + f"&BBOX={bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
            + f"&CRS={tms.srs}")
        print(query_string)

    elif re.match("^BBOX:", args.input) and args.output == "SLAB_INDICES":
        # input = BBOX, output = slab indices
        tm = tms.get_level(args.level)
        coord_pattern = "-?[0-9]+([.][0-9]+)?"
        bbox_pattern = (f"^BBOX:({coord_pattern}),({coord_pattern}),"
                    + f"({coord_pattern}),({coord_pattern})$")
        bbox_match = re.match(bbox_pattern, args.input)
        bbox = (
            float(bbox_match.group(1)),
            float(bbox_match.group(3)),
            float(bbox_match.group(5)),
            float(bbox_match.group(7)),
        )
        # format (tile_box, slab_box): (min_col, min_row, max_col, max_row)
        tile_box = tm.bbox_to_tiles(bbox)
        slab_box = (
            math.floor(tile_box[0] / slab_size[0]),
            math.floor(tile_box[1] / slab_size[1]),
            math.floor(tile_box[2] / slab_size[0]),
            math.floor(tile_box[3] / slab_size[1])
        )
        for slab_col in range(slab_box[0], slab_box[2] + 1, 1):
            for slab_row in range(slab_box[1], slab_box[3] + 1, 1):
                print(f"{slab_col},{slab_row}")

    else:
        error_message = ("No implemented conversion from "
            + f"'{args.input}' to '{args.output}'.")
        print(error_message, file=sys.stderr)
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
