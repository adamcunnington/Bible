import setuptools


with open("requirements.txt") as f:
    dependencies = f.readlines()


setuptools.setup(
    name="Bible",
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=dependencies,
    extras_require={
        "dev": [
            "flake8",
            "pyclean"
        ]
    }
)
