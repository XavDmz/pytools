import argparse
import json
import math
import os
from os import path
import re
import sys

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

    tms_path = path.join(os.environ["ROK4_TMS_DIRECTORY"],
        f"{args.tms_name}.json")
    tms_content = None

    with open(tms_path, "r") as file_handle:
        tms_content = json.load(file_handle) # Is there a memory risk ?

    commons = {
        "TMS": {
            "axis": tms_content["orderedAxes"],
            "crs": tms_content["crs"],
            "id": tms_content["id"],
            "TM": {},
        }
    }

    for tm in tms_content["tileMatrices"]:
        commons["TMS"]["TM"][tm["id"]] = {
            "cell_size": tm["cellSize"],
            "matrix_height": tm["matrixHeight"],
            "matrix_width": tm["matrixWidth"],
            "origin": tm["pointOfOrigin"],
            "scale_denominator": tm["scaleDenominator"],
            "tile_height": tm["tileHeight"],
            "tile_width": tm["tileWidth"],
        }

    if re.match("^BBOX:", args.input) and args.output == "GETTILE_PARAMS":
        # input = BBOX, output = GetTile query parameters
        # TODO: implement true response to this request

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

        cell_size = commons["TMS"]["TM"][args.level]["cell_size"]
        origin = commons["TMS"]["TM"][args.level]["origin"]
        tile_height = commons["TMS"]["TM"][args.level]["tile_height"]
        tile_width = commons["TMS"]["TM"][args.level]["tile_width"]

        col_min = math.floor((bbox[0]-origin[0])/(cell_size*tile_width))
        col_max = math.floor((bbox[2]-origin[0])/(cell_size*tile_width))
        row_min = math.floor((origin[1]-bbox[3])/(cell_size*tile_height))
        row_max = math.floor((origin[1]-bbox[1])/(cell_size*tile_height))

        for tile_row in range(row_min, row_max + 1, 1):
            for tile_col in range(col_min, col_max + 1, 1):
                print(
                    f"TILEMATRIX={args.level}&TILECOL={tile_col}"
                    + f"&TILEROW={tile_row}"
                )

    sys.exit(0)

if __name__ == "__main__":
    main()
