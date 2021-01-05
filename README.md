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

#### All Attributes
| ATTRIBUTE                  | CATEGORY     | DESCRIPTION                                                            | SPECIAL NOTES                                                  |
| -------------------------- | ------------ | ---------------------------------------------------------------------- | -------------------------------------------------------------- |
| *d[k]*                     | Magic Method | Fetches a child object of the parent (e.g. verse number of chapter).   | `Translation` supports fuzzy lookup using number, id, alt_ids. |
| *k in d*                   | Magic Method | Checks whether an object belongs to a parent (e.g. verse in chapter).  | `Translation` supports fuzzy lookup using number, id, alt_ids. |
| *iter()*                   | Magic Method | Iterates over parent to yield child objects (e.g. verses of chapter).  |                                                                |
| *len()*                    | Magic Method | Finds out how many children the parent has (e.g. verses in a chapter). | `Text` object length is the number of words in the text body.  |
| *repr()*                   | Magic Method | Prints a scripture-oriented representation of the object.              |                                                                |
| *str()*                    | Magic Method | Prints a human-readable scripture reference for the object.            |                                                                |
| *.alt_ids*                 | Property     | The alternative ids (sluggified names) that the object is known by.    |                                                                |
| *.alt_names*               | Property     | The alternative names that the object is known by.                     |                                                                |
| *.author*                  | Property     | The author/writer of the text.                                         |                                                                |
| *.book*                    | Property     | The book object that the object belongs to.                            |                                                                |
| *.book_end*                | Property     | The book object where the ranged object finishes (e.g. -**Exo**).      |                                                                |
| *.book_start*              | Property     | The book object where the ranged object starts. (e.g. **Gen**-).       |                                                                |
| *.categories*              | Property     | The categories that the object belongs to (e.g. Old Testament).        |                                                                |
| *.chapter*                 | Property     | The chapter object that the object belongs to.                         |                                                                |
| *.chapter_end*             | Property     | The chapter object where the ranged object finishes (e.g. -Exo **4**). |                                                                |
| *.chapter_start*           | Property     | The chapter object where the ranged object starts (e.g. Gen **4**-).   |                                                                |
| *.id*                      | Property     | The id (sluggified name) that the object is primarily known by.        |                                                                |
| *.int_reference*           | Property     | The object's numeric reference form, XXYYYZZZ (book, chapter, verse).  |                                                                |
| *.is_first*                | Property     | Whether the object is the first in parent (e.g. chapter 1).            |                                                                |
| *.is_last*                 | Property     | Whether the object is the last in parent (e.g. last chapter of book).  |                                                                |
| *.language*                | Property     | The language the text was written in.                                  |                                                                |
| *.name*                    | Property     | The name that the object is primarily known by.                        |                                                                |
| *.number*                  | Property     | The number that the object is identified by (based on order).          |                                                                |
| *.translation*             | Property     | The translation object that the object belongs to.                     |                                                                |
| *.verse_end*               | Property     | The verse object where the ranged object finishes (e.g. -Exo :**10**). |                                                                |
| *.verse_start*             | Property     | The verse object where the ranged object starts (e.g. Gen :**9**-).    |                                                                |
| *audio()*                  | Method       | Fetches and plays the audio that relates to the object's text.         |                                                                |
| *books()*                  | Method       | Returns a generator of book objects that relate to the object.         |                                                                |
| *chapters()*               | Method       | Returns a generator of chapter objects that relate to the object.      |                                                                |
| *first()*                  | Method       | Returns the first child object of parent (e.g. first chapter).         |                                                                |
| *last()*                   | Method       | Returns the last child object of parent (e.g. last chapter of book).   |                                                                |
| *next(overspill=True)*     | Method       | Returns the next object. Spill into next parent object/None.           |                                                                |
| *passage(reference="-")*   | Method       | Returns an object ranging across many children (e.g. many verses).     |                                                                |
| *previous(overspill=True)* | Method       | Return sthe previous object. Spill into previous parent object/None.   |                                                                |
| *text()*                   | Method       | Fetches and prints the text that relates to the object.                | ESV translation returns a `Text` object with extra properties. |
| *verses()*                 | Method       | Returns a generator of verse objects that relate to the object.        |                                                                |

#### Attribute Support
| ATTRIBUTE                  |    TRANSLATION     |        BOOK        |      CHAPTER       |       VERSE        |      PASSAGE       |
| -------------------------- | :----------------: | :----------------: | :----------------: | :----------------: | :----------------: |
| *d[k]*                     | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |                    |
| *k in d*                   | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |                    |
| *iter()*                   | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |                    |
| *len()*                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    | :heavy_check_mark: |
| *repr()*                   | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |
| *str()*                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |
| *.alt_ids*                 |                    | :heavy_check_mark: |                    |                    |                    |
| *.alt_names*               |                    | :heavy_check_mark: |                    |                    |                    |
| *.author*                  |                    | :heavy_check_mark: |                    |                    |                    |
| *.book*                    |                    |                    | :heavy_check_mark: | :heavy_check_mark: |                    |
| *.book_end*                |                    |                    |                    |                    | :heavy_check_mark: |
| *.book_start*              |                    |                    |                    |                    | :heavy_check_mark: |
| *.categories*              | :heavy_check_mark: | :heavy_check_mark: |                    |                    |                    |
| *.chapter*                 |                    |                    |                    | :heavy_check_mark: |                    |
| *.chapter_end*             |                    |                    |                    |                    | :heavy_check_mark: |
| *.chapter_start*           |                    |                    |                    |                    | :heavy_check_mark: |
| *.id*                      |                    | :heavy_check_mark: |                    |                    |                    |
| *.int_reference*           |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |
| *.is_first*                |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |
| *.is_last*                 |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |
| *.language*                |                    | :heavy_check_mark: |                    |                    |                    |
| *.name*                    |                    | :heavy_check_mark: |                    |                    |                    |
| *.number*                  |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |
| *.translation*             |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |
| *.verse_end*               |                    |                    |                    |                    | :heavy_check_mark: |
| *.verse_start*             |                    |                    |                    |                    | :heavy_check_mark: |
| *audio()*                  |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |
| *books()*                  |                    | :heavy_check_mark: |                    |                    | :heavy_check_mark: |
| *chapters()*               |                    | :heavy_check_mark: |                    |                    | :heavy_check_mark: |
| *first()*                  | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |                    |
| *last()*                   | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |                    |
| *next(overspill=True)*     |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |
| *passage(reference="-")*   | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |                    |
| *previous(overspill=True)* |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |
| *text()*                   |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |
| *verses()*                 |                    |                    |                    |                    | :heavy_check_mark: |

### ESV API Extensions

#### Translation
```
Translation.search(query, page_size=100)
```


#### Text
```
len(Text) -> len(Text.body.split())
```
```
repr(Text) -> Text.body
```
```
Text.body
```
```
Text.footnotes
```
```
Text.title
```
