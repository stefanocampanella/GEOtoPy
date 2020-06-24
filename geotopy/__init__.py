import os
from shutil import which

print("Welcome to GEOtoPy")

# Look for geotop in PATH, if it's not there try to look in ENV
geotop_exe = which("geotop")
if not geotop_exe:
    geotop_exe_env = os.getenv("GEOTOP_EXE")
    if geotop_exe_env and os.access(geotop_exe_env, os.X_OK):
        geotop_exe = geotop_exe_env

if geotop_exe:
    print(f"GEOtop executable found at {geotop_exe}")
else:
    print("GEOtop executable not found. Please check your installation.")

from .core import GEOtop