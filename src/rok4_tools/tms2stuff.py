import argparse
from importlib.metadata import version
import sys

__version__ = version("rok4-tools")

def main():

    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        description="Coordinates conversion tool using Tile Matrix Sets (TMS)"
    )
    parser.add_argument("--version", action="version", version=__version__,
                        help="Prints the version then exits")
    parser.add_argument("--tms", required=True, help="Path to a TMS file.",
                        dest="tms_path")
    parser.add_argument("--from", required=True, help="Input to convert.",
                        dest="input")
    parser.add_argument("--to", required=True, help="Output format.",
                        dest="output")
    parser.add_argument("--level", required=False, help="TMS level, or TM id.",
                        dest="level")
    args = parser.parse_args()

    sys.exit(0)

if __name__ == "__main__": 
    main()