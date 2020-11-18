from abc import ABC, abstractmethod
from datetime import datetime
from subprocess import CalledProcessError, TimeoutExpired
from os.path import join as joinpath

import numpy as np

from . import GEOtop


class GEOtopRun(GEOtop):

    @abstractmethod
    def postprocess(self, working_dir):

        raise NotImplementedError

    def preprocess(self, working_dir, *args, **kwargs):

        settings = self.settings.copy()
        settings.update(kwargs)

        src_path = joinpath(self.inputs_dir, 'geotop.inpts')
        dst_path = joinpath(working_dir, 'geotop.inpts')
        with open(src_path, 'r') as src, open(dst_path, 'w') as dst:
            dst.write(f"! GEOtop input file written by GEOtoPy {datetime.now().strftime('%x %X')}\n")
            while line := src.readline():
                if GEOtopRun._comment_re.match(line):
                    dst.write(line)
                else:
                    try:
                        key, value = GEOtopRun.read_setting(line)

                        if key in settings and value != settings[key]:
                            dst.write(f"! GEOtoPy: {key} overwritten, was {value}\n")
                            line = GEOtopRun.print_setting(key, settings[key])
                        else:
                            line = GEOtopRun.print_setting(key, value)

                        dst.write(line)
                        del settings[key]

                    except ValueError as err:
                        dst.write(f"! GEOtoPy: {err}\n")
                        dst.write(line)

            if settings:
                dst.write("\n! Settings added by GEOtoPy\n")
                for key, value in settings.items():
                    try:
                        line = GEOtopRun.print_setting(key, value)
                        dst.write(line)
                    except ValueError as err:
                        dst.write(f"! GEOtoPy: {err}\n")
                        dst.write(f"{key} = {value}\n")


class Variables(ABC):

    @property
    @abstractmethod
    def num_vars(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def names(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def bounds(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def types(self):
        raise NotImplementedError


class Loss(ABC):

    def __init__(self, model, variables, measure):

        self.model = model
        self.variables = variables
        self.criteria = measure

    @abstractmethod
    def massage(self, *args, **kwargs):

        raise NotImplementedError

    def __call__(self, *args, **kwargs):

        args, kwargs = self.massage(*args, **kwargs)

        try:
            simulation = self.model(*args, **kwargs)
        except CalledProcessError:
            return np.nan
        except TimeoutExpired:
            return np.nan

        return self.criteria(simulation)


class Calibration(ABC):

    @abstractmethod
    def __init__(self, loss, settings):

        self.loss = loss
        self.settings = settings

    @property
    @abstractmethod
    def parametrization(self):

        raise NotImplementedError

    @property
    @abstractmethod
    def optimizer(self):

        raise NotImplementedError

    @abstractmethod
    def __call__(self, *args, **kwargs):

        raise NotImplementedError
