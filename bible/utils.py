import collections
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
import num2words

from bible import enums


DEFAULT_THRESHOLD = 60


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


class FamilyTreeMixin:
    _IRRELEVANT = object()
    FIRST_PREFIX = "(First)"
    RELATION_TYPES = {  # (my_distance, other_distance, gender): (relation_type, is_maternal_relevant)
        (1, 1, enums.CharacterGender.MALE.value): ("Brother", False),
        (1, 1, enums.CharacterGender.FEMALE.value): ("Sister", False),
        (1, 1, UNKNOWN): ("Sibling", False),
        (1, 0, enums.CharacterGender.MALE.value): ("Father", False),
        (1, 0, enums.CharacterGender.FEMALE.value): ("Mother", False),
        (1, 0, UNKNOWN): ("Parent", False),
        (2, 0, enums.CharacterGender.MALE.value): ("Grandfather", True),
        (2, 0, enums.CharacterGender.FEMALE.value): ("Grandmother", True),
        (2, 0, UNKNOWN): ("Grandparent", True),
        (0, 1, enums.CharacterGender.MALE.value): ("Son", False),
        (0, 1, enums.CharacterGender.FEMALE.value): ("Daughter", False),
        (0, 1, UNKNOWN): ("Child", False),
        (0, 2, enums.CharacterGender.MALE.value): ("Grandson", False),
        (0, 2, enums.CharacterGender.FEMALE.value): ("Granddaughter", False),
        (0, 2, UNKNOWN): ("Grandchild", False),
        (2, 1, enums.CharacterGender.MALE.value): ("Uncle", True),
        (2, 1, enums.CharacterGender.FEMALE.value): ("Aunt", True),
        (2, 1, UNKNOWN): ("Uncle/Aunt", True),
        (3, 1, enums.CharacterGender.MALE.value): ("Granduncle", True),
        (3, 1, enums.CharacterGender.FEMALE.value): ("Grandaunt", True),
        (3, 1, UNKNOWN): ("Granduncle/Grandaunt", True),
        (1, 2, enums.CharacterGender.MALE.value): ("Nephew", False),
        (1, 2, enums.CharacterGender.FEMALE.value): ("Niece", False),
        (1, 2, UNKNOWN): ("Nephew/Niece", False),
        (1, 3, enums.CharacterGender.MALE.value): ("Grandnephew", False),
        (1, 3, enums.CharacterGender.FEMALE.value): ("Grandniece", False),
        (1, 3, UNKNOWN): ("Grandnephew/Grandniece", False),
        (2, 2, enums.CharacterGender.MALE.value): (f"{FIRST_PREFIX} Cousin (Male)", True),
        (2, 2, enums.CharacterGender.FEMALE.value): (f"{FIRST_PREFIX} Cousin (Female)", True),
        (2, 2, UNKNOWN): (f"{FIRST_PREFIX} Cousin", True)
    }
    _ancestor_set = collections.namedtuple("AncestorSet", ("male", "female"), defaults=(_IRRELEVANT, _IRRELEVANT))

    @staticmethod
    def _add_next_ancestors(my_ancestors, my_next_ancestors, other_ancestors, other_next_ancestors, gen):
        for ancestors, next_ancestors in ((my_ancestors, my_next_ancestors), (other_ancestors, other_next_ancestors)):
            for next_ancestor_set, is_maternal_relevant in next_ancestors:
                male, female = next_ancestor_set
                ancestor_data = [(next_ancestor_set, is_maternal_relevant, gen)]
                if male:
                    ancestors[male] = iter(list(ancestors.get(male, ())) + ancestor_data)
                if female:
                    ancestors[female] = iter(list(ancestors.get(female, ())) + ancestor_data)

    @staticmethod
    def _format_relatedness(lower, upper):
        return f"{lower:.2%}" + (f"-{upper:.2%}" if upper != lower else "")

    @classmethod
    def _process_next_ancestors(cls, lowest_common_ancestors, my_ancestors, my_next_ancestors, other_ancestors, other_next_ancestors, gen):
        default_value = [((None, None), None, None)]
        for opposite_ancestors, next_ancestors, distance_index, opposite_distance_index in ((other_ancestors, my_next_ancestors, 0, 1),
                                                                                                (my_ancestors, other_next_ancestors, 1, 0)):
            found = False
            for index, (next_ancestor_set, is_maternal_relation) in enumerate(next_ancestors):
                distances = [0, 0]  # [my_distance, other_distance]
                male, female = next_ancestor_set
                opposite_ancestor_details = opposite_ancestors.get(male, opposite_ancestors.get(female, iter(default_value)))
                n = next(opposite_ancestor_details)
                opposite_next_ancestor_set, opposite_is_maternal_relation, opposite_distance = n
                opposite_male, opposite_female = opposite_next_ancestor_set
                if opposite_distance is None:
                    continue
                found = True
                my_is_maternal_relation = is_maternal_relation if next_ancestors is my_next_ancestors else opposite_is_maternal_relation
                common_male = male and male is opposite_male
                common_female = female and female is opposite_female
                common_ancestors = set(filter(None, next_ancestor_set)).intersection(opposite_next_ancestor_set)
                distances[distance_index] = gen
                distances[opposite_distance_index] = opposite_distance
                if (common_male and common_female) or cls._IRRELEVANT in opposite_next_ancestor_set:
                    is_half = False
                elif UNKNOWN in next_ancestor_set or UNKNOWN in opposite_next_ancestor_set:
                    is_half = UNKNOWN
                else:
                    is_half = True
                lowest_common_ancestors.append((list(common_ancestors), is_half, my_is_maternal_relation, *distances))
                # Stop traversing family tree for found common ancestors by updating ancestor set
                next_ancestors[index] = (cls._ancestor_set(male=None if common_male else male, female=None if common_female else female),
                                         is_maternal_relation)
            if found:
                # If we have matched from one side, we don't need to look on the other side
                return

    def _lowest_common_ancestors(self, other):
        lowest_common_ancestors = []
        gen = 0
        my_ancestors = {self: iter([(self._ancestor_set(**{self.gender.lower(): self}), self._IRRELEVANT, gen)])}
        other_ancestors = {other: iter([(self._ancestor_set(**{other.gender.lower(): other}), self._IRRELEVANT, gen)])}
        my_next_ancestors = [(self._ancestor_set(male=self.father, female=self.mother), self._IRRELEVANT)] if self.parents else []
        other_next_ancestors = [(self._ancestor_set(male=other.father, female=other.mother), self._IRRELEVANT)] if other.parents else []
        while my_next_ancestors or other_next_ancestors:
            gen += 1
            self._add_next_ancestors(my_ancestors, my_next_ancestors, other_ancestors, other_next_ancestors, gen)
            self._process_next_ancestors(lowest_common_ancestors, my_ancestors, my_next_ancestors, other_ancestors, other_next_ancestors, gen)
            for next_ancestors in (my_next_ancestors, other_next_ancestors):
                next_ancestors[:] = [(self._ancestor_set(next_ancestor.father, next_ancestor.mother),
                                          next_ancestor.gender == enums.CharacterGender.FEMALE.value if is_maternal_relation is self._IRRELEVANT
                                          else is_maternal_relation)
                                         for next_ancestor_set, is_maternal_relation in next_ancestors
                                         for next_ancestor in next_ancestor_set
                                         if next_ancestor and next_ancestor.parents]
        return lowest_common_ancestors  # [[common_ancestors], is_half, is_maternal_relation, my_distance, other_distance]

    def relation(self, other):  # Doesn't support identical twins
        connection_template = {"type": None, "relatedness": None, "lowest_common_ancestors": None}
        connections = []
        blood_relations = {"connections": connections, "total_relatedness": None}
        relations_data = {"blood": blood_relations, "marital": {"in-law": None, "step": None}}
        total_relatedness_lower = total_relatedness_upper = 0
        for lowest_common_ancestor_set, is_half, is_maternal_relation, my_distance, other_distance in self._lowest_common_ancestors(other):
            connection = connection_template.copy()
            relation_type, is_maternal_relevant = self.RELATION_TYPES.get((my_distance, other_distance, other.gender), (None, None))
            if relation_type is None:
                difference = abs(my_distance - other_distance)
                if min(my_distance, other_distance) <= 1:  # Great Relative
                    if my_distance == 0:  # Grandchild's Descendent
                        partial_relation_type, is_maternal_relevant = self.RELATION_TYPES[(0, 2, other.gender)]
                    elif other_distance == 0:  # Grandparent's Ancestor
                        partial_relation_type, is_maternal_relevant = self.RELATION_TYPES[(2, 0, other.gender)]
                    elif my_distance == 1:  # Grandnephew/Grandniece's Descendent
                        partial_relation_type, is_maternal_relevant = self.RELATION_TYPES[(1, 3, other.gender)]
                    elif other_distance == 1:  # Ancestor's Aunt/Uncle
                        partial_relation_type, is_maternal_relevant = self.RELATION_TYPES[(3, 1, other.gender)]
                    relation_type = "Great-" + ("great-" * (difference - 3)) + partial_relation_type.lower()
                else:  # Cousin
                    prefix = num2words.num2words(min(my_distance, other_distance) - 2, to="ordinal").capitalize()
                    suffix = ""
                    if difference:
                        degrees_removed = {1: "once", 2: "twice", 3: "thrice"}.get(difference, f"{num2words.num2words(difference)} times")
                        suffix = f" {degrees_removed} removed ({'later' if my_distance > other_distance else 'earlier'} generation)"
                    partial_relation_type, is_maternal_relevant = self.RELATION_TYPES[(2, 2, other.gender)]
                    relation_type = partial_relation_type.lower().replace(self.FIRST_PREFIX, prefix) + suffix
            maternal_prefix = "Maternal " if is_maternal_relation else "Paternal "
            relation_type = f"{maternal_prefix if is_maternal_relevant else ''}{'Half ' if is_half else ''}{relation_type}"
            connection["type"] = relation_type
            connection["lowest_common_ancestors"] = lowest_common_ancestor_set
            relatedness_component = 0.5 ** (my_distance + other_distance)
            relatedness_lower = sum(relatedness_component for _ in lowest_common_ancestor_set)
            total_relatedness_lower += relatedness_lower
            relatedness_upper = relatedness_lower * (2 if is_half is UNKNOWN else 1)
            total_relatedness_upper += relatedness_upper
            connection["relatedness"] = self._format_relatedness(relatedness_lower, relatedness_upper)
            connections.append(connection)
        blood_relations["total_relatedness"] = self._format_relatedness(total_relatedness_lower, total_relatedness_upper)
        return relations_data
        # in-law - also, don't forget special case of wife!
        # step


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
            if value in self._getattr(i, self._field):
                yield i

    def _contains_not(self, value):
        for i in self:
            if value not in self._getattr(i, self._field):
                yield i

    def _filter(self, operation, value):
        for i in self:
            if operation(self._getattr(i, self._field), value):
                yield i

    def _filter_unary(self, operation):
        for i in self:
            if operation(self._getattr(i, self._field)):
                yield i

    def _like(self, *values, threshold):
        for i in self:
            field_value = self._getattr(i, self._field)
            for value in values:
                if safe_ratio(field_value, value) >= threshold:
                    yield i
                    break

    def _like_not(self, *values, threshold):
        for i in self:
            field_value = self._getattr(i, self._field)
            for value in values:
                if safe_ratio(field_value, value) >= threshold:
                    break
            else:
                yield i

    def _limit(self, limit):
        if limit is None:
            return iter(self)
        return itertools.islice(self, limit)

    def _any(self, *values):
        for i in self:
            if self._getattr(i, self._field) in values:
                yield i

    def _any_not(self, *values):
        for i in self:
            if self._getattr(i, self._field) not in values:
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

    def any(self, *values, not_=False):
        if not not_:
            return type(self)(self._any(*values), self._dataclass, self._field)
        return type(self)(self._any_not(*values), self._dataclass, self._field)

    def combine(self, *filterables):
        return type(self)(self._combine(*filterables), self._dataclass, self._field)

    def contains(self, value, not_=False):
        if not not_:
            return type(self)(self._contains(value), self._dataclass, self._field)
        return type(self)(self._contains_not(value), self._dataclass, self._field)

    def false(self):
        return type(self)(self._filter_unary(operator.not_), self._dataclass, self._field)

    def like(self, *values, not_=False, threshold=DEFAULT_THRESHOLD):
        if not not_:
            return type(self)(self._like(*values, threshold=threshold), self._dataclass, self._field)
        return type(self)(self._like_not(*values, threshold=threshold), self._dataclass, self._field)

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
        yield from ({field: self._getattr(i, field) for field in self._check_fields(fields)} for i in self._limit(limit))

    def true(self):
        return type(self)(self._filter_unary(operator.truth), self._dataclass, self._field)

    def values(self, field=None, limit=None):
        return tuple(self._getattr(i, field or self._field) for i in self._limit(limit))


