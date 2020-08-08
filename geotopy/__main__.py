import argparse
import tempfile
import geotopy as gtp

parser = argparse.ArgumentParser(prog="GEOtoPy",
                                 description="Simple GEOtop launcher.")
parser.add_argument("inputs_dir")
args = parser.parse_args()

with tempfile.TemporaryDirectory() as tmpdir:
    try:
        model = gtp.GEOtop(args.inputs_dir, working_dir=tmpdir)
        print(f"Running GEOtop...")
        model.run(check=True)
    except Exception:
        raise
