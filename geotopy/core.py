import os
import shutil
import subprocess
from . import geotop_exe
import string

class GEOtop:
    def __init__(self, src, dest=None, replace=None):

        if os.path.isdir(src):
            if dest:
                shutil.copytree(src, dest, dirs_exist_ok=True)
                self.working_dir = dest
            else:
                self.working_dir = src
        else:
            raise FileNotFoundError(f"{src} does not exist.")

        self.inputs_path = os.path.join(self.working_dir, "geotop.inpts")

        self.replace = replace
        if replace:
            self.inputs_template_path = \
                os.path.join(self.working_dir, "geotop.inpts.template")

    def run(self, **kwargs):
        if self.replace:
            with open(self.inputs_template_path, "r") as template_file, \
                    open(self.inputs_path, "w") as inputs_file:
                inputs_template = string.Template(template_file.read())
                inputs = inputs_template.substitute(self.replace)
                inputs_file.write(inputs)
        elif not os.access(self.inputs_path, os.F_OK):
            raise FileNotFoundError(f"{self.inputs_path} does not exist.")

        subprocess.run([geotop_exe, self.working_dir], **kwargs)
