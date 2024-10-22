from setuptools import setup, find_packages

setup(
    name="trajectory_simulator",
    version="1.0.2",
    packages=find_packages(),
    install_requires=[
        'shapely',
    ],
    author="sgc",
    author_email="s944804675@gmail.com",
    description="A trajectory simulation package. Add elevation data to trajectory.",
    long_description=open('README.md',encoding='utf-8').read(),
    long_description_content_type="text/markdown",
    url="",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)