import argparse
import tempfile
import time
import geotopy as gtp

parser = argparse.ArgumentParser(prog="GEOtoPy",
                                 description="Simple GEOtop launcher.")
parser.add_argument("inputs_dir")
args = parser.parse_args()

tic = time.perf_counter()
with tempfile.TemporaryDirectory() as tmpdir:
    try:
        model = gtp.GEOtop(args.inputs_dir)
        print(f"Running GEOtop...")
        model.eval(working_dir=tmpdir)
    except Exception:
        raise

toc = time.perf_counter()
print(f"Wall time: {toc - tic:.2f} seconds.")
