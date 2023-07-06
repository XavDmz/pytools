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
    args = parser.parse_args()

    tms = TileMatrixSet.TileMatrixSet(args.tms_name)

    if re.match("^BBOX:", args.input) and args.output == "GETTILE_PARAMS":
        # input = BBOX, output = GetTile query parameters
        tm = tms.get_level(args.level)

        coord_pattern = "-?[0-9]+([.][0-9]+)?"
        bbox_pattern = (f"^BBOX:({coord_pattern}),({coord_pattern}),"
                    + f"({coord_pattern}),({coord_pattern})$")
        bbox_match = re.match(bbox_pattern,args.input)
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

    sys.exit(0)

if __name__ == "__main__":
    main()
