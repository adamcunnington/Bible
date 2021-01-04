import regex as re  # we need variable-width lookbehind assertions

from bible import utils


_range = "(?P<range>-)?"


def _extract_pattern(cls, group_suffix="_start"):
    name_pattern = getattr(cls, "_NAME_REGEX").pattern
    if group_suffix is not None:
        name_pattern = name_pattern.replace(">", f"{group_suffix}>")
    return name_pattern[1:-1]


def _int(value):
    str_value = str(value)
    return int(str_value) if str_value.isdigit() else value


def _int_reference(book_number, chapter_number=1, verse_number=1):
    return int(f"{book_number:01d}{chapter_number:03d}{verse_number:03d}")


def _name_to_id(value):
    try:
        return value.replace(" ", "").upper()
    except AttributeError:
        return value


def _reference(book_name, chapter_number=None, verse_number=None):
    return f"{book_name}{(f' {chapter_number}') if chapter_number else ''}{(f':{verse_number}') if verse_number else ''}"


class BibleReferenceError(Exception):
    pass


class BibleSetupError(Exception):
    pass


class Verse(object):
    _NAME_REGEX = re.compile(r"^(?P<verse_number>\d+)$")

    def __init__(self, number, chapter):
        self._number = number
        chapter._register_verse(self)
        self._chapter = chapter
        self._book = self.chapter.book
        self._translation = self.book.translation

    def __int__(self):
        return _int_reference(self.book.number, self.chapter.number, self.number)

    def __repr__(self):
        return (f"{self.__class__.__module__}.{self.__class__.__name__}(number={self.number}, chapter={self.chapter.number}, "
                f"book={self.book.name}, translation={self.translation.name})")

    def __str__(self):
        return _reference(self.book.name, self.chapter.number, self.number)

    @property
    def book(self):
        return self._book

    @property
    def chapter(self):
        return self._chapter

    @property
    def is_first(self):
        return self.number == 1

    @property
    def is_last(self):
        return self.number == len(self.chapter)

    @property
    def number(self):
        return self._number

    @property
    def translation(self):
        return self._translation

    def audio(self):
        raise NotImplementedError()

    def next(self, overspill=True):
        if self.is_last:
            if overspill:
                next_chapter = self.chapter.next()
                if next_chapter is not None:
                    return next_chapter[1]
            return None
        return self.chapter[self.number + 1]

    def previous(self, overspill=True):
        if self.is_last:
            if overspill:
                previous_chapter = self.chapter.previous()
                if previous_chapter is not None:
                    return previous_chapter[len(previous_chapter)]
            return None
        return self.chapter[self.number - 1]

    def text(self):
        raise NotImplementedError()


class Chapter(object):
    _NAME_REGEX = re.compile(r"^(?P<chapter_number>\d+)$")
    _PASSAGE_REGEX = re.compile(f"^{_extract_pattern(Verse)}?{_range}{_extract_pattern(Verse, '_end')}?$", flags=re.ASCII | re.IGNORECASE)

    def __init__(self, number, book):
        self._number = number
        book._register_chapter(self)
        self._book = book
        self._translation = self.book.translation
        self._verses = {}

    def __contains__(self, item):
        return item in self.verses.values()

    def __getitem__(self, key):
        try:
            return self.verses[key]
        except KeyError:
            raise BibleReferenceError(f"{key} is not between 1 and {len(self)}")

    def __int__(self):
        return _int_reference(self.book.number, self.number)

    def __iter__(self):
        return iter(self.verses)

    def __len__(self):
        return len(self.verses)

    def __repr__(self):
        return (f"{self.__class__.__module__}.{self.__class__.__name__}(number={self.number}, book={self.book.name}, "
                f"translation={self.translation.name})")

    def __str__(self):
        return _reference(self.book.name, self.number)

    def _register_verse(self, verse):
        if verse.number in self.verses:
            raise BibleSetupError(f"there is already a verse registered in this chapter ({self}) with the number, {verse.number}")
        self._verses[verse.number] = verse

    @property
    def book(self):
        return self._book

    @property
    def is_first(self):
        return self.number == 1

    @property
    def is_last(self):
        return self.number == len(self.book)

    @property
    def number(self):
        return self._number

    @property
    def translation(self):
        return self._translation

    @property
    def verses(self):
        return self._verses

    def next(self, overspill=True):
        if self.is_last:
            if overspill:
                next_book = self.book.next()
                if next_book is not None:
                    return next_book[1]
            return None
        return self.book[self.number + 1]

    def passage(self, reference="-"):
        match = self._PASSAGE_REGEX.match(reference)
        if match is None:
            raise BibleReferenceError(f"the reference, '{reference}'' does not match the expected regex pattern, {self._PASSAGE_REGEX}")
        groups = match.groupdict()
        verse_start = self[_int(groups["verse_number_start"]) or 1]
        if groups["range"] is None:
            verse_end = verse_start
        else:
            verse_end = self[_int(groups["verse_number_end"]) or len(self)]
        if int(verse_end) < int(verse_start):
            raise BibleReferenceError("the requested passage range is invalid; the right hand side of the range must be greater than the left")
        return utils.module_of_instance(self).Passage(self.book, self, verse_start, self.book, self, verse_end)

    def previous(self, overspill=True):
        if self.is_last:
            if overspill:
                previous_book = self.book.previous()
                if previous_book is not None:
                    return previous_book[len(previous_book)]
            return None
        return self.book[self.number - 1]


