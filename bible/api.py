import collections
import dataclasses
import graphviz
import regex as re  # we need variable-width lookbehind assertions
import typing

from bible import enums, utils


_range = "(?P<range>-)?"


class _Characters(utils.Filterable):
    def __getitem__(self, key):
        character = (self.number == key).one()
        if character is None:
            highest_ratio = utils.DEFAULT_THRESHOLD - 1
            most_verses = 0
            for potential_character in self:
                ratio = utils.safe_ratio(key, potential_character.name)
                if ratio < highest_ratio:
                    continue
                total_verses = sum(map(len, potential_character.passages))
                if ratio == highest_ratio and total_verses <= most_verses:
                    continue
                highest_ratio = ratio
                most_verses = total_verses
                character = potential_character
            if character is None:
                raise KeyError(key)
        return character

    def lineage(self, ancestor, descendant):
        return self.combine(self.number == ancestor.number, self.ancestors.contains(ancestor).descendants.contains(descendant),
                            self.number == descendant.number)

    def tree(self, directory=f".tmp/{__name__}", view=True):  # WIP
        dot = graphviz.Digraph(comment="Genealogy")
        relationships = []
        for character in self:
            dot.node(str(character.number), f"{character.name} ({character.born} - {character.died})")
            for parent in (character.mother, character.father):
                if parent is not utils.UNKNOWN:
                    relationships.append((str(parent.number), str(character.number)))
        dot.edges(relationships)
        dot.render(directory=directory, view=view, cleanup=True, format="png", quiet=True, quiet_view=True)


class Verse:
    _NAME_REGEX = re.compile(r"^(?P<verse_number>\d+)$")

    def __init__(self, number, chapter):
        self._number = number
        self._chapter = chapter
        self._book = self._chapter.book
        self._translation = self._book.translation
        chapter._register_verse(self)

    def __repr__(self):
        return (f"{utils.name(type(self))}(number={self._number}, chapter={self._chapter.number}, book={self._book.name}, "
                f"translation={self._translation.name})")

    def __str__(self):
        return utils.reference(self._book.name, self._chapter.number, self._number)

    def _characters(self):
        int_reference = int(self.int_reference)
        for character in self._translation.characters().all():
            for passage in character.passages:
                passage_int_reference_start, passage_int_reference_end = passage.int_reference.split(" - ")
                if int(passage_int_reference_start) <= int_reference <= int(passage_int_reference_end):
                    yield character
                    break

    @property
    def book(self):
        return self._book

    @property
    def chapter(self):
        return self._chapter

    @property
    def is_first(self):
        return self._number == 1

    @property
    def is_last(self):
        return self._number == len(self._chapter)

    @property
    def number(self):
        return self._number

    @property
    def int_reference(self):
        return utils.int_reference(self._book.number, self._chapter.number, self._number)

    @property
    def translation(self):
        return self._translation

    def audio(self):
        raise NotImplementedError()

    def characters(self, field=None):
        return _Characters(self._characters(), Character, field)

    def next(self, overspill=True):
        if self.is_last:
            if overspill:
                next_chapter = self._chapter.next()
                if next_chapter is not None:
                    return next_chapter.first()
            return None
        return self._chapter[self._number + 1]

    def previous(self, overspill=True):
        if self.is_last:
            if overspill:
                previous_chapter = self._chapter.previous()
                if previous_chapter is not None:
                    return previous_chapter.last()
            return None
        return self._chapter[self._number - 1]

    def text(self):
        raise NotImplementedError()


