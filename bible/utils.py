import dataclasses
import enum
import glob
import inspect
import itertools
import json
import operator
import os
import sys

from fuzzywuzzy import fuzz
import jsonmerge

from bible import enums


class Unknown:
    def __bool__(self):
        return False

    def __repr__(self):
        return repr(self.value)

    def __str__(self):
        return self.value

    @property
    def value(self):
        return "?"


UNKNOWN = Unknown()


class BibleReferenceError(Exception):
    pass


class BibleSetupError(Exception):
    pass


class _EnumDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        self.enum_classes = {name(enum_class): enum_class for enum_class in kwargs.pop("enum_classes")}
        super().__init__(*args, **kwargs)
        self._parse_string = self.parse_string
        self.parse_string = self.py_scanstring
        self.scan_once = json.scanner.py_make_scanner(self)

    def py_scanstring(self, *args, **kwargs):
        s, i = self._parse_string(*args, **kwargs)
        enum_class_name, sep, rest = s.partition(".")
        enum_class = self.enum_classes.get(enum_class_name)
        if not sep or not enum_class:
            return s, i
        try:
            return getattr(enum_class, rest).value, i
        except AttributeError:
            raise json.decoder.JSONDecodeError(f"{rest} is not a valid enumeration of {enum_class}", s, i)


class Filterable:
    def __init__(self, iterable, dataclass=None, field=None):
        self._iterable = iterable
        self._dataclass = dataclass
        self._fields = self._inspect_fields(self._dataclass)
        self.field = field

    @staticmethod
    def _getattr(i, field):
        if field is None:
            raise BibleReferenceError("the field attribute is not set on the parent object")
        return getattr(i, field)

    @staticmethod
    def _inspect_fields(dataclass):
        if dataclass is None:
            return ()
        fields = (field.name for field in dataclasses.fields(dataclass) if not field.name.startswith("_"))
        properties = (name for name, _ in inspect.getmembers(dataclass, lambda value: isinstance(value, property)))
        return tuple(sorted((*fields, *properties)))

    def __eq__(self, value):
        return type(self)(self._filter(operator.eq, value), self._dataclass, self._field)

    def __ge__(self, value):
        return type(self)(self._filter(operator.ge, value), self._dataclass, self._field)

    def __getattr__(self, name):
        if self._dataclass is not None and name not in self._fields:
            raise AttributeError(f"{name(self._dataclass)!r} object has no attribute {name!r}")
        return type(self)(self._iterable, self._dataclass, name)

    def __gt__(self, value):
        return type(self)(self._filter(operator.gt, value), self._dataclass, self._field)

    def __iter__(self):
        self._iterable, iterable_copy = itertools.tee(self._iterable)
        return iterable_copy

    def __le__(self, value):
        return type(self)(self._filter(operator.le, value), self._dataclass, self._field)

    def __len__(self):
        return sum(1 for _ in self)

    def __lt__(self, value):
        return type(self)(self._filter(operator.lt, value), self._dataclass, self._field)

    def __ne__(self, value):
        return type(self)(self._filter(operator.ne, value), self._dataclass, self._field)

    def __repr__(self):
        return f"{name(type(self))}(field={self._field}, dataclass={name(self._dataclass)}, len={len(self)})"

    def _check_fields(self, fields):
        if not fields:
            if self._field is None:
                raise BibleReferenceError("field is not set")
            fields = (self._field, )
        return fields

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

    def _filter_unary(self, operation):
        for i in self:
            if operation(self._getattr(i, self.field)):
                yield i

    def _limit(self, limit):
        if limit is None:
            return iter(self)
        return itertools.islice(self, limit)

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
        if value is not None and self._dataclass is not None and value not in self._fields:
            raise AttributeError(f"{name(self._dataclass)!r} object has no attribute {value!r}")
        self._field = value

    @property
    def fields(self):
        return self._fields

    def all(self, limit=None):
        yield from self._limit(limit)

    def combine(self, *filterables):
        return type(self)(self._combine(*filterables), self._dataclass, self._field)

    def contains(self, value, inverse=False):
        if not inverse:
            return type(self)(self._contains(value), self._dataclass, self._field)
        return type(self)(self._contains_not(value), self._dataclass, self._field)

    def false(self):
        return type(self)(self._filter_unary(operator.not_), self._dataclass, self._field)

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

    def select(self, *fields, limit=None):
        yield from ({field: getattr(i, field) for field in self._check_fields(fields)} for i in self._limit(limit))

    def true(self):
        return type(self)(self._filter_unary(operator.truth), self._dataclass, self._field)

    def values(self, *fields, limit=None):
        yield from (tuple(getattr(i, field) for field in self._check_fields(fields)) for i in self._limit(limit))

    def where(self, *values, inverse=False):
        if not inverse:
            return type(self)(self._where(*values), self._dataclass, self._field)
        return type(self)(self._where_not(*values), self._dataclass, self._field)


