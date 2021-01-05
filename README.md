# Bible

- [Setup](#setup)
  - [1. Local Instructions](#1-local-instructions)
    - [Pre Requisites](#pre-requisites)
    - [Installation](#installation)
    - [Execution](#execution)
  - [2. Docker Instructions](#2-docker-instructions)
    - [Pre Requisites](#pre-requisites-1)
    - [Installation](#installation-1)
    - [Execution](#execution-1)
- [Usage](#usage)
  - [Core API](#core-api)
  - [ESV API Extensions](#esv-api-extensions)



## Setup
The application can be executed in two ways:
1. Locally
2. Via Docker

### 1. Local Instructions
You can run the application locally (in editable mode) which is especially useful if you are making changes to the code. The `make` commands in this section assume you have an executable called `python3.9`. If you do not, you may pass `PYTHON3=x` where `x` is the name of your python 3 executable, e.g. `PYTHON3=python3.7`. Run `make` to see full details.

#### Pre Requisites
1. Clone the repo.
2. Install makefile dependencies, python3.x and python3.x-dev and build-essential packages (required by python-levenshtein).
3. Set the `ESV_API_TOKEN` environment variable (either explicitly or implicitly via a ./.env file).

#### Installation
1. Install the application locally (a virtual environment will be created for you) with `make install`.

#### Execution
1. Run the application locally with `make run-local`.


### 2. Docker Instructions
You can run the application inside of a docker container. No dependencies are required other than docker.

#### Pre Requisites
1. Clone the repo.
2. Install docker.
3. Set the `ESV_API_TOKEN` environment variable (either explicitly or implicitly via a ./.env file).

#### Installation
1. Build the docker image with `make build`.

#### Execution
1. Run an ephemeral container using the docker image with `make run`.



## Usage

### Core API
| Attribute                | Category     | Description | Translation        | Book               | Chapter            | Verse              | Passage            |
| ------------------------ | ------------ | ----------- | :----------------: | :----------------: | :----------------: | :----------------: | :----------------: |
| repr()                   | Magic Method |             | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |
| str()                    | Magic Method |             | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |
| k in d                   | Magic Method |             | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |                    |
| d[k]                     | Magic Method |             | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |                    |
| iter()                   | Magic Method |             | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |                    |
| len()                    | Magic Method |             | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    | :heavy_check_mark: |
| .alt_ids                 | Property     |             |                    | :heavy_check_mark: |                    |                    |                    |
| .alt_names               | Property     |             |                    | :heavy_check_mark: |                    |                    |                    |
| .author                  | Property     |             |                    | :heavy_check_mark: |                    |                    |                    |
| .book                    | Property     |             |                    |                    | :heavy_check_mark: | :heavy_check_mark: |                    |
| .book_end                | Property     |             |                    |                    |                    |                    | :heavy_check_mark: |
| .book_start              | Property     |             |                    |                    |                    |                    | :heavy_check_mark: |
| .categories              | Property     |             | :heavy_check_mark: | :heavy_check_mark: |                    |                    |                    |
| .chapter                 | Property     |             |                    |                    |                    | :heavy_check_mark: |                    |
| .chapter_end             | Property     |             |                    |                    |                    |                    | :heavy_check_mark: |
| .chapter_start           | Property     |             |                    |                    |                    |                    | :heavy_check_mark: |
| .id                      | Property     |             |                    | :heavy_check_mark: |                    |                    |                    |
| .int_reference           | Property     |             |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |
| .is_first                | Property     |             |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |
| .is_last                 | Property     |             |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |
| .language                | Property     |             |                    | :heavy_check_mark: |                    |                    |                    |
| .name                    | Property     |             |                    | :heavy_check_mark: |                    |                    |                    |
| .number                  | Property     |             |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |
| .translation             | Property     |             |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |
| .verse_end               | Property     |             |                    |                    |                    |                    | :heavy_check_mark: |
| .verse_start             | Property     |             |                    |                    |                    |                    | :heavy_check_mark: |
| audio()                  | Method       |             |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |
| books()                  | Method       |             |                    | :heavy_check_mark: |                    |                    | :heavy_check_mark: |
| chapters()               | Method       |             |                    | :heavy_check_mark: |                    |                    | :heavy_check_mark: |
| first()                  | Method       |             | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |                    |
| last()                   | Method       |             | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |                    |
| next(overspill=True)     | Method       |             |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |
| passage(reference="-")   | Method       |             | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |                    |
| previous(overspill=True) | Method       |             |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |
| text()                   | Method       |             |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |
| verses()                 | Method       |             |                    |                    |                    |                    | :heavy_check_mark: |

### ESV API Extensions
```
Translation.search(query, page_size=100)
```

```
len(Text) -> len(Text.body.split())
repr(Text) -> Text.body
Text.body
Text.footnotes
Text.title
```
