# Bible

Interact with the Bible through an intuitive and extensible API with unprecedented ease. Traverse scripture at speed using a simple object model and run analytical queries across Character metadata through familiar python syntax. The application is designed primarily to be used via a notebook interface but can also be used to power applications.

- [Quick Start (Ubuntu)](#quick-start-ubuntu)
- [Full Setup](#full-setup)
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
    - [Structure](#structure)
      - [Passage References](#passage-references)
      - [Attribute Map](#attribute-map)
      - [Attribute Details](#attribute-details)
    - [Character](#character)
  - [ESV API Specifics](#esv-api-specifics)
    - [Translation Object Extensions](#translation-object-extensions)
    - [ESVText Object Addition](#esvtext-object-addition)
- [Developing Translations](#developing-translations)
  - [1. New Python Package](#1-new-python-package)
  - [2. Translation-Specific Metadata](#2-translation-specific-metadata)
  - [3. Loading the Translation](#3-loading-the-translation)


## Quick Start (Ubuntu)
Install system dependencies, create and activate a virtual environment, install the application from github and launch a python interpreter.
```bash
sudo apt update && sudo apt install -y build-essential python3.9 python3.9-dev vlc
python3.9 -m venv .venv
source .venv/bin/activate
pip install git+https://github.com/adamcunnington/Bible#egg=Bible
python
```

Load the ESV translation, fetch text for Genesis 1:1, fetch audio for Genesis 1:2-2 and fetch a list of mentioned character names.
```python
import bible
esv = bible.esv()
genesis = esv[1]
genesis[1][1].text()
genesis.passage("1:2-2:").audio()
genesis.passage("1-2").characters().values("name")
```

## Full Setup
The application can be executed in two ways:
1. Locally
2. Via Docker

*Note: If you are running WSL or WSL2, you may additional to install and configure additional dependencies to get audio working. See [here]([https://link](https://git.bortle-host.io/eamondo2/wsl2-pulse-x11-setup)) for more details.*

### 1. Local Instructions
The application can be ran locally (in editable mode) which is especially useful if changes are being made to the code. The `make` commands in this section assume an executable called `python3.9`. Alternatively, `PYTHON3=x` can be passed with the make target where `x` is the name of the python3 executable to use, e.g. `PYTHON3=python3.7`. Run `make` to see full details.

#### Pre Requisites
1. Clone the repo.
2. Install makefile dependencies, vlc, python3.x and python3.x-dev and build-essential packages (required by python-levenshtein).
3. Set the `ESV_API_TOKEN` environment variable (either explicitly or implicitly via a ./.env file). To obtain an API token, visit [ESV API documentation](https://api.esv.org/docs/).

#### Installation
1. Install the application locally (a virtual environment will be created) with `make install`.

#### Execution
1. Run the application locally with `make run-local`.

---

### 2. Docker Instructions
The application can also be ran inside of a docker container. No dependencies are required other than docker.

#### Pre Requisites
1. Clone the repo.
2. Install docker.
3. Set the `ESV_API_TOKEN` environment variable, locally (either explicitly or implicitly via a ./.env file). To obtain an API token, visit [ESV API documentation](https://api.esv.org/docs/).

#### Installation
1. Build the docker image with `make build`.

#### Execution
1. Run an ephemeral container using the docker image with `make run`.

---

## Usage
The execution of the application, whether locally or via Docker, starts a python interpreter with the bible package already imported. Translations should be accessed directly through the bible namespace, e.g. `bible.esv`. All attributes are accessed through the `Translation` object directly, or indirectly via descendent objects.

### Core API
There are 6 main objects in the core API.
* `Translation` (e.g. ESV)
* `Book` (e.g. Genesis)
* `Chapter` (e.g. Chapter 1 of Genesis)
* `Verse` (e.g. Verse 1 of Genesis 1)
* `Passage` (e.g. range of verses from 1 or more chapters/books)
* `Character` (e.g. Jesus)

The first 5 objects relate to the structure and content of the bible whilst the 6th relates to character metadata. The two categories will be discussed separately.

#### Structure
[Two tables at the end of this section](#attribute-map) provide an overview of what is available through the core API. The first lists all attributes and which objects they are supported by whilst the second provides information for each attribute as well as details of any object-specific behaviour.

Each translation is responsible for providing both the metadata and content for the translation. Additionally, each translation may extend the core API (or even override, sparingly) to surface extra content or functionality (such as using an online concordance service).

For now, it suffices to say that the first four objects should be seen as a hierarcy, e.g. start with a `Translation` and dive into a `Book`, then `Chapter`, then `Verse` - much like a physical Bible. The fifth, `Passage` object, can be generated by using the `passage()` method on any object that has children (e.g. all but `Verse`) and passing a reference which identifies the range to generate.

##### Passage References
The convention that passage references must follow is consistent across `Translations`, `Books` and `Chapters` but the form minimises as the parent object is scoped down. It is easier to describe the form per parent:

```
Translation.passage(reference=None, int_reference=None)
```
* *reference* - takes the form, `<book> <chapter>:<verse> - <book> <chapter>:<verse>` where spaces are optional, each component is optional, book can be a number, fuzzy matched sluggified name or even fuzzy matched alternative name, and chapter/verse should be numbers. If a component is omitted from the left hand side, it will be assumed to be 1 whereas if a component is omitted from the right hand side, it will either be: i) assumed to be the final entity if there were no components provided afterwards or ii) the same value as the left hand side if there were components provided afterwards. In the case of i), note that this assumption cascades such that the extreme case of *reference=*`x-` will actually return a `Passage` object that spans the rest of the Bible (to the final verse of final chapter of final book) from x onwards. In the case of ii) a more intuitive short hand experience is realised, i.e. the desired behaviour of `Genesis 3-16` is *Genesis 3 - Genesis 16* rather than *Genesis 3 - Revelation 16*. It is also possible to return a single book/chapter/verse by omitting the right hand side entirely as well as the `-` character. If provided, the right hand side must be greater than the left.
* *int_reference* - takes a simplified form, `XXYYYZZZ - XXYYYZZZ` where spaces are optional, XX is an optionally 0-padded book number (i.e. both 6 and 06 are acceptable), YYY is a 00-padded chapter number and ZZZ is a 00-padded verse number. For example, `Genesis 1:1 - Exodus 3:6` would be represented as `01001001 - 02003006`. Each side is optional but the component parts that make up the side are not. If provided, the right hand side must be canonically after the left hand side.

```
Book.passage(reference="-")
```
* *reference* - behaves exactly as *reference* above except it takes the simplified form, `<chapter>:<verse> - <chapter>:<verse>` as the book comes implicitly from the parent object.

```
Chapter.passage(reference="-")
```
* *reference* - behaves exactly as *reference* above except it takes the simplified form, `<verse> - <verse>` as the chapter and book come implicitly from the parent object.

**Examples:**
| PASSAGE REFERENCE                                | BOOK START   | CHAPTER START | VERSE START | BOOK END        | CHAPTER END | VERSE END |
| ------------------------------------------------ | ------------ | ------------- | ----------- | --------------- | ----------- | --------- |
| `Translation`.passage("-")                       | 1 (Genesis)  | 1             | 1           | 66 (Revelation) | 22          | 21        |
| `Translation`.passage("Matth-")                  | 40 (Matthew) | 1             | 1           | 66 (Relevation) | 22          | 21        |
| `Translation`.passage("John 2:3-John")           | 43 (John)    | 2             | 3           | 43 (John)       | 21          | 25        |
| `Translation`.passage("John 2:3 - John 2")       | 43 (John)    | 2             | 3           | 43 (John)       | 2           | 25        |
| `Translation`.passage("John 2-6")                | 43 (John)    | 2             | 1           | 43 (John)       | 6           | 71        |
| `Translation`.passage("John 2:3-6")              | 43 (John)    | 2             | 3           | 43 (John)       | 2           | 6         |
| `Translation`.passage("- Exo")                   | 1 (Genesis)  | 1             | 1           | 2 (Exodus)      | 40          | 38        |
| `Translation`.passage(None, "01001001-02003006") | 1 (Genesis)  | 1             | 1           | 2 (Exodus)      | 3           | 6         |
| `Translation`.passage(None, "37002003-")         | 37 (Haggai)  | 2             | 3           | 66 (Revelation) | 22          | 21        |
| `Translation`.passage(None, "4002009")           | 4 (Numbers)  | 2             | 9           | 4 (Numbers)     | 2           | 9         |
| `Translation`.passage(None, " -2003019")         | 1 (Genesis)  | 1             | 1           | 2 (Exodus)      | 3           | 19        |
| `<Genesis>`.passage("7:13-9:21")                 | 1 (Genesis)  | 7             | 13          | 1 (Genesis)     | 9           | 21        |
| `<Genesis>`.passage("7:13-21")                   | 1 (Genesis)  | 7             | 13          | 1 (Genesis)     | 7           | 21        |
| `<Genesis>`.passage("7-21")                      | 1 (Genesis)  | 7             | 1           | 1 (Genesis)     | 21          | 34        |
| `<Genesis>`.passage("-3:")                       | 1 (Genesis)  | 1             | 1           | 1 (Genesis)     | 3           | 24        |
| `<Genesis>`.passage()                            | 1 (Genesis)  | 1             | 1           | 1 (Genesis)     | 50          | 26        |
| `<John 3>`.passage("9-16")                       | 43 (John)    | 3             | 9           | 43 (John)       | 3           | 16        |
| `<John 3>`.passage("13")                         | 43 (John)    | 3             | 13          | 43 (John)       | 3           | 13        |
| `<John 3>`.passage()                             | 43 (John)    | 3             | 1           | 43 (John)       | 3           | 36        |

---

##### Attribute Map
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
| *.name*                    | :heavy_check_mark: | :heavy_check_mark: |                    |                    |                    |
| *.number*                  |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |
| *.translation*             |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |
| *.verse_end*               |                    |                    |                    |                    | :heavy_check_mark: |
| *.verse_start*             |                    |                    |                    |                    | :heavy_check_mark: |
| *audio()*                  |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |
| *books()*                  |                    | :heavy_check_mark: |                    |                    | :heavy_check_mark: |
| *chapters()*               |                    | :heavy_check_mark: |                    |                    | :heavy_check_mark: |
| *characters(field=None)*   | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |
| *first()*                  | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |                    |
| *last()*                   | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |                    |
| *next(overspill=True)*     |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |
| *passage(...)*             | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |                    |
| *previous(overspill=True)* |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |                    |
| *text()*                   |                    | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: |
| *verses()*                 |                    |                    |                    |                    | :heavy_check_mark: |

##### Attribute Details
| ATTRIBUTE                  | CATEGORY     | DESCRIPTION                                                                 | SPECIAL NOTES                                                  |
| -------------------------- | ------------ | --------------------------------------------------------------------------- | -------------------------------------------------------------- |
| *d[k]*                     | Magic Method | Fetches a child object of the parent (e.g. verse number of chapter).        | `Translation` supports fuzzy lookup using number, id, alt_ids. |
| *k in d*                   | Magic Method | Checks whether an object belongs to a parent (e.g. verse in chapter).       | `Translation` supports fuzzy lookup using number, id, alt_ids. |
| *iter()*                   | Magic Method | Iterates over parent to yield child objects (e.g. verses of chapter).       |                                                                |
| *len()*                    | Magic Method | Finds out how many children the parent has (e.g. verses in a chapter).      | `Passage` object length is the number of verses in the range.  |
| *repr()*                   | Magic Method | Prints a scripture-oriented representation of the object.                   |                                                                |
| *str()*                    | Magic Method | Prints a human-readable scripture reference for the object.                 |                                                                |
| *.alt_ids*                 | Property     | The alternative ids (sluggified names) that the object is known by.         |                                                                |
| *.alt_names*               | Property     | The alternative names that the object is known by.                          |                                                                |
| *.author*                  | Property     | The author/writer of the text.                                              |                                                                |
| *.book*                    | Property     | The `Book` object that the object belongs to.                               |                                                                |
| *.book_end*                | Property     | The `Book` object where the ranged object finishes (e.g. -**Exo**).         |                                                                |
| *.book_start*              | Property     | The `Book` object where the ranged object starts. (e.g. **Gen**-).          |                                                                |
| *.categories*              | Property     | The categories that the object belongs to (e.g. Old Testament).             |                                                                |
| *.chapter*                 | Property     | The `Chapter` object that the object belongs to.                            |                                                                |
| *.chapter_end*             | Property     | The `Chapter` object where the ranged object finishes (e.g. -Exo **4**).    |                                                                |
| *.chapter_start*           | Property     | The `Chapter` object where the ranged object starts (e.g. Gen **4**-).      |                                                                |
| *.id*                      | Property     | The id (sluggified name) that the object is primarily known by.             |                                                                |
| *.int_reference*           | Property     | The object's numeric reference form, XXYYYZZZ (book, chapter, verse).       |                                                                |
| *.is_first*                | Property     | Whether the object is the first in parent (e.g. chapter 1).                 |                                                                |
| *.is_last*                 | Property     | Whether the object is the last in parent (e.g. last chapter of book).       |                                                                |
| *.language*                | Property     | The language the text was written in.                                       |                                                                |
| *.name*                    | Property     | The name that the object is primarily known by.                             |                                                                |
| *.number*                  | Property     | The number that the object is identified by (based on order).               |                                                                |
| *.translation*             | Property     | The `Translation` object that the object belongs to.                        |                                                                |
| *.verse_end*               | Property     | The `Verse` object where the ranged object finishes (e.g. -Exo :**10**).    |                                                                |
| *.verse_start*             | Property     | The `Verse` object where the ranged object starts (e.g. Gen :**9**-).       |                                                                |
| *audio()*                  | Method       | Fetches and plays the audio that relates to the object's text.              |                                                                |
| *books()*                  | Method       | Returns a generator of `Book` objects that relate to the object.            |                                                                |
| *chapters()*               | Method       | Returns a generator of `Chapter` objects that relate to the object.         |                                                                |
| *characters(field=None)*   | Method       | Returns a Filterable object of `Chapter` objects for querying.              |                                                                |
| *first()*                  | Method       | Returns the first child object of parent (e.g. first chapter).              |                                                                |
| *last()*                   | Method       | Returns the last child object of parent (e.g. last chapter of book).        |                                                                |
| *next(overspill=True)*     | Method       | Returns the next object. Spill into next parent object/None.                |                                                                |
| *passage(...)*             | Method       | Returns a `Passage` object ranging across many children (e.g. many verses). | `Translation` supports a second parameter, int_reference.      |
| *previous(overspill=True)* | Method       | Returns the previous object. Spill into previous parent object/None.        |                                                                |
| *text()*                   | Method       | Fetches and prints the text that relates to the object.                     |                                                                |
| *verses()*                 | Method       | Returns a generator of verse objects that relate to the object.             |                                                                |

---

#### Character
The `Character` objects themselves don't have any interesting properties beyond those described in [Character attributes](#2-translation-specific-metadata) but as indicated in the above table, when the `.characters(field=None)` method is called, a `Filterable` object is returned which represents a collection of characters. Any supported logical operation (like SQL predicates) or attempt to access a character attribute will return a new, filtered-down `Filterable` object. Additional reduction methods allow the selection of values (like SQL selects). The following table summarises what is possible:
| ATTRIBUTE                        | CATEGORY         | DESCRIPTION                                                                                 | EXAMPLE                              |
| -------------------------------- | ---------------- | ------------------------------------------------------------------------------------------- | ------------------------------------ |
| *dataclass*                      | Property         | The dataclass that the object's collection are instances of. (read only).                   | c.dataclass                          |
| *field*                          | Property         | The attribute that will be used for logical operations and the values() method by default.  | c.field = "name"                     |
| *fields*                         | Property         | The tuple of attributes that the collection of objects support.                             | c.fields                             |
| *\_\_eq\_\_*                     | Magic Method     | Return a new `Filterable` object, filtering to characters whose attribute == the value.     | c.name == "Adam"                     |
| *\_\_ge\_\_*                     | Magic Method     | Return a new `Filterable` object, filtering to characters whose attribute was >= value.     | c.age >= 35                          |
| *\_\_getattr\_\_*                | Magic Method     | Return a new `Filterable` object, with the *field* attribute set to the name.               | c.name                               |
| *\_\_getitem\_\_*                | Magic Method     | Return the `Character` object based on the *id* attribute of the Character.                 | c[5]                                 |
| *\_\_gt\_\_*                     | Magic Method     | Return a new `Filterable` object, filtering to characters whose attribute was > value.      | c.age > 35                           |
| *\_\_iter\_\_*                   | Magic Method     | Return an iterable of `Character` objects matched by the current filtered object.           | for character in c: ...              |
| *\_\_le\_\_*                     | Magic Method     | Return a new `Filterable` object, filtering to characters whose attribute <= the value.     | c.age <= "Adam"                      |
| *\_\_len\_\_*                    | Magic Method     | Return the number of `Character` objects matched by the current filtered object.            | len(c)                               |
| *\_\_lt\_\_*                     | Magic Method     | Return a new `Filterable` object, filtering to characters whose attribute < the value.      | c.age < 35                           |
| *\_\_ne\_\_*                     | Magic Method     | Return a new `Filterable` object, filtering to characters whose attribute != the value.     | c.name != "Adam"                     |
| *combine(\*filterables)*         | Logical Method   | Return a new `Filterable` object, filtering self to characters described by any filterable. | c.combine(c.born > 200, c.age > 30)  |
| *contains(value, inverse=False)* | Logical Method   | Return a new `Filterable` object, behaves like in (or not in if inverse=True).              | c.spouses.contains(c[4], c[5])       |
| *where(\*values, inverse=False)* | Logical Method   | Return a new `Filterable` object, like __eq__ (__ne__ if inverse=True) but for many values. | c.name.where("Adam", "Eve")          |
| *all(limit=None)*                | Reduction Method | Return a tuple of limit/all `Character` objects matched by the current filtered object.     | c.all()                              |
| *one(error=True)*                | Reduction Method | Return the one matched `Character`, errors if > 1 unless error=False.                       | jesus = c.one()                      |
| *select(\*fields, limit=None)*   | Reduction Method | Return a tuple of limit/all dicts mapping fields (all if none) to `Character` values.       | characters = c.select("name", "age") |
| *values(\*fields, limit=None)*   | Reduction Method | Return a tuple of limit/all scalars (if 0 or 1 fields) or tuples of `Character` values.     | names = c.values("name")             |

---

### ESV API Specifics
For the most part, the ESV translation sticks to the core API. The following additions apply.

#### Translation Object Extensions
```
Translation.search(query, page_size=100)
```
Search the bible for verses that are related to the query and return a generator.
* *query* - a word or phrase to search for.

#### ESVText Object Addition
Calling the *text()* method on any object that supports it will return a `ESVText` object with the following attributes:

```
len(ESVText) -> len(ESVText.body.split())
```
```
repr(ESVText) -> ESVText.body
```
```
ESVText.body -> String text body
```
```
ESVText.footnotes -> String footnotes
```
```
ESVText.title -> String title (where relevant, and typically only first verses)
```

---

## Developing Translations
Adding a translation to the codebase entails 3 tasks:
1. Create a python package under `bible/translations/`
2. Create the translation-specific metadata under `bible/translations/<translation>/data.json`
3. Add the loading of the translation to `bible/__init__.py`

Each of these tasks will be explored in greater detail. It is useful to refer to bible/translations/esv/ as an existing example.

### 1. New Python Package
A typical translation should consist of:
```
bible/translations/<translation>/__init__.py - needed so the translation is a python package; can be empty
bible/translations/<translation>/api.py - the file name is irrelevant but api.py is suggested for consistency
bible/translations/<translation>/enums.py - an optional file where custom enums can be defined
```

In `api.py`, the `Translation`, `Book`, `Chapter`, `Verse`, `Passage` and `Character` classes from `bible.api` should be inherited and implementations should be provided for the `text()` and `audio()` methods. Typically, content for these will come from 3rd party API services. Optionally, extensions to the API can also be made.

It is likely that additional environment variables will be required to accommodate API secrets and possibly additional python dependencies too. Therefore, it is expected that the following files in the root of the project may also need changing accordingly:
- `Dockerfile`
- `README.md`
- `requirements.txt`
- `Makefile`

### 2. Translation-Specific Metadata
The python package alone is not enough. Each translation must provide metadata for the bible structure (as there are subtle variations between translations) and characters.

The base metadata is defined in `bible/data.json`. Translation-specific metadata must be provided at `bible/translations/<translation>/data.json` and is merged with precedence into the base metadata. The properties that relate to the bible book structures are self explanatory - refer to `bible/translations/esv/data/data.json` for a more concrete example. The only detail to call out is the special syntax for expressing enum values. String values can take the form of "X.Y" where X is the name of the enum class and Y is the name of a valid enum within the class. When deserialised, the enum value will be imported as a regular string but this serves to validate the provided values in the JSON.

Regarding character metadata, the below table details the properties available - all of which are optional except for *id* and *passages*.

| Field Name           | Type             | Description                                                                           | Example                       |
| -------------------- | ---------------- | ------------------------------------------------------------------------------------- | ----------------------------- |
| *number*             | string           | The identifier of the character.                                                      | "1"                           |
| *passages*           | array of strings | Each item should be a [valid Translation.passage reference](#passage-references).     | ["Matthew"]                   |
| *age*                | integer          | The age the character died/left earth at.                                             | 35                            |
| *aliases*            | array of strings | Alternative names the character is known by.                                          | ["Son of Man", "Cornerstone"] |
| *born*               | integer          | The year the character was born. Negative number for BC, positive for AD.             | 0                             |
| *cause_of_death*     | enum             | A string (from a consistent list) that describes how the character died.              | "Crucified"                   |
| *died*               | integer          | The year the character died. Negative number for BC, positive for AD.                 | 35                            |
| *father*             | string           | The identifier of the mother character.                                               | "4"                           |
| *mother*             | string           | The identifier of the mother character.                                               | "5"                           |
| *name*               | string           | The primary name the character is known by.                                           | "Jesus"                       |
| *nationality*        | string           | The place/nation where the character is considerd to be from. Often not birthplace.   | "Nazareth"                    |
| *place_of_death*     | enum             | A string (from a consistent list) that describes where the character died.            | "Golgotha"                    |
| *primary_occupation* | enum             | A string (from a consistent list) that describes the character's main job / passtime. | "Carpenter/Savior!"           |
| *spouses*            | array of strings | The identifierss of the character's husbands/wives.                                   | ["1"]                         |

For *passages*, it can be difficult to know how to accurately represent the range of passages that refer to a particular character. The following rule serves as useful guidance:
* If the character is seldom mentioned (e.g. Melchizedek), then a list of very specific verses is most appropriate.
* If the character is described in the context of a story, limit the specifity to entire chapters or even entire books if appropriate (e.g. Jesus).

### 3. Loading the Translation
This is the simplest step. `bible/__init__.py` should be altered in two ways:
- An additional import will be needed; `import bible.translations.<translation>.api`
- An additional function will be needed; `def <translation>: return utils.load_translation(bible.translations.<translation>.api)`

Note that the `utils.load_translation` method takes a second argument which is the enums module to use when deserialising the JSON data. If omitted, `bible.enums` will be used.
