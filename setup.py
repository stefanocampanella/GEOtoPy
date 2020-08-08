import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="geotopy",
    version="0.0.1",
    author="Stefano Campanella",
    author_email="scampane@sissa.it",
    description="A calibration tool for GEOtop",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/stefanocampanella/GEOtoPy",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)
