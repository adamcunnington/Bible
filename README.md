# Bible
The application can be ran in two ways:
1. Locally
2. Via Docker

## 1. Local Installation Instructions
You can run the application locally (in editable mode) which is especially useful if you are making changes to the code. The `make` commands in this section assume you have an executable called `python3.9`. If you do not, you may pass `PYTHON3=x` where `x` is the name of your python 3 executable, e.g. `PYTHON3=python3.7`. Run `make` to see full details.

### Pre Requisites
1. Install makefile dependencies, python3.x and python3.x-dev and build-essential packages (required by python-levenshtein).
2. Set the `ESV_API_TOKEN` environment variable (either explicitly or implicitly via a ./.env file).

### Installation
1. Install the application locally (a virtual environment will be created for you) with `make install`.

### Usage
1. Run the application locally with `make run-local`.


## 2. Docker Installation Instructions
You can run the application inside of a docker container. No dependencies are required other than docker.

### Pre Requisites
1. Install docker.
2. Set the `ESV_API_TOKEN` environment variable (either explicitly or implicitly via a ./.env file).

### Installation
1. Build the docker image with `make build`.

### Usage
1. Run an ephemeral container using the docker image with `make run`.
