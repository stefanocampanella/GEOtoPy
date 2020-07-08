import os
import glob
import tempfile
import re

import pandas as pd
from geotopy.core import GEOtop

with tempfile.TemporaryDirectory() as tmpdir:

    model = GEOtop("inputs", dest=tmpdir)

    print(f"Running GEOtop...")
    model.run(check=True, capture_output=True)

    print("Saving dataframes...")
    glob_path = os.path.join(tmpdir, "output/*.txt")
    for file_path in glob.iglob(glob_path):
        df = pd.read_csv(file_path, na_values=['-9999'])
        basename = os.path.basename(file_path)
        basename = basename.split(".")[0]
        key = re.match(r"[a-z]+", basename).group(0)
        df.to_hdf("output/Matsch_B2_Ref_007.h5", key=key)
