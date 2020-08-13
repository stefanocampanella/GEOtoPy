"""GEOtoPy: a dead simple, paper-thin GEOtop wrapper.

GEOtoPy contains just the GEOtop class, which is used to launch a simulation
and can be subclassed to provide more specific/advanced feature. GEOtop should
be already installed on your system as GEOtoPy does not provide its own
binaries (right now, at least). If the executable can't be located in any of
the directories in your PATH, GEOtoPy will look for the GEOTOP_EXE environment
variable. You can check your installation by running the package (see
`python -m geotopy --help`). However, you can specify the path of the
executable for each simulation, as an optional argument.

    Usage example:

    import geotopy as gtp

    model = GEOtop("path/to/inputs")
    model.run()
"""

import os
import shutil
import subprocess
import warnings

# Checks for default geotop executable, if not found prompts a warning
if path := shutil.which('geotop'):
    _geotop_exe = path
elif path := os.getenv('GEOTOP_EXE'):
    _geotop_exe = path
else:
    _geotop_exe = None
    warnings.warn("Default GEOTop executable not found, check your installation",
                  RuntimeWarning)


class GEOtop:
    """Represents a GEOtop simulation as a black box.

    Attributes:
        inputs_dir : path
            The path of the inputs dir, must be a readable directory
        exe : path
            The path of the `geotop` executable
            (default is geotopy._geotop_exe)
    """
    # The constructor just checks the preconditions on files and
    # directories pointed by the arguments
    def __init__(self, inputs_dir, exe=None, run_args=None):
        # inputs_dir must be a readable directory
        if not os.path.isdir(inputs_dir):
            raise FileNotFoundError(f"{inputs_dir} does not exist.")
        elif not os.access(inputs_dir, os.R_OK):
            raise PermissionError(f"{inputs_dir} is not readable.")
        else:
            self.inputs_dir = inputs_dir

        # and must contain a readable 'geotop.inpts' file
        inputs_path = os.path.join(inputs_dir, 'geotop.inpts')
        if not os.path.isfile(inputs_path):
            raise FileNotFoundError(f"{inputs_path} does not exist.")
        elif not os.access(inputs_path, os.R_OK):
            raise PermissionError(f"{inputs_path} is not readable.")

        # exe must be an executable file (but there are no checks
        # that is indeed a geotop executable)
        exe = exe if exe else _geotop_exe
        if not os.path.isfile(exe):
            raise FileNotFoundError(f"{exe} does not exist.")
        elif not os.access(exe, os.R_OK):
            raise PermissionError(f"{exe} is not readable.")
        else:
            self.exe = exe

        self.run_args = \
            run_args if run_args else {'check': True, 'capture_output': True}

    def preprocess(self, working_dir, *args, **kwargs):
        pass

    def postprocess(self, working_dir):
        pass

    def eval(self, *args, working_dir=None, **kwargs):
        # working_dir must be a writable directory
        working_dir = working_dir if working_dir else self.inputs_dir
        if not os.path.isdir(working_dir):
            raise FileNotFoundError(f"{working_dir} does not exist.")
        elif not os.access(working_dir, os.W_OK):
            raise PermissionError(f"{working_dir} is not writable.")
        else:
            # Copies the content of inputs_dir into working_dir
            shutil.copytree(self.inputs_dir, working_dir, dirs_exist_ok=True)

        # Pre-process step
        self.preprocess(working_dir, *args, **kwargs)

        # runs the model
        subprocess.run([self.exe, working_dir], **self.run_args)

        # Post-process step
        self.postprocess(working_dir)