class Chapter:
    _NAME_REGEX = re.compile(r"^(?P<chapter_number>\d+)$")
    _PASSAGE_REGEX = re.compile(f"^{utils.fetch_pattern(Verse)}?{_range}{utils.fetch_pattern(Verse, '_end')}?$", flags=re.ASCII | re.IGNORECASE)

    def __init__(self, number, book):
        self._number = number
        self._book = book
        self._translation = self._book.translation
        self._verses = {}
        book._register_chapter(self)

    def __contains__(self, item):
        return item in self._verses.values()

    def __getitem__(self, key):
        try:
            return self._verses[key]
        except KeyError:
            raise utils.BibleReferenceError(f"{key} is not a valid number between {str(self.first())} and {str(self.last())}")

    def __iter__(self):
        return utils.unique_value_iterating_dict(self._verses)

    def __len__(self):
        return len(self._verses)

    def __repr__(self):
        return f"{utils.name(type(self))}(number={self._number}, book={self._book.name}, translation={self._translation.name})"

    def __str__(self):
        return utils.reference(self._book.name, self._number)

    def _characters(self):
        int_reference_0 = int(utils.int_reference(self._book.number, self._number, 0))
        for character in self._translation.characters().all():
            for passage in character.passages:
                if (
                    int(utils.int_reference(passage.book_start.number, passage.chapter_start.number, 0)) <=
                    int_reference_0 <=
                    int(utils.int_reference(passage.book_end.number, passage.chapter_end.number, 0))
                   ):
                    yield character
                    break

    def _register_verse(self, verse):
        if verse.number in self._verses:
            raise utils.BibleSetupError(f"a verse is already registered in this chapter ({self}) with the number, {verse.number}")
        self._verses[verse.number] = verse

    @property
    def book(self):
        return self._book

    @property
    def int_reference(self):
        return utils.int_reference(self._book.number, self._number)

    @property
    def is_first(self):
        return self._number == 1

    @property
    def is_last(self):
        return self._number == len(self._book)

    @property
    def number(self):
        return self._number

    @property
    def translation(self):
        return self._translation

    def audio(self):
        raise NotImplementedError()

    def characters(self, field=None):
        return _Characters(self._characters(), self._translation.Character, field)

    def first(self):
        return self[1]

    def last(self):
        return self[len(self)]

    def next(self, overspill=True):
        if self.is_last:
            if overspill:
                next_book = self._book.next()
                if next_book is not None:
                    return next_book.first()
            return None
        return self._book[self._number + 1]

    def passage(self, reference="-"):
        match = self._PASSAGE_REGEX.match(reference)
        if match is None:
            raise utils.BibleReferenceError(f"the reference, '{reference}' does not match the expected regex, {self._PASSAGE_REGEX}")
        groups = match.groupdict()
        verse_start = self[utils.safe_int(groups["verse_number_start"]) or 1]
        if groups["range"] is None:
            verse_end = verse_start
        else:
            verse_end = self[utils.safe_int(groups["verse_number_end"]) or len(self)]
        if int(verse_end.int_reference) < int(verse_start.int_reference):
            raise utils.BibleReferenceError("the requested passage range is invalid; the right hand side of the range must be greater than the left")
        return self._translation.Passage(self._book, self, verse_start, self._book, self, verse_end)

    def previous(self, overspill=True):
        if self.is_last:
            if overspill:
                previous_book = self._book.previous()
                if previous_book is not None:
                    return previous_book.last()
            return None
        return self._book[self._number - 1]

    def text(self):
        raise NotImplementedError()

    def verses(self):
        yield from self._verses.values()


