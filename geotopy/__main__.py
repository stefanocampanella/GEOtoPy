import argparse
import os
import time
import geotopy as gtp
import subprocess
import shutil

parser = argparse.ArgumentParser(prog="GEOtoPy",
                                 description="Simple GEOtop launcher.")
parser.add_argument("inputs_dir",
                    help="Input directory, containing geotop.inpts "
                         "and other input files.")
parser.add_argument("outputs_dir",
                    help="Working directory, where the inputs will be copied "
                         "and GEOtop will run. Must be different from "
                         "inputs_dir.")
cli_args = parser.parse_args()


class GEOtopSimpleRun(gtp.GEOtop):

    def preprocess(self, working_dir, *args, **kwargs):
        if shutil.which('tree'):
            print("==== Input files: ====")
            subprocess.run(['tree', '-D', self.inputs_dir])
            print()

        print("==== Overriding geotop.inpts ====\n")
        geotop_inpts = os.path.join(working_dir, 'geotop.inpts')
        os.remove(geotop_inpts)
        with open(geotop_inpts, 'w') as settings:
            settings.write("! GEOtop input file written by GEOtoPy\n")
            for key, value in self.items():
                settings.write(gtp.print_setting(key, value))

        print("==== Running GEOtop... ====\n")

    def postprocess(self, working_dir):
        if shutil.which('tree'):
            print(f"==== Output files: ====")
            subprocess.run(['tree', '-D', working_dir])
            print()

        return None


tic = time.perf_counter()
try:
    model = GEOtopSimpleRun(cli_args.inputs_dir)
    model.eval(cli_args.outputs_dir)
except Exception:
    raise

toc = time.perf_counter()
print(f"Wall time: {toc - tic:.2f} seconds.")
