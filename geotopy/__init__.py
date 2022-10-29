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
from multiprocessing import Lock
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
            self.lock = Lock()
        else:
            self.inputs = None

        # inputs_path must contain a readable 'geotop.inpts' file
        geotop_inpts_path = self.inputs_path / 'geotop.inpts'
        if not geotop_inpts_path.is_file():
            raise FileNotFoundError(f"{geotop_inpts_path} does not exist.")
        elif not os.access(geotop_inpts_path, os.R_OK):
            raise PermissionError(f"{geotop_inpts_path} is not readable.")
        else:
            self.settings = GEOtop.read_settings(geotop_inpts_path)

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

    def clone_into(self, working_dir):
        """ Copy the content of inputs_path into working_dir, using the its
        internal (compressed) copy of the files if available.
        
        :param working_dir: 
        :return: 
        """
        if self.inputs:
            with self.lock:
                with tarfile.open(fileobj=self.inputs, mode='r') as tar:
                    def is_within_directory(directory, target):
                        
                        abs_directory = os.path.abspath(directory)
                        abs_target = os.path.abspath(target)
                    
                        prefix = os.path.commonprefix([abs_directory, abs_target])
                        
                        return prefix == abs_directory
                    
                    def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                    
                        for member in tar.getmembers():
                            member_path = os.path.join(path, member.name)
                            if not is_within_directory(path, member_path):
                                raise Exception("Attempted Path Traversal in Tar File")
                    
                        tar.extractall(path, members, numeric_owner=numeric_owner) 
                        
                    
                    safe_extract(tar, path=working_dir)
                self.inputs.seek(io.SEEK_SET)
        else:
            shutil.copytree(self.inputs_path, working_dir, dirs_exist_ok=True)

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
    def read_settings(geotop_inpts_path):
        """ Read a geotop.inpts file and return a dictionary of settings.
        Warn the user if there are malformed lines.

        :param geotop_inpts_path:
        :return:
        """
        settings = {}
        with open(geotop_inpts_path, 'r') as geotop_inpts_file:
            while line := geotop_inpts_file.readline():
                if not GEOtop._comment_re.match(line):
                    try:
                        key, value = GEOtop.read_setting(line)
                        settings[key] = value
                    except ValueError as err:
                        warnings.warn(f"{err} Skipping.")
        return settings

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

    @staticmethod
    def dump_to(settings, destination):
        """ Dump settings to destination file

        :param settings:
        :param destination:
        :return:
        """
        for keyword, value in settings.items():
            if value:
                line = GEOtop.print_setting(keyword, value)
                destination.write(line)

    @staticmethod
    def dump_in(settings, working_dir):
        """ Dump settings in working_dir/geotop.inpts

        :param settings:
        :param working_dir:
        :return:
        """
        destination_path = working_dir / 'geotop.inpts'
        with open(destination_path, 'w') as destination:
            GEOtop.dump_to(settings, destination)

    @staticmethod
    def patch_inpts_file(working_dir, diff, annotations=True):
        """ Patch the geotop.inpts file within working_dir with current
        settings.

        :param annotations:
        :param working_dir:
        :param diff:
        :return:
        """
        diff = diff.copy()
        geotop_inpts = working_dir / 'geotop.inpts'

        with open(geotop_inpts, 'r') as source:
            text_settings = source.readlines()

        with open(geotop_inpts, 'w') as destination:
            destination.write("! GEOtop input file written by GEOtoPy "
                              f"{datetime.now().strftime('%x %X')}\n")
            for line in text_settings:
                if GEOtop._comment_re.match(line):
                    destination.write(line)
                else:
                    try:
                        key, value = GEOtop.read_setting(line)
                        if key in diff:
                            if diff[key] is None:
                                if annotations:
                                    destination.write(f"! GEOtoPy: {key} deleted, "
                                                      f"was {value}.\n")
                            elif diff[key] != value:
                                if annotations:
                                    destination.write(f"! GEOtoPy: {key} overwritten, "
                                                      f"was {value}.\n")
                                line = GEOtop.print_setting(key, diff[key])
                            del diff[key]

                        destination.write(line)

                    except ValueError as err:
                        if annotations:
                            destination.write(f"! GEOtoPy: {err}\n")

            if diff:
                if annotations:
                    destination.write("\n! Settings added by GEOtoPy\n")
                GEOtop.dump_to(diff, destination)