class Book:
    _NAME_REGEX = re.compile(r"^(?P<book_name>(?:\d{1})?[A-Z]+)$", flags=re.ASCII | re.IGNORECASE)
    _PASSAGE_REGEX = re.compile(fr"^{utils.fetch_pattern(Chapter)}?:?{utils.fetch_pattern(Verse)}?{_range}"
                                fr"(?P<chapter_number_end>(?<!:.*-)\d+|(?=\d*:)\d+)?:?{utils.fetch_pattern(Verse, '_end')}?$",
                                flags=re.ASCII | re.IGNORECASE)

    def __init__(self, number, name, translation, alt_names=(), author=None, categories=(), language=None):
        self._number = number
        id_ = utils.slugify(name)
        if not self._NAME_REGEX.match(id_):
            raise utils.BibleSetupError(f"the derived id, '{id_}' does not match the expected regex, {self._NAME_REGEX}")
        self._id = id_
        self._name = name
        self._translation = translation
        self._alt_ids = tuple(sorted(map(utils.slugify, alt_names)))
        self._alt_names = tuple(sorted(alt_names))
        self._author = author
        self._categories = tuple(sorted(categories))
        self._language = language
        self._chapters = {}
        translation._register_book(self)

    def __contains__(self, item):
        return item in self._chapters.values()

    def __getitem__(self, key):
        try:
            return self._chapters[key]
        except KeyError:
            raise utils.BibleReferenceError(f"{key} is not a valid number between {str(self.first())} and {str(self.last())}")

    def __iter__(self):
        return utils.unique_value_iterating_dict(self._chapters)

    def __len__(self):
        return len(self._chapters)

    def __repr__(self):
        return f"{utils.name(type(self))}(name={self._name}, number={self._number}, translation={self._translation.name})"

    def __str__(self):
        return utils.reference(self._name)

    def _characters(self):
        int_reference_0 = int(utils.int_reference(self._number, 0, 0))
        for character in self._translation.characters().all():
            for passage in character.passages:
                if (
                    int(utils.int_reference(passage.book_start.number, 0, 0)) <=
                    int_reference_0 <=
                    int(utils.int_reference(passage.book_end.number, 0, 0))
                   ):
                    yield character
                    break

    def _register_chapter(self, chapter):
        if chapter.number in self._chapters:
            raise utils.BibleSetupError(f"a chapter is already registered in this book ({self}) with the number, {chapter.number}")
        self._chapters[chapter.number] = chapter

    @property
    def alt_ids(self):
        return self._alt_ids

    @property
    def alt_names(self):
        return self._alt_names

    @property
    def author(self):
        return self._author

    @property
    def categories(self):
        return self._categories

    @property
    def id(self):
        return self._id

    @property
    def int_reference(self):
        return utils.int_reference(self._book.number)

    @property
    def is_first(self):
        return self._number == 1

    @property
    def is_last(self):
        return self._number == len(self._translation)

    @property
    def language(self):
        return self._language

    @property
    def name(self):
        return self._name

    @property
    def number(self):
        return self._number

    @property
    def translation(self):
        return self._translation

    def audio(self):
        raise NotImplementedError()

    def chapters(self):
        yield from self._chapters.values()

    def characters(self, field=None):
        return _Characters(self._characters(), self._translation.Character, field)

    def first(self):
        return self[1]

    def last(self):
        return self[len(self)]

    def next(self):
        if self.is_last:
            return None
        return self._translation[self._number + 1]

    def passage(self, reference="-"):
        match = self._PASSAGE_REGEX.match(reference)
        if match is None:
            raise utils.BibleReferenceError(f"the reference, '{reference}' does not match the expected regex, {self._PASSAGE_REGEX}")
        groups = match.groupdict()
        chapter_number_start = utils.safe_int(groups["chapter_number_start"])
        chapter_start = self[chapter_number_start or 1]
        verse_number_start = utils.safe_int(groups["verse_number_start"])
        verse_start = chapter_start[verse_number_start or 1]
        if groups["range"] is None:
            chapter_end = chapter_start
            verse_end = verse_start
        else:
            verse_number_end = utils.safe_int(groups["verse_number_end"])
            chapter_end = self[utils.safe_int(groups["chapter_number_end"]) or (chapter_number_start if verse_number_end else len(self))]
            verse_end = chapter_end[verse_number_end or len(chapter_end)]
        if int(verse_end.int_reference) < int(verse_start.int_reference):
            raise utils.BibleReferenceError("the requested passage range is invalid; the right hand side of the range must be greater than the left")
        return self._translation.Passage(self, chapter_start, verse_start, self, chapter_end, verse_end)

    def previous(self):
        if self.is_first:
            return None
        return self._translation[self._number - 1]

    def text(self):
        raise NotImplementedError()

    def verses(self):
        next_verse = self.first().first()
        verse_end_int_reference = int(self.last().last().int_reference)
        while next_verse is not None and int(next_verse.int_reference) <= verse_end_int_reference:
            yield next_verse
            next_verse = next_verse.next()


