import argparse
import geotopy.core as gtp
import os

parser = argparse.ArgumentParser(prog="GEOtoPy", description="Simple GEOtop launcher.")
parser.add_argument("working_directory")
args = parser.parse_args()

try:
    model = gtp.GEOtop(args.working_directory)
    model.run()
except:
    raise





