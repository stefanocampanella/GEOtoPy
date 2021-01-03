import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="geotopy",
    version="0.4.2",
    author="Stefano Campanella",
    author_email="scampane@sissa.it",
    description="Paper-thin wrapper to work with GEOtop from Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/stefanocampanella/GEOtoPy",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    include_package_data=True,
    python_requires='>=3.8',
)