class Translation:
    _INT_PASSAGE_REGEX = re.compile(fr"^(?:(?P<book_number_start>\d{{1,2}})(?P<chapter_number_start>\d{{3}})(?P<verse_number_start>\d{{3}}))?{_range}"
                                    r"(?:(?P<book_number_end>\d{1,2})(?P<chapter_number_end>\d{3})(?P<verse_number_end>\d{3}))?$")
    _PASSAGE_REGEX = re.compile(fr"^{utils.fetch_pattern(Book)}?{utils.fetch_pattern(Chapter)}?:?{utils.fetch_pattern(Verse)}?{_range}"
                                fr"{utils.fetch_pattern(Book, '_end')}?(?P<chapter_number_end>(?<!:.*-)\d+|(?=\d*:)\d+)?:?"
                                fr"{utils.fetch_pattern(Verse, '_end')}?$", flags=re.ASCII | re.IGNORECASE)

    def __init__(self, name, passage_cls, character_cls):
        self._name = name
        self._passage_cls = passage_cls
        self._character_cls = character_cls
        self._books = utils.FuzzyDict()
        self._categories = utils.FuzzyDict()
        self._characters = {}

    def __contains__(self, item):
        return item in set(self._books.values())

    def __getitem__(self, key):
        try:
            return self._books[utils.slugify(key)]
        except KeyError:
            raise utils.BibleReferenceError(f"{key} cannot be found")

    def __iter__(self):
        return utils.unique_value_iterating_dict(self._books)

    def __len__(self):
        return len(set(self._books.values()))

    def __repr__(self):
        return f"{utils.name(type(self))}(name={self._name})"

    def _register_book(self, book):
        book_ids = (book.number, book.id, *book.alt_ids)
        existing_book_ids = [book_id for book_id in book_ids if book_id in self._books]
        if existing_book_ids:
            raise utils.BibleSetupError(f"a book is already registered in this translation ({self}) with the id(s), {','.join(existing_book_ids)}")
        self._books.update(dict.fromkeys(book_ids, book))
        for category in book.categories:
            existing_category = self._categories.get(category, ())
            self._categories[category] = existing_category + (book, )

    def _register_character(self, character):
        if character.number in self._characters:
            raise utils.BibleSetupError(f"a character is already registered in this translation ({self}) with the number, {character.number}")
        self._characters[character.number] = character

    @property
    def categories(self):
        return self._categories

    @property
    def Character(self):
        return self._character_cls

    @property
    def name(self):
        return self._name

    @property
    def Passage(self):
        return self._passage_cls

    def books(self):
        yield from utils.unique_value_iterating_dict(self._books)

    def characters(self, field=None):
        return _Characters(self._characters.values(), self.Character, field)

    def first(self):
        return self[1]

    def last(self):
        return self[len(self)]

    def passage(self, reference=None, int_reference=None):
        if reference is not None:
            if int_reference is not None:
                raise ValueError("reference and int_reference are mutually exclusive arguments; only 1 should be not None")
            match = self._PASSAGE_REGEX.match(utils.slugify(reference))
            if match is None:
                raise utils.BibleReferenceError(f"the reference, '{reference}' does not match the expected regex, {self._PASSAGE_REGEX}")
            book_start_group = "book_name_start"
            book_end_group = "book_name_end"
        else:
            if int_reference is None:
                raise ValueError("either reference or int_reference must be not None")
            match = self._INT_PASSAGE_REGEX.match(utils.slugify(int_reference))
            if match is None:
                raise utils.BibleReferenceError(f"the int_reference, {int_reference} does not match the expected regex, {self._INT_PASSAGE_REGEX}")
            book_start_group = "book_number_start"
            book_end_group = "book_number_end"
        groups = match.groupdict()
        book_start_identifier = utils.safe_int(groups[book_start_group])
        book_start = self._books[book_start_identifier or 1]
        chapter_number_start = utils.safe_int(groups["chapter_number_start"])
        chapter_start = book_start[chapter_number_start or 1]
        verse_start = chapter_start[utils.safe_int(groups["verse_number_start"]) or 1]
        if groups["range"] is None:
            book_end = book_start
            chapter_end = chapter_start
            verse_end = verse_start
        else:
            chapter_number_end = utils.safe_int(groups["chapter_number_end"])
            verse_number_end = utils.safe_int(groups["verse_number_end"])
            book_end = self._books[utils.safe_int(groups[book_end_group]) or
                                   (book_start_identifier if (chapter_number_end or verse_number_end) else len(self))]
            chapter_end = book_end[chapter_number_end or (chapter_number_start if verse_number_end else len(book_end))]
            verse_end = chapter_end[verse_number_end or len(chapter_end)]
        if int(verse_end.int_reference) < int(verse_start.int_reference):
            raise utils.BibleReferenceError("the requested passage range is invalid; the right hand side of the range must be greater than the left")
        return self.Passage(book_start, chapter_start, verse_start, book_end, chapter_end, verse_end)


