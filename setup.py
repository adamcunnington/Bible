import setuptools


with open("requirements.txt") as f:
    dependencies = f.readlines()


setuptools.setup(
    name="Bible",
    install_requires=dependencies
)
