import argparse
import shutil
import subprocess
import time
from . import GEOtop

parser = argparse.ArgumentParser(prog="GEOtoPy",
                                 description="Paper-thin wrapper to work with GEOtop from Python.")
parser.add_argument("inputs_path",
                    help="Input directory, containing geotop.inpts "
                         "and other input files.")
parser.add_argument("working_dir",
                    nargs='?',
                    default=None,
                    help="Working directory, where the inputs will be copied "
                         "and GEOtop will run. Must be different from "
                         "inputs_path.")
cli_args = parser.parse_args()


class Model(GEOtop):

    def preprocess(self, working_dir, *args, **kwargs):
        if shutil.which('tree'):
            print("==== Input files: ====")
            subprocess.run(['tree', '-D', self.inputs_path])
            print()
        self.clone_inputs_to(working_dir)

        print("==== Running GEOtop... ====\n")

    def postprocess(self, working_dir):
        if shutil.which('tree'):
            print(f"==== Output files: ====")
            subprocess.run(['tree', '-D', working_dir])
            print()

        return None


tic = time.perf_counter()
try:
    model = Model(cli_args.inputs_path)
    if working_dir := cli_args.working_dir:
        model.run_in(working_dir)
    else:
        model()
except Exception:
    raise
toc = time.perf_counter()
print(f"Wall time: {toc - tic:.2f} seconds.")
