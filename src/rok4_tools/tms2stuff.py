import argparse
from importlib.metadata import version
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
    parser.add_argument("tms_path", help="path to a TMS file.",)
    parser.add_argument("input", help="input data to convert")
    parser.add_argument("output", help="output format")
    parser.add_argument("--level", help="TMS level, or TM id", dest="level")
    args = parser.parse_args()

    if re.match("^BBOX:", args.input) and args.output == "GETTILE_PARAMS":
        # input = BBOX, output = GetTile query parameters
        print("TILEMATRIX=15&TILECOL=439&TILEROW=1023")
        # TODO: implement true response to this request


    sys.exit(0) # TODO : move to 'if __name__ == "__main__":' block

if __name__ == "__main__": 
    main()