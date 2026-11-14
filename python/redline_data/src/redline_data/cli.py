"""T0 entry point: do not report unimplemented data operations as success."""
import argparse
from collections.abc import Sequence

from redline_data import __version__


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="redline-data",
        description="T0 package foundation. Archive processing commands arrive in T1.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.parse_args(argv)
    parser.print_help()
    return 0
