import setuptools


with open("requirements.txt") as f:
    dependencies = f.readlines()


setuptools.setup(
    name="ESV",
    install_requires=dependencies
)