class Book(object):
    _NAME_REGEX = re.compile(r"^(?P<book_name>(?:\d{1})?[A-Z]+)$", flags=re.ASCII | re.IGNORECASE)
    _PASSAGE_REGEX = re.compile(fr"^{_extract_pattern(Chapter)}?:?{_extract_pattern(Verse)}?{_range}(?P<chapter_number_end>(?<!:.*-)\d+|(?=\d*:)\d+)?"
                                f":?{_extract_pattern(Verse, '_end')}?$", flags=re.ASCII | re.IGNORECASE)

    def __init__(self, name, number, translation, author, language, alt_names=(), categories=()):
        _id = _name_to_id(name)
        if not self._NAME_REGEX.match(_id):
            raise BibleSetupError(f"the derived id, '{_id}' does not match the expected regex pattern, {self._NAME_REGEX}")
        self._name = name
        self._id = _id
        self._number = number
        self._author = author
        self._language = language
        self._alt_names = sorted(alt_names)
        self._alt_ids = sorted(_name_to_id(alt_name) for alt_name in alt_names)
        self._categories = sorted(categories)
        translation._register_book(self)
        self._translation = translation
        self._chapters = {}

    def __contains__(self, item):
        return item in self.chapters.values()

    def __getitem__(self, key):
        try:
            return self.chapters[key]
        except KeyError:
            raise BibleReferenceError(f"{key} is not between 1 and {len(self)}")

    def __int__(self):
        return _int_reference(self.book.number)

    def __iter__(self):
        return iter(self.chapters)

    def __len__(self):
        return len(self.chapters)

    def __repr__(self):
        return f"{self.__class__.__module__}.{self.__class__.__name__}(name={self.name}, number={self.number}, translation={self.translation.name})"

    def __str__(self):
        return _reference(self.name)

    def _register_chapter(self, chapter):
        if chapter.number in self.chapters:
            raise BibleSetupError(f"there is already a chapter registered in this book ({self}) with the number, {chapter.number}")
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
    def chapters(self):
        return self._chapters

    @property
    def id(self):
        return self._id

    @property
    def is_first(self):
        return self.number == 1

    @property
    def is_last(self):
        return self.number == len(self.translation)

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

    def next(self):
        if self.is_last:
            return None
        return self.translation[self.number + 1]

    def passage(self, reference="-"):
        match = self._PASSAGE_REGEX.match(reference)
        if match is None:
            raise BibleReferenceError(f"the reference, '{reference}' does not match the expected regex pattern, {self._PASSAGE_REGEX}")
        groups = match.groupdict()
        chapter_start = self[_int(groups["chapter_number_start"]) or 1]
        verse_number_start = _int(groups["verse_number_start"])
        verse_start = chapter_start[verse_number_start or 1]
        if groups["range"] is None:
            chapter_end = chapter_start
            verse_end = verse_start
        else:
            chapter_end = self[_int(groups["chapter_number_end"]) or (chapter_start.number if verse_number_start else len(self))]
            verse_end = chapter_end[_int(groups["verse_number_end"]) or len(chapter_end)]
        if int(verse_end) < int(verse_start):
            raise BibleReferenceError("the requested passage range is invalid; the right hand side of the range must be greater than the left")
        return utils.module_of_instance(self).Passage(self, chapter_start, verse_start, self, chapter_end, verse_end)

    def previous(self):
        if self.is_first:
            return None
        return self.translation[self.number - 1]