class Passage:
    def __init__(self, book_start, chapter_start, verse_start, book_end, chapter_end, verse_end):
        self._book_start = book_start
        self._chapter_start = chapter_start
        self._verse_start = verse_start
        self._book_end = book_end
        self._chapter_end = chapter_end
        self._verse_end = verse_end
        self._translation = self._book_start.translation

    def __len__(self):
        return sum(1 for _ in self.verses())

    def __repr__(self):
        return (f"{utils.name(type(self))}(book_start={self._book_start.name}, chapter_start={self._chapter_start.number}, "
                f"verse_start={self._verse_start.number}, book_end={self._book_end.name}, chapter_end={self._chapter_end.number}, "
                f"verse_end={self._verse_end.number})")

    def __str__(self):
        return (f"{utils.reference(self._book_start.name, self._chapter_start.number, self._verse_start.number)} - "
                f"{utils.reference(self._book_end.name, self._chapter_end.number, self._verse_end.number)}")

    def _characters(self):
        int_reference_start, int_reference_end = self.int_reference.split(" - ")
        for character in self._translation.characters().all():
            for passage in character.passages:
                passage_int_reference_start, passage_int_reference_end = passage.int_reference.split(" - ")
                if (
                    int(passage_int_reference_start) <= int(int_reference_start) <= int(passage_int_reference_end)
                    or
                    int(passage_int_reference_start) <= int(int_reference_end) <= int(passage_int_reference_end)
                ):
                    yield character
                    break

    @property
    def book_end(self):
        return self._book_end

    @property
    def book_start(self):
        return self._book_start

    @property
    def chapter_end(self):
        return self._chapter_end

    @property
    def chapter_start(self):
        return self._chapter_start

    @property
    def int_reference(self):
        return (f"{self._verse_start.int_reference} - {self._verse_end.int_reference}")

    @property
    def translation(self):
        return self._translation

    @property
    def verse_end(self):
        return self._verse_end

    @property
    def verse_start(self):
        return self._verse_start

    def audio(self):
        raise NotImplementedError()

    def books(self):
        next_book = self._book_start
        book_end_int_reference = int(self._book_end.int_reference)
        while next_book is not None and int(next_book.int_reference) <= book_end_int_reference:
            yield next_book
            next_book = next_book.next()

    def chapters(self):
        next_chapter = self._chapter_start
        chapter_end_int_reference = int(self._chapter_end.int_reference)
        while next_chapter is not None and int(next_chapter.int_reference) <= chapter_end_int_reference:
            yield next_chapter
            next_chapter = next_chapter.next()

    def characters(self, field=None):
        return _Characters(self._characters(), self._translation.Character, field)

    def text(self):
        raise NotImplementedError()

    def verses(self):
        next_verse = self._verse_start
        verse_end_int_reference = int(self._verse_end.int_reference)
        while next_verse is not None and int(next_verse.int_reference) <= verse_end_int_reference:
            yield next_verse
            next_verse = next_verse.next()


@dataclasses.dataclass(frozen=True)
class Character(utils.FamilyTreeMixin):
    number: int
    translation: Translation
    passages: tuple[Passage]
    _mother: typing.Union[utils.Unknown, int] = utils.UNKNOWN
    _father: typing.Union[utils.Unknown, int] = utils.UNKNOWN
    _spouses: tuple = dataclasses.field(default_factory=tuple)
    age: typing.Union[utils.Unknown, int] = utils.UNKNOWN
    aliases: tuple = dataclasses.field(default_factory=tuple)
    born: typing.Union[utils.Unknown, utils.Year] = utils.UNKNOWN
    cause_of_death: typing.Union[utils.Unknown, str] = utils.UNKNOWN
    died: typing.Union[utils.Unknown, utils.Year] = utils.UNKNOWN
    gender: typing.Union[utils.Unknown, str] = utils.UNKNOWN
    name: typing.Union[utils.Unknown, str] = utils.UNKNOWN
    nationality: typing.Union[utils.Unknown, str] = utils.UNKNOWN
    place_of_death: typing.Union[utils.Unknown, str] = utils.UNKNOWN
    primary_occupation: typing.Union[utils.Unknown, str] = utils.UNKNOWN
    _children: list = dataclasses.field(default_factory=list, hash=False)

    def __post_init__(self):
        for parent in self.parents:
            parent._children.append(self)
        self.translation._register_character(self)

    def __repr__(self):
        return f"{utils.name(type(self))}(number={self.number}, name={self.name}, gender={self.gender}, born={self.born})"

    @property
    def ancestors(self):
        next_ancestors = collections.deque(self.parents)
        while next_ancestors:
            next_ancestor = next_ancestors.popleft()
            yield next_ancestor
            next_ancestors.extend(next_ancestor.parents)

    @property
    def brothers(self):
        return tuple(sibling for sibling in self.siblings if sibling.gender == enums.CharacterGender.MALE.value)

    @property
    def children(self):
        return tuple(self._children)

    @property
    def daughters(self):
        return tuple(child for child in self.children if child.female)

    @property
    def descendants(self):
        next_descendants = collections.deque(self.children)
        while next_descendants:
            next_descendant = next_descendants.popleft()
            yield next_descendant
            next_descendants.extend(next_descendant.children)

    @property
    def female(self):
        return self.gender == enums.CharacterGender.FEMALE.value

    @property
    def husbands(self):
        return tuple(spouse for spouse in self.spouses if spouse.gender == enums.CharacterGender.MALE.value)

    @property
    def male(self):
        return self.gender == enums.CharacterGender.MALE.value

    @property
    def mother(self):
        return self.translation._characters.get(self._mother, utils.UNKNOWN)

    @property
    def father(self):
        return self.translation._characters.get(self._father, utils.UNKNOWN)

    @property
    def parents(self):
        return tuple(filter(None, (self.mother, self.father)))

    @property
    def siblings(self):
        return tuple(set(child for parent in self.parents for child in parent.children if child is not self))

    @property
    def sisters(self):
        return tuple(sibling for sibling in self.siblings if sibling.gender == enums.CharacterGender.FEMALE.value)

    @property
    def sons(self):
        return tuple(child for child in self.children if child.male)

    @property
    def spouses(self):
        return tuple(self.translation._characters[spouse] for spouse in self._spouses)

    @property
    def wives(self):
        return tuple(spouse for spouse in self.spouses if spouse.gender == enums.CharacterGender.FEMALE.value)
