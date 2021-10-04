import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="Plost",
    version="0.2.1",
    author="Thiago Teixeira",
    author_email="me@thiagot.com",
    description="A deceptively simple plotting library for Streamlit",
    license="Apache 2",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tvst/plost",
    packages=setuptools.find_packages(exclude=["tests", "tests.*"]),
    install_requires=[], # Not including Streamlit here to allow nightlies, etc.
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.5',
)