class Translation(object):
    _INT_PASSAGE_REGEX = re.compile(r"(?P<book_number_start>\d{1,2})(?P<chapter_number_start>\d{3})(?P<verse_number_start>\d{3}){_range}"
                                    r"(?P<book_number_end>\d{1,2})(?P<chapter_number_end>\d{3})(?P<verse_number_end>\d{3})")
    _PASSAGE_REGEX = re.compile(fr"^{_extract_pattern(Book)}?{_extract_pattern(Chapter)}?:?{_extract_pattern(Verse)}?{_range}"
                                fr"{_extract_pattern(Book, '_end')}?(?P<chapter_number_end>(?<!:.*-)\d+|(?=\d*:)\d+)?:?"
                                fr"{_extract_pattern(Verse, '_end')}?$", flags=re.ASCII | re.IGNORECASE)

    def __init__(self, name):
        self.name = name
        self._books = utils.FuzzyDict()
        self._categories = utils.FuzzyDict()

    def __contains__(self, item):
        return item in set(self.books.values())

    def __getitem__(self, key):
        try:
            return self.books[_name_to_id(key)]
        except KeyError:
            raise BibleReferenceError(f"{key} is not between 1 and {len(self)}")

    def __iter__(self):
        return iter(self.books)

    def __len__(self):
        return len(set(self.books.values()))

    def __repr__(self):
        return f"{self.__class__.__module__}.{self.__class__.__name__}(name={self.name})"

    def _register_book(self, book):
        book_ids = (book.number, book.id, *book.alt_ids)
        existing_book_ids = [book_id for book_id in book_ids if book_id in self.books]
        if existing_book_ids:
            raise BibleSetupError(f"there is already a book registered in this translation ({self}) with the key(s), {','.join(existing_book_ids)}")
        self._books.update(dict.fromkeys(book_ids, book))
        for category in book.categories:
            existing_category = self._categories.get(category)
            if existing_category is None:
                existing_category = self._categories[category] = []
            existing_category.append(book)

    @property
    def books(self):
        return self._books

    @property
    def categories(self):
        return self._categories

    def passage(self, reference=None, int_reference=None):
        if reference is not None:
            if int_reference is not None:
                raise ValueError("reference and int_reference are mutually exclusive arguments; only 1 should be not None")
            match = self._PASSAGE_REGEX.match(_name_to_id(reference))
            if match is None:
                raise BibleReferenceError(f"the reference, '{reference}' does not match the expected regex pattern, {self._PASSAGE_REGEX}")
            book_start_group = "book_name_start"
            book_end_group = "book_name_end"
        else:
            if int_reference is None:
                raise ValueError("either reference or int_reference must be not None")
            match = self._INT_PASSAGE_REGEX.match(_name_to_id(int_reference))
            if match is None:
                raise BibleReferenceError(f"the int_reference, {int_reference} does not match the expected regex pattern, {self._INT_PASSAGE_REGEX}")
            book_start_group = "book_number_start"
            book_end_group = "book_number_end"
        groups = match.groupdict()
        book_start = self.books[groups[book_start_group] or 1]
        chapter_number_start = _int(groups["chapter_number_start"])
        chapter_start = book_start[chapter_number_start or 1]
        verse_number_start = _int(groups["verse_number_start"])
        verse_start = chapter_start[verse_number_start or 1]
        if groups["range"] is None:
            book_end = book_start
            chapter_end = chapter_start
            verse_end = verse_start
        else:
            chapter_or_verse = chapter_number_start or verse_number_start
            book_end = self.books[groups[book_end_group] or (book_start.number if chapter_or_verse else len(self.books))]
            chapter_end = book_end[_int(groups["chapter_number_end"]) or (chapter_start.number if verse_number_start else len(book_end))]
            verse_end = chapter_end[_int(groups["verse_number_end"]) or len(chapter_end)]
        if int(verse_end) < int(verse_start):
            raise BibleReferenceError("the requested passage range is invalid; the right hand side of the range must be greater than the left")
        return utils.module_of_instance(self).Passage(book_start, chapter_start, verse_start, book_end, chapter_end, verse_end)


class Passage(object):
    def __init__(self, book_start, chapter_start, verse_start, book_end, chapter_end, verse_end):
        self._book_start = book_start
        self._chapter_start = chapter_start
        self._verse_start = verse_start
        self._book_end = book_end
        self._chapter_end = chapter_end
        self._verse_end = verse_end

    def __len__(self):
        return sum(1 for _ in self.verses())

    def __repr__(self):
        return (f"{self.__class__.__module__}.{self.__class__.__name__}(book_start={self.book_start.name}, "
                f"chapter_start={self.chapter_start.number}, verse_start={self.verse_start.number}, book_end={self.book_end.name}, "
                f"chapter_end={self.chapter_end.number}, verse_end={self.verse_end.number})")

    def __str__(self):
        return (f"{_reference(self.book_start.name, self.chapter_start.number, self.verse_start.number)} - "
                f"{_reference(self.book_end.name, self.chapter_end.number, self.verse_end.number)}")

    @property
    def book_start(self):
        return self._book_start

    @property
    def chapter_start(self):
        return self._chapter_start

    @property
    def verse_start(self):
        return self._verse_start

    @property
    def book_end(self):
        return self._book_end

    @property
    def chapter_end(self):
        return self._chapter_end

    @property
    def int_reference(self):
        return (f"{str(int(self.verse_start))}-{str(int(self.verse_end))}")

    @property
    def verse_end(self):
        return self._verse_end

    def audio(self):
        raise NotImplementedError()

    def books(self):
        next_book = self.book_start
        while next_book is not None and int(next_book) <= int(self.book_end):
            yield next_book
            next_book = next_book.next()

    def chapters(self):
        next_chapter = self.chapter_start
        while next_chapter is not None and int(next_chapter) <= int(self.chapter_end):
            yield next_chapter
            next_chapter = next_chapter.next()

    def text(self):
        raise NotImplementedError()

    def verses(self):
        next_verse = self.verse_start
        while next_verse is not None and int(next_verse) <= int(self.verse_end):
            yield next_verse
            next_verse = next_verse.next()

# TODO: Use dataclasses?