class FuzzyDict(dict):
    _MISSING = object()

    def __init__(self, *args, **kwargs):
        self.threshold = kwargs.pop("threshold", DEFAULT_THRESHOLD)
        super().__init__(*args, **kwargs)

    def __getitem__(self, key):
        matched, closest_key, value, closest_ratio = self.search(key)
        if not matched:
            if closest_key is self._MISSING:
                raise KeyError(key)
            raise KeyError(f"'{key}'. The closest match was {closest_key} but with a ratio ({closest_ratio}) < the threshold "
                           f"({self.threshold})")
        return value

    def search(self, key, return_first=False, threshold=None):
        value = self.get(key, self._MISSING)
        if value is not self._MISSING:
            return (True, key, super().__getitem__(key), 1)
        matched = False
        closest_key = self._MISSING
        closest_ratio = 0
        threshold = threshold or self.threshold
        for existing_key in self:
            ratio = safe_ratio(key, existing_key)
            if ratio > closest_ratio:
                matched = ratio >= threshold
                closest_ratio = ratio
                closest_key = existing_key
                if matched and return_first:
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


def safe_ratio(s1, s2):
    ratio = 0
    try:
        ratio = fuzz.ratio(s1, s2)
    except TypeError:
        pass
    return ratio


def slugify(value):
    try:
        return value.replace(" ", "").upper()  # we don't expect any strange characters in book names
    except AttributeError:
        return value


def unique_value_iterating_dict(d):
    yield from dict.fromkeys(d.values())
