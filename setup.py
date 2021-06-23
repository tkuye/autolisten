from setuptools import setup
import setuptools
from distutils.command.clean import clean
from distutils.command.install import install

class MyInstall(install):

    # Calls the default run command, then deletes the build area
    # (equivalent to "setup clean --all").
    def run(self):
        install.run(self)
        c = clean(self.distribution)
        c.all = True
        c.finalize_options()
        c.run()

with open("README.md", "r", encoding="utf-8") as f:
    long_desc=f.read()

setup(
    name="autolisten",
    version="1.0.0",
    author="Tosin Kuye", 
    author_email="tosin.kuye@edmonton.ca",
    description="AutoListen is a scripting tool to record and separate large amounts of audio.",
    long_description=long_desc,
    long_description_content_type="text/markdown",
    url="https://portal-git.edmonton.ca/toskuy/autolisten",
    classifiers=[
        "Programming Language :: Python :: 3",  
        "Topic :: Multimedia :: Sound/Audio :: Capture/Recording"
    ], 
    cmdclass={"install":MyInstall},
    install_requires=["numpy", "sounddevice", "soundfile"],
    python_requires=">=3.6", 
    entry_points={"console_scripts": [
        " autolisten = src.autolisten.main:main"
    ]},
    packages=setuptools.find_packages(exclude=("tests"))

)