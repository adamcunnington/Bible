import dataclasses
import importlib
import inspect
import itertools
import json
import operator
import os
import sys

from fuzzywuzzy import fuzz
import jsonmerge


# INTERNALS
_json_merge_schema = {
    "properties": {
        "books": {
            "mergeStrategy": "arrayMergeByIndex"
        }
    }
}


class BibleReferenceError(Exception):
    pass


class BibleSetupError(Exception):
    pass


class Filterable:
    def __init__(self, dataclass, iterable, field=None):
        self._dataclass = dataclass
        self._iterable = iterable
        self._fields = self._inspect_fields(self._dataclass)
        self.field = field

    @staticmethod
    def _getattr(i, field):
        if field is None:
            raise BibleReferenceError("the field attribute is not set on the parent object")
        return getattr(i, field)

    @staticmethod
    def _inspect_fields(dataclass):
        fields = (field.name for field in dataclasses.fields(dataclass) if not field.name.startswith("_"))
        properties = (name for name, _ in inspect.getmembers(dataclass, lambda value: isinstance(value, property)))
        return tuple(sorted((*fields, *properties)))

    def __eq__(self, value):
        return Filterable(self._dataclass, self._filter(operator.eq, value), self._field)

    def __ge__(self, value):
        return Filterable(self._dataclass, self._filter(operator.ge, value), self._field)

    def __getattr__(self, name):
        if name not in self.fields:
            raise AttributeError(f"{self._dataclass.__name__!r} object has no attribute {name!r}")
        return Filterable(self._dataclass, self._iterable, name)

    def __getitem__(self, key):
        for i in self:
            if i.id == key:
                return i
        raise KeyError(key)

    def __gt__(self, value):
        return Filterable(self._dataclass, self._filter(operator.gt, value), self._field)

    def __iter__(self):
        return self._tee()

    def __le__(self, value):
        return Filterable(self._dataclass, self._filter(operator.le, value), self._field)

    def __len__(self):
        return sum(1 for _ in self)

    def __lt__(self, value):
        return Filterable(self._dataclass, self._filter(operator.lt, value), self._field)

    def __ne__(self, value):
        return Filterable(self._dataclass, self._filter(operator.ne, value), self._field)

    def _combine(self, *filterables):
        candidates = set().union(*filterables)
        for i in self:
            if i in candidates:
                yield i

    def _contains(self, value):
        for i in self:
            if value in self._getattr(i, self.field):
                yield i

    def _contains_not(self, value):
        for i in self:
            if value not in self._getattr(i, self.field):
                yield i

    def _filter(self, operation, value):
        for i in self:
            if operation(self._getattr(i, self.field), value):
                yield i

    def _tee(self):
        self._iterable, iterable_copy = itertools.tee(self._iterable)
        return iterable_copy

    def _where(self, *values):
        for i in self:
            if self._getattr(i, self.field) in values:
                yield i

    def _where_not(self, *values):
        for i in self:
            if self._getattr(i, self.field) not in values:
                yield i

    @property
    def dataclass(self):
        return self._dataclass

    @property
    def field(self):
        return self._field

    @field.setter
    def field(self, value):
        if value is not None and value not in self._fields:
            raise AttributeError(f"{self._dataclass.__name__!r} object has no attribute {value!r}")
        self._field = value

    @property
    def fields(self):
        return self._fields

    def all(self):
        return tuple(self)

    def combine(self, *filterables):
        return Filterable(self._dataclass, self._combine(*filterables), self._field)

    def contains(self, value, inverse=False):
        if not inverse:
            return Filterable(self._dataclass, self._contains(value), self._field)
        return Filterable(self._dataclass, self._contains_not(value), self._field)

    def one(self, error=True):
        first = None
        for i in self:
            if first is None:
                first = i
            elif error:
                raise BibleReferenceError("there is more than one item that matches the current filter")
            else:
                break
        return first

    def select(self, *fields):
        iterable = self._tee()
        if not fields:
            return [vars(i) for i in iterable]
        return tuple({field: getattr(i, field) for field in fields} for i in iterable)

    def values(self, *fields):
        iterable = self._tee()
        if len(fields) > 1:
            return tuple(tuple(getattr(i, field) for field in fields) for i in iterable)
        field = next(iter(fields), self._field)
        if field is None:
            raise BibleReferenceError("field is not set")
        return tuple(getattr(i, field) for i in iterable)

    def where(self, *values, inverse=False):
        if not inverse:
            return Filterable(self._dataclass, self._where(*values), self._field)
        return Filterable(self._dataclass, self._where_not(*values), self._field)


class FuzzyDict(dict):
    def __init__(self, *args, **kwargs):
        self.ratio_threshold = kwargs.pop("ratio_threshold", 60)
        super().__init__(*args, **kwargs)

    def __getitem__(self, key):
        matched, closest_key, closest_value, ratio = self.search(key)
        if not matched:
            if closest_key is None:
                raise KeyError(key)
            raise KeyError(f"'{key}'. The closest match was {closest_key} but with a ratio ({ratio}) < the threshold ({self.ratio_threshold})")
        return closest_value

    def search(self, key, return_first=False, ratio_threshold_override=None):
        if key in self:
            return (True, key, super().__getitem__(key), 1)
        if not isinstance(key, str):
            return (False, key, None, 0)
        closest_key = None
        closest_ratio = 0
        ratio_threshold = ratio_threshold_override or self.ratio_threshold
        for existing_key in self:
            if not isinstance(existing_key, str):
                continue
            ratio = fuzz.partial_ratio(key, existing_key)
            if ratio > closest_ratio:  # if it's the same, we will favour the one found first; deterministic as python dicts retain order from 3.7
                closest_ratio = ratio
                closest_key = existing_key
                if return_first and closest_ratio >= ratio_threshold:
                    break
        return (closest_ratio >= ratio_threshold, closest_key, self.get(closest_key), closest_ratio)


class Unknown:
    def __str__(self):
        return "Unknown"


class Year(int):
    def __str__(self):
        if self < 0:
            return f"{abs(self)} BC"
        return f"{abs(self)} AD"  # abs() appears extraneous but needed to avoid infinite recursion


def fetch_pattern(cls, group_suffix="_start"):
    name_pattern = getattr(cls, "_NAME_REGEX").pattern
    if group_suffix is not None:
        name_pattern = name_pattern.replace(">", f"{group_suffix}>")
    return name_pattern[1:-1]


def int_reference(book_number, chapter_number=1, verse_number=1):
    return f"{book_number:01d}{chapter_number:03d}{verse_number:03d}"


def load_translation(module_name):
    with open(os.path.join(os.path.dirname(__file__), "data.json")) as f:
        base_data = json.load(f)
    module = sys.modules[module_name]
    file_path = os.path.join(os.path.dirname(module.__file__), "data.json")
    api_module = importlib.import_module(f"{module_name}.api")
    with open(file_path) as f:
        translation_data = json.load(f)
    data = jsonmerge.Merger(_json_merge_schema).merge(base_data, translation_data)
    translation = api_module.Translation(data["translation_meta"]["name"])
    for book_index, book_data in enumerate(data["books"]):
        book = api_module.Book(book_data["name"], book_index + 1, translation, book_data["author"], book_data["language"],
                               alt_names=book_data.get("alt_names", ()), categories=book_data.get("categories", ()))
        for chapter_index, verse_count in enumerate(book_data["chapter_verses"]):
            chapter = api_module.Chapter(chapter_index + 1, book)
            for verse_index in range(verse_count):
                _ = api_module.Verse(verse_index + 1, chapter)
    for character_data in data["characters"]:
        character_data["aliases"] = tuple(character_data.get("aliases", ()))
        character_data["_mother"] = character_data.pop("mother", Unknown())
        character_data["_father"] = character_data.pop("father", Unknown())
        character_data["_spouses"] = tuple(character_data.pop("spouses", ()))
        character_data["passages"] = tuple(translation.passage(passage) for passage in character_data.get("passages", ()))
        _ = api_module.Character(translation=translation, **character_data)
    return translation


def module_of_instance(self):
    return sys.modules[self.__class__.__module__]


def reference(book_name, chapter_number=None, verse_number=None):
    return f"{book_name}{(f' {chapter_number}') if chapter_number else ''}{(f':{verse_number}') if verse_number else ''}"


def safe_int(value):
    str_value = str(value)
    return int(str_value) if str_value.isdigit() else value


def slugify(value):
    try:
        return value.replace(" ", "").upper()  # we don't expect any strange characters in book names
    except AttributeError:
        return value


def unique_value_iterating_dict(d):
    yield from dict.fromkeys(d.values())
