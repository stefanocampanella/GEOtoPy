"""GEOtoPy: a dead simple, paper-thin GEOtop wrapper.

GEOtoPy contains just the GEOtop class, which is used to launch a simulation
and can be subclassed to provide more specific/advanced feature. GEOtop should
be already installed on your system as GEOtoPy does not provide its own
binaries. If the executable can't be located in any of
the directories in your PATH, GEOtoPy will look for the GEOTOP_EXE environment
variable. You can check your installation by running the package (see
`python -m geotopy --help`). However, you can specify the path of the
executable for each simulation, as an optional argument.
"""
import importlib.resources as resources
import json
import os
import re
import shutil
import subprocess
import warnings
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory


class GEOtop(ABC):
    """Represents a GEOtop simulation as a black box.

    Attributes:
        inputs_dir : pathlib object
            The path of the inputs dir, must be a readable directory containing
            a readable `geotop.inpts` file
        geotop_inpts_path : pathlib object
            The path of the `geotop.inpts` file
        exe : pathlib object, default = GEOtop._geotop_exe
            The path of the `geotop` executable
        run_args: dict, default = {'check': True, 'capture_output': True}
            Optional arguments for subprocess.run
        settings: dict
            Simulation settings, parsed at instantiation of a GEOtop object
    """

    # Checks for default geotop executable, if not found prompts a warning
    if geotop_path := shutil.which('geotop'):
        _geotop_exe = Path(geotop_path).resolve()
    elif geotop_path := os.getenv('GEOTOP_EXE'):
        _geotop_exe = Path(geotop_path).resolve()
    else:
        _geotop_exe = None
        warnings.warn("Default GEOTop executable not found, check your installation.",
                      RuntimeWarning)

    # Load keywords type dictionary
    with resources.open_text(__name__, 'keywords.json') as keywords_file:
        keywords = json.load(keywords_file)

    _comment_re = re.compile(r'\s*!.*\n|\s+')
    _setting_re = re.compile(r'\s*(?P<keyword>[A-Z]\w*)\s*=\s*(?P<value>.*)(?:\n|\Z)')

    # The constructor just check all preconditions and parse `geotop.inpts`
    def __init__(self, inputs_dir, exe=None, **kwargs):
        super().__init__()

        # inputs_dir must be a readable directory
        inputs_dir = Path(inputs_dir)
        if not inputs_dir.is_dir():
            raise FileNotFoundError(f"{inputs_dir} does not exist.")
        elif not os.access(inputs_dir, os.R_OK):
            raise PermissionError(f"{inputs_dir} is not readable.")
        else:
            self.inputs_dir = inputs_dir.resolve()

        # and must contain a readable 'geotop.inpts' file
        inputs_path = self.inputs_dir / 'geotop.inpts'
        if not inputs_path.is_file():
            raise FileNotFoundError(f"{inputs_path} does not exist.")
        elif not os.access(inputs_path, os.R_OK):
            raise PermissionError(f"{inputs_path} is not readable.")
        else:
            self.geotop_inpts_path = inputs_path
            self.settings = dict()
            with open(inputs_path, 'r') as f:
                while line := f.readline():
                    if not GEOtop._comment_re.match(line):
                        try:
                            key, value = GEOtop.read_setting(line)
                            self.settings[key] = value
                        except ValueError as err:
                            warnings.warn(f"{err} Skipping.")

        # exe must be an executable file
        exe = Path(exe) if exe else GEOtop._geotop_exe
        if not exe:
            raise RuntimeError("A GEOtop executable must be provided")
        elif not exe.is_file():
            raise FileNotFoundError(f"{exe} does not exist.")
        elif not os.access(exe, os.X_OK):
            raise PermissionError(f"{exe} is not executable.")
        else:
            self.exe = exe.resolve()

        self.run_args = {'check': True, 'capture_output': True}
        if kwargs:
            self.run_args.update(kwargs)

    @abstractmethod
    def preprocess(self, working_dir, *args, **kwargs):

        raise NotImplementedError

    @abstractmethod
    def postprocess(self, working_dir):

        raise NotImplementedError

    def eval(self, working_dir, *args, **kwargs):
        # working_dir must be a writable directory different from inputs_dir
        working_dir = Path(working_dir)
        if not working_dir.exists():
            raise FileNotFoundError(f"{working_dir} does not exist.")
        elif not working_dir.is_dir():
            raise RuntimeError(f"{working_dir} is not a directory.")
        elif working_dir.samefile(self.inputs_dir):
            raise RuntimeError("Working directory must be "
                               "different from the inputs one.")
        elif not os.access(working_dir, os.W_OK):
            raise PermissionError(f"{working_dir} is not writable.")
        else:
            # Copies the content of inputs_dir into working_dir
            shutil.copytree(self.inputs_dir, working_dir, dirs_exist_ok=True)

        # Pre-process step prepares, takes the inputs and prepare input files
        self.preprocess(working_dir, *args, **kwargs)

        # Run step, it communicates with prev and next step via files
        subprocess.run([self.exe, working_dir], **self.run_args)

        # Post-process step, read files from prev step and returns the output
        output = self.postprocess(working_dir)

        return output

    # Calling the GEOtop object runs the model in a temporary directory
    def __call__(self, *args, **kwargs):

        with TemporaryDirectory() as tmpdir:
            sim = self.eval(tmpdir, *args, **kwargs)
        return sim

    def overwrite_settings(self, working_dir, new_settings):

        settings = self.settings.copy()
        settings.update(new_settings)

        destination_path = working_dir / 'geotop.inpts'
        with open(self.geotop_inpts_path, 'r') as src, open(destination_path, 'w') as destination:
            destination.write(f"! GEOtop input file written by GEOtoPy {datetime.now().strftime('%x %X')}\n")
            while line := src.readline():
                if GEOtop._comment_re.match(line):
                    destination.write(line)
                else:
                    try:
                        key, value = GEOtop.read_setting(line)

                        if key in settings and value != settings[key]:
                            destination.write(f"! GEOtoPy: {key} overwritten, was {value}\n")
                            line = GEOtop.print_setting(key, settings[key])
                        else:
                            line = GEOtop.print_setting(key, value)

                        destination.write(line)
                        del settings[key]

                    except ValueError as err:
                        destination.write(f"! GEOtoPy: {err}\n")
                        destination.write(line)

            if settings:
                destination.write("\n! Settings added by GEOtoPy\n")
                for key, value in settings.items():
                    try:
                        line = GEOtop.print_setting(key, value)
                        destination.write(line)
                    except ValueError as err:
                        destination.write(f"! GEOtoPy: {err}\n")
                        destination.write(f"{key} = {value}\n")

    @staticmethod
    def read_setting(line):
        if match := GEOtop._setting_re.match(line):
            key, value = match.groups()
        else:
            raise ValueError(f"{line} is not a valid setting.")

        if key not in GEOtop.keywords:
            raise ValueError(f"Unknown keyword {key}.")
        else:
            keyword_type = GEOtop.keywords[key]
            if keyword_type == 'float':
                value = float(value)
            elif keyword_type == 'array':
                value = [float(n) for n in value.split(',')]
            elif keyword_type == 'bool':
                value = True if int(value) == 1 else False
            elif keyword_type == 'int':
                value = int(value)
            elif keyword_type == 'string':
                value = str(value)
            else:
                warnings.warn(f"Unknown type of {key}, please"
                              f" consider updating \'keywords.json\' file"
                              f" in the GEOtoPy repository with a PR.")
        return key, value

    @staticmethod
    def print_setting(key, value):
        if key not in GEOtop.keywords:
            raise ValueError(f"Unknown keyword {key}.")
        else:
            keyword_type = GEOtop.keywords[key]
            if keyword_type in ('float', 'int', 'string'):
                line = f"{key} = {value}\n"
            elif keyword_type == 'bool':
                line = f"{key} = {1 if value else 0}\n"
            elif keyword_type == 'array':
                line = f"{key} = {str(value).strip('[]')}\n"
            else:
                warnings.warn(f"Unknown type of {key}, please"
                              f" consider updating \'keywords.json\' file"
                              f" in the GEOtoPy repository with a PR.")
                line = f"{key} = {value}\n"
        return line