class FuzzyDict(dict):
    _MISSING = object()

    def __init__(self, *args, **kwargs):
        self.ratio_threshold = kwargs.pop("ratio_threshold", 60)
        super().__init__(*args, **kwargs)

    def __getitem__(self, key):
        matched, closest_key, value, closest_ratio = self.search(key)
        if not matched:
            if closest_key is self._MISSING:
                raise KeyError(key)
            raise KeyError(f"'{key}'. The closest match was {closest_key} but with a ratio ({closest_ratio}) < the threshold "
                           f"({self.ratio_threshold})")
        return value

    def search(self, key, return_first=False, ratio_threshold_override=None):
        if key in self:
            return (True, key, super().__getitem__(key), 1)
        if not isinstance(key, str):
            return (False, key, None, 0)
        matched = False
        closest_key = self._MISSING
        closest_ratio = 0
        ratio_threshold = ratio_threshold_override or self.ratio_threshold
        for existing_key in self:
            if not isinstance(existing_key, str):
                continue
            ratio = fuzz.partial_ratio(key, existing_key)
            if ratio > closest_ratio:  # if it's the same, we will favour the one found first; deterministic as python dicts retain order from 3.7
                matched = closest_ratio >= ratio_threshold
                closest_ratio = ratio
                closest_key = existing_key
                if return_first and matched:
                    break
        return (matched, closest_key, self.get(closest_key), closest_ratio)


class Year(int):
    def __repr__(self):
        return repr(self.value)

    def __str__(self):
        return self.value

    @property
    def value(self):
        if self < 0:
            return f"{abs(self)} BC"
        return f"{abs(self)} AD"  # abs() appears extraneous but needed to avoid infinite recursion


def fetch_pattern(cls, group_suffix="_start"):
    name_pattern = getattr(cls, "_NAME_REGEX").pattern
    if group_suffix is not None:
        name_pattern = name_pattern.replace(">", f"{group_suffix}>")
    return name_pattern[1:-1]


def find_data_file_path(adjacent_module_name=__name__):
    module = sys.modules[adjacent_module_name]
    module_directory = os.path.dirname(module.__file__)
    data_json_file_path = os.path.join(module_directory, "data.json")
    return data_json_file_path if os.path.isfile(data_json_file_path) else next(glob.iglob(os.path.join(module_directory, "*.json")), None)


def find_enum_classes(*modules):
    if not modules:
        modules = (enums, )
    for module in modules:
        for _, enum_class in inspect.getmembers(module, lambda value: isinstance(value, enum.EnumMeta)):
            yield enum_class


def int_reference(book_number, chapter_number=1, verse_number=1):
    return f"{book_number:01d}{chapter_number:03d}{verse_number:03d}"


def load_data(file_path, enum_classes):
    with open(file_path) as f:
        return json.load(f, cls=_EnumDecoder, enum_classes=enum_classes)


def load_translation(data_file_path=None, translation_cls=None, book_cls=None, chapter_cls=None, verse_cls=None, passage_cls=None, character_cls=None,
                     enum_classes=()):
    from bible import api  # Avoid circular import
    enum_classes = enum_classes or tuple(find_enum_classes())
    data = base_data = load_data(find_data_file_path(), enum_classes=enum_classes)
    arbitrary_cls = next(filter(None, (translation_cls, book_cls, chapter_cls, verse_cls, passage_cls, character_cls)), None)
    if arbitrary_cls is not None:
        data = jsonmerge.merge(base_data, load_data(data_file_path or find_data_file_path(arbitrary_cls.__module__), enum_classes=enum_classes))
    passage_cls = passage_cls or api.Passage
    character_cls = character_cls or api.Character
    meta_data = data["meta"]
    translation = (translation_cls or api.Translation)(name=meta_data.pop("name"), passage_cls=passage_cls, character_cls=character_cls, **meta_data)
    for book_number, book_data in data.get("books", {}).items():
        chapters = book_data.pop("chapters", {})
        book = (book_cls or api.Book)(number=int(book_number), name=book_data.pop("name"), translation=translation, **book_data)
        for chapter_number, chapter_data in chapters.items():
            verses = chapter_data.pop("verses", {})
            chapter = (chapter_cls or api.Chapter)(number=int(chapter_number), book=book, **chapter_data)
            for verse_number, verse_data in verses.items():
                _ = (verse_cls or api.Verse)(number=int(verse_number), chapter=chapter, **verse_data)
    for character_number, character_data in data.get("characters", {}).items():
        character_data["passages"] = tuple(map(translation.passage, character_data.get("passages", ())))
        character_data["aliases"] = tuple(character_data.pop("aliases", ()))
        character_data["_father"] = safe_int(character_data.pop("father", UNKNOWN))
        character_data["_mother"] = safe_int(character_data.pop("mother", UNKNOWN))
        character_data["_spouses"] = tuple(map(int, character_data.pop("spouses", ())))
        for attribute in ("age", "born", "died"):
            value = character_data.pop(attribute, UNKNOWN)
            if value is not UNKNOWN:
                character_data[attribute] = Year(value)
        _ = character_cls(number=int(character_number), translation=translation, **character_data)
    return translation


def name(obj):
    return obj.__name__


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
