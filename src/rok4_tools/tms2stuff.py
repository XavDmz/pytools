import argparse
from importlib.metadata import version
import json
import os
from os import path
import re
import sys

__version__ = version("rok4-tools")

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
    tms_content = {}

    with open(tms_path, "r"):
        tms_content = {}

    if re.match("^BBOX:", args.input) and args.output == "GETTILE_PARAMS":
        # input = BBOX, output = GetTile query parameters
        # TODO: implement true response to this request
        tile_col = 439
        tile_row = 1023

        print(f"TILEMATRIX={args.level}&TILECOL={tile_col}&TILEROW={tile_row}")

    sys.exit(0)

if __name__ == "__main__":
    main()
