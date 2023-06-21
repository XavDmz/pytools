import argparse
import importlib.metadata
import sys

__version__ = importlib.metadata.version("rok4-tools")

def main():

    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        description="Coordinates conversion tool using Tile Matrix Sets (TMS)"
    )
    parser.add_argument("--version", action="version", version=__version__,
                        help="Prints the version then exits")
    parser.add_argument("--tms", required=True, help="Path to a TMS file.",
                        dest="tms_path")
    args = parser.parse_args()

    sys.exit(0)

if __name__ == "__main__": 
    main()