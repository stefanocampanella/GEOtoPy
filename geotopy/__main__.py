import argparse
import tempfile
import time
import geotopy as gtp
import subprocess
import shutil

parser = argparse.ArgumentParser(prog="GEOtoPy",
                                 description="Simple GEOtop launcher.")
parser.add_argument("inputs_dir")
args = parser.parse_args()


class GEOtopSimpleRun(gtp.GEOtop):

    def preprocess(self, working_dir):
        if shutil.which('tree'):
            print(f"==== Input files: ====")
            subprocess.run(['tree', '-D', self.inputs_dir])
            print()
        print("==== Running GEOtop... ====\n")

    def postprocess(self, working_dir):
        if shutil.which('tree'):
            print(f"==== Output files: ====")
            subprocess.run(['tree', '-D', working_dir])
            print()

        return None


tic = time.perf_counter()
with tempfile.TemporaryDirectory() as tmpdir:
    try:
        model = GEOtopSimpleRun(args.inputs_dir)
        model.eval(working_dir=tmpdir)
    except Exception:
        raise

toc = time.perf_counter()
print(f"Wall time: {toc - tic:.2f} seconds.")
