import argparse
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
        print("==== Cloning files and patching `geotop.inpts`... ====")
        tic = time.perf_counter()
        self.clone_into(working_dir)
        self.patch_inpts_file(working_dir, kwargs)
        toc = time.perf_counter()
        print(f"Elapsed time: {toc - tic:.2f} seconds.")

        print("==== Running GEOtop... ====")

    def postprocess(self, working_dir):
        return None


if __name__ == "__main__":
    print("==== Storing files and parsing `geotop.inpts`... ====")
    tic = time.perf_counter()
    model = Model(cli_args.inputs_path)
    toc = time.perf_counter()
    print(f"Elapsed time: {toc - tic:.2f} seconds.")

    tic = time.perf_counter()
    if working_dir := cli_args.working_dir:
        model.run_in(working_dir, LSAI=0)
    else:
        model(LSAI=0)
    toc = time.perf_counter()
    print(f"Elapsed time: {toc - tic:.2f} seconds.")
    print()
