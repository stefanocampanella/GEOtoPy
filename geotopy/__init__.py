"""GEOtoPy: a dead simple, paper-thin GEOtop wrapper.

GEOtoPy contains just the GEOtop base class, which is able to run the model
once the preprocessing/postprocessing is implemented in a derived class.
GEOtop should be already installed on your system as GEOtoPy does not provide
its own binaries. If the executable can't be located in any of
the directories in your PATH, GEOtoPy will look for the GEOTOP_EXE environment
variable. You can check your installation by running the package (see
`python -m geotopy --help`). However, you can specify the path of the
executable for each simulation, as an optional argument.
"""
import importlib.resources as resources
import json
import os
import re
import io
import tarfile
import shutil
import subprocess
import warnings
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory


class GEOtop(ABC):
    """Represent a GEOtop simulation as a black box.

    Attributes:
        inputs_dir : pathlib object
            The path of the inputs directory, must be a readable directory
            containing a readable geotop.inpts file
        geotop_inpts_path : pathlib object
            The path of the geotop.inpts file
        exe : pathlib object, default = GEOtop._geotop_exe
            The path of the geotop executable
        run_args : dict, default = {'check': True, 'capture_output': True}
            Optional arguments for subprocess.run
        inpts : io.ByteIO object, default = None
            LZMA compressed tar of the inputs directory
        geotop_inpts : list
            Unparsed lines of the geotop.inpts file
        settings: dict
            Simulation settings, parsed at the instantiation of an object
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
    def __init__(self, inputs_dir, exe=None, store=True, compression=None,
                 **kwargs):
        """ Read, parse and store the model settings within inputs_dir.

        :param inputs_dir:
        :param exe:
        :param store:
        :param kwargs:
        """
        super().__init__()

        # inputs_path must be a readable directory
        inputs_dir = Path(inputs_dir)
        if not inputs_dir.is_dir():
            raise FileNotFoundError(f"{inputs_dir} does not exist.")
        elif not os.access(inputs_dir, os.R_OK):
            raise PermissionError(f"{inputs_dir} is not readable.")
        else:
            self.inputs_path = inputs_dir.resolve()

        if store:
            self.inputs = io.BytesIO()
            mode = f"w:{compression if compression else ''}"
            with tarfile.open(fileobj=self.inputs, mode=mode) as tar:
                tar.add(self.inputs_path, arcname='.')
            self.inputs.seek(io.SEEK_SET)
        else:
            self.inputs = None

        # inputs_path must contain a readable 'geotop.inpts' file
        geotop_inpts_path = self.inputs_path / 'geotop.inpts'
        if not geotop_inpts_path.is_file():
            raise FileNotFoundError(f"{geotop_inpts_path} does not exist.")
        elif not os.access(geotop_inpts_path, os.R_OK):
            raise PermissionError(f"{geotop_inpts_path} is not readable.")
        else:
            with open(geotop_inpts_path, 'r') as geotop_inpts_file:
                self.geotop_inpts = geotop_inpts_file.readlines()
            self.settings = dict()
            for line in self.geotop_inpts:
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
        """ Preprocess settings and inputs data,
        then writes them to working_dir.

        This is an abstract method and must be implemented, the implementation
        shall not have side effects (change files in inputs_dir or attributes
        of the object).

        :param working_dir:
        :param args:
        :param kwargs:
        :return:
        """

        raise NotImplementedError

    @abstractmethod
    def postprocess(self, working_dir):
        """ Postprocess the simulation data within working_dir, then return the
        result.

        This is an abstract method and must be implemented, the implementation
        shall not have side effects (change files in inputs_dir or attributes
        of the object).

        :param working_dir:
        :return:
        """

        raise NotImplementedError

    def run_in(self, working_dir, *args, **kwargs):
        """ Evaluate the model within working_dir with provided args and kwargs.

        :param working_dir:
        :param args:
        :param kwargs:
        :return:
        """
        # working_dir must be a writable directory different from inputs_path
        working_dir = Path(working_dir)
        if not working_dir.exists():
            raise FileNotFoundError(f"{working_dir} does not exist.")
        elif not working_dir.is_dir():
            raise RuntimeError(f"{working_dir} is not a directory.")
        elif working_dir.samefile(self.inputs_path):
            raise RuntimeError("Working directory must be "
                               "different from the inputs one.")
        elif not os.access(working_dir, os.W_OK):
            raise PermissionError(f"{working_dir} is not writable.")

        # Pre-process step prepares, takes the inputs and prepare input files
        self.preprocess(working_dir, *args, **kwargs)

        # Run step, it communicates with prev and next step via files
        subprocess.run([self.exe, working_dir], **self.run_args)

        # Post-process step, read files from prev step and returns the output
        output = self.postprocess(working_dir)

        return output

    def __call__(self, *args, **kwargs):
        """ Run the GEOtop model in a temporary directory without side effects.
        :param args:
        :param kwargs:
        :return:
        """

        with TemporaryDirectory() as tmpdir:
            sim = self.run_in(tmpdir, *args, **kwargs)
        return sim

    def clone_inputs_to(self, working_dir):
        """ Copy the content of inputs_path into working_dir, using the its
        internal (compressed) copy of the files if available.
        
        :param working_dir: 
        :return: 
        """
        if self.inputs:
            with tarfile.open(fileobj=self.inputs, mode='r') as tar:
                tar.extractall(path=working_dir)
            self.inputs.seek(io.SEEK_SET)
        else:
            shutil.copytree(self.inputs_path, working_dir, dirs_exist_ok=True)

    def patch_geotop_inpts_file(self, working_dir, settings):
        """ Patch the geotop.inpts file within working_dir with current
        settings.

        :param working_dir:
        :param settings:
        :return:
        """
        settings = settings.copy()
        destination_path = working_dir / 'geotop.inpts'
        with open(destination_path, 'w') as destination:
            destination.write("! GEOtop input file written by GEOtoPy "
                              f"{datetime.now().strftime('%x %X')}\n")
            for setting in self.geotop_inpts:
                if GEOtop._comment_re.match(setting):
                    destination.write(setting)
                else:
                    try:
                        key, value = GEOtop.read_setting(setting)

                        if key in settings and value != settings[key]:
                            destination.write(f"! GEOtoPy: {key} overwritten, "
                                              f"was {value}\n")
                            setting = GEOtop.print_setting(key, settings[key])

                            del settings[key]
                        elif key not in settings:
                            destination.write(f"! GEOtoPy: {key} deleted")
                            setting = "!" + setting

                        destination.write(setting)


                    except ValueError as err:
                        destination.write(f"! GEOtoPy: {err}\n")
                        destination.write(setting)

            if settings:
                destination.write("\n! Settings added by GEOtoPy\n")
                for key, value in settings.items():
                    try:
                        setting = GEOtop.print_setting(key, value)
                        destination.write(setting)
                    except ValueError as err:
                        destination.write(f"! GEOtoPy: {err}\n")
                        destination.write(f"{key} = {value}\n")

    @staticmethod
    def read_setting(line):
        """ Read a geotop.inpts line and return a keyword, value pair.
        Raise an error if the line is not a setting or if the keyword is
        unknown. Warn the user if the keyword type is unknown.

        :param line:
        :return:
        """
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
        """ Print a geotop.inpts line with provided keyword and value. Raise
        an error if keyword is unknown. Warn the user if the keyword type is
        unknown.

        :param key:
        :param value:
        :return:
        """
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
