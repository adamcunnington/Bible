import re


# TODO: Should we make certain attributes not settable by public callers? E.g. name, reference to parents etc.


def _extract_pattern(cls, group_suffix="_start"):
    name_pattern = getattr(cls, "_NAME_REGEX").pattern
    if group_suffix is not None:
        name_pattern = name_pattern.replace(">", f"{group_suffix}>")
    return name_pattern[1:-1]


def _int_reference(book_number, chapter_number=1, verse_number=1):
    return f"{book_number:01d}{chapter_number:03d}{verse_number:03d}"


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
        return f"{self.__class__.__module__}.{self.__class__.__name__}(number={self.number!r}, chapter={self.chapter!r})"

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
        return self.number == max(self.chapter)

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
                    return next_chapter.verse(1)
            return None
        return self.chapter.verse(self.number + 1)

    def previous(self, overspill=True):
        if self.is_last:
            if overspill:
                previous_chapter = self.chapter.previous()
                if previous_chapter is not None:
                    return previous_chapter.verse(max(previous_chapter))
            return None
        return self.chapter.verse(self.number - 1)

    def text(self):
        raise NotImplementedError()


class Chapter(object):
    _NAME_REGEX = re.compile(r"^(?P<chapter_number>\d+)$")
    _PASSAGE_REGEX = re.compile(f"^{_extract_pattern(Verse)}?-{_extract_pattern(Verse, '_end')}?$", flags=re.ASCII | re.IGNORECASE)

    def __init__(self, number, book):
        self._number = number
        book._register_chapter(self)
        self._book = book
        self._translation = self.book.translation
        self._verses = {}

    def __int__(self):
        return _int_reference(self.book.number, self.number)

    def __iter__(self):
        return iter(self._verses)

    def __len__(self):
        return len(self._verses)

    def __repr__(self):
        return f"{self.__class__.__module__}.{self.__class__.__name__}(number={self.number!r}, book={self.book!r})"

    def __str__(self):
        return _reference(self.book.name, self.number)

    def _register_verse(self, verse):
        if verse.number in self._verses:
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
        return self.number == max(self.book)

    @property
    def number(self):
        return self._number

    @property
    def translation(self):
        return self._translation

    def next(self, overspill=True):
        if self.is_last:
            if overspill:
                next_book = self.book.next()
                if next_book is not None:
                    return next_book.chapter(1)
            return None
        return self.book.chapter(self.number + 1)

    def passage(self, reference="-"):
        match = self._PASSAGE_REGEX.match(reference.replace(" ", ""))
        if match is None:
            raise BibleReferenceError(f"the reference, {reference} does not match the expected regex pattern, {self._PASSAGE_REGEX}")
        groups = match.groupdict()
        verse_start = self.verse(match.group["verse_number_start"] or 1)
        verse_end = self.verse(match.group["verse_number_end"] or max(self))
        if verse_end.number <= verse_start.number:
            raise BibleReferenceError(f"the requested passage range is invalid; the right hand side of the range must be greater than the left")
        return Passage(self.book, self, verse_start, self.book, self, verse_end)

    def previous(self, overspill=True):
        if self.is_last:
            if overspill:
                previous_book = self.book.previous()
                if previous_book is not None:
                    return previous_book.chapter(max(previous_book))
            return None
        return self.book.chapter(self.number - 1)

    def verse(self, number):
        if number not in self._verses:
            raise BibleReferenceError(f"the number, {number} is out of range of this chapter's verses")


class Book(object):
    _NAME_REGEX = re.compile(r"^(?P<book_name>(?:\d{1})?[A-Z]+)$", flags=re.ASCII | re.IGNORECASE)
    _PASSAGE_REGEX = re.compile(f"^{_extract_pattern(Chapter)}?(?::{_extract_pattern(Verse)})?"
                                f"-{_extract_pattern(Chapter, '_end')}?(?::{_extract_pattern(Verse, '_end')})?$", flags=re.ASCII | re.IGNORECASE)

    def __init__(self, name, number, translation, alt_names=None, categories=None):
        # TODO: Need to implement other_names; the book should be findable from any of the names.
        # TODO: Need to implement categories; these should become methods on the translation object. Enum? How to access on book object? Testaments?
        if not self._NAME_REGEX.match(name):
            raise BibleSetupError(f"the name, {name} does not match the expected regex pattern, {self._NAME_REGEX}")
        self._name = name.upper()
        self._number = number
        translation._register_book(self)
        self._translation = translation
        self._chapters = {}

    def __int__(self):
        return _int_reference(self.book.number)

    def __iter__(self):
        return iter(self._chapters)

    def __len__(self):
        return len(self._chapters)

    def __repr__(self):
        return f"{self.__class__.__module__}.{self.__class__.__name__}(name={self.name!r}, number={self.number!r}, translation={self.translation!r})"

    def __str__(self):
        return _reference(self.name)

    def _register_chapter(self, chapter):
        if chapter.number in self._chapters:
            raise BibleSetupError(f"there is already a chapter registered in this book ({self}) with the number, {chapter.number}")
        self._chapters[chapter.number] = chapter

    @property
    def is_first(self):
        return self.number == 1

    @property
    def is_last(self):
        return self.number == max(self.translation)

    @property
    def name(self):
        return self._name

    @property
    def number(self):
        return self._number

    @property
    def translation(self):
        return self._translation

    def chapter(self, number):
        if number not in self._chapters:
            raise BibleReferenceError(f"the number, {number} is out of range of this book's chapters")

    def next(self):
        if self.is_last:
            return None
        return self.translation.book(number=self.number + 1)

    def passage(self, reference="-"):
        match = self._PASSAGE_REGEX.match(reference.replace(" ", ""))
        if match is None:
            raise BibleReferenceError(f"the reference, {reference} does not match the expected regex pattern, {self._PASSAGE_REGEX}")
        groups = match.groupdict()
        chapter_start = self.chapter(match.group["chapter_number_start"] or 1)
        verse_start = chapter.verse(match.group["verse_number_start"] or 1)
        chapter_end = self.chapter(match.group["chapter_number_end"] or max(self))
        verse_end = chapter_end.verse(match.group["verse_number_end"] or max(chapter_end))
        if (chapter_end.number < chapter_start.number) or (verse_end.number <= verse_start.number):
            raise BibleReferenceError(f"the requested passage range is invalid; the right hand side of the range must be greater than the left")
        return Passage(self, chapter_start, verse_start, self, chapter_end, verse_end)

    def previous(self):
        if self.is_first:
            return None
        return self.translation.book(number=self.number - 1)


class Translation(object):
    _INT_PASSAGE_REGEX = re.compile(r"(?P<book_number_start>\d{1,2})(?P<chapter_number_start>\d{3})(?P<verse_number_start>\d{3})-"
                                    r"(?P<book_number_end>\d{1,2})(?P<chapter_number_end>\d{3})(?P<verse_number_end>\d{3})")
    _PASSAGE_REGEX = re.compile(f"^{_extract_pattern(Book)}?(?:{_extract_pattern(Chapter)}?(?::{_extract_pattern(Verse)})?)?-"
                                f"{_extract_pattern(Book, '_end')}?(?:{_extract_pattern(Chapter, '_end')}?(?::{_extract_pattern(Verse, '_end')})?)?$",
                                flags=re.ASCII | re.IGNORECASE)

    def __init__(self, name):
        self.name = name
        self._books_by_name = {}
        self._books_by_number = {}

    def __iter__(self):
        return iter(self._books_by_number)

    def __len__(self):
        return len(self._books_by_number)

    def __repr__(self):
        return f"{self.__class__.__module__}.{self.__class__.__name__}(name={self.name!r})"

    def _register_book(self, book):
        if book.name in self._books_by_name:
            raise BibleSetupError(f"there is already a book registered in this translation ({self}) with the name, {book.name}")
        elif book.number in self._books_by_number:
            raise BibleSetupError(f"there is already a book registered in this translation ({self}) with the number, {book.number}")
        self._books_by_name[book.name] = book
        self._books_by_number[book.number] = book

    def book(self, name=None, number=None):
        if name is not None:
            if number is not None:
                raise ValueError("name and number are mutually exclusive arguments; only 1 should be not None")
            name = name.upper()
            if name not in self._books_by_name:
                raise BibleReferenceError(f"the name, {name} is out of range of this translation's books")
            return self._books_by_name[name]
        if number is None:
            raise ValueError("either name or number must be not None")
        if number not in self._books_by_number:
            raise BibleReferenceError(f"the number, {number} is out of range of this translation's books")
        return self._books_by_number[number]

    def passage(self, reference=None, int_reference=None):
        if reference is not None:
            if int_reference is not None:
                raise ValueError("reference and int_reference are mutually exclusive arguments; only 1 should be not None")
            match = self._PASSAGE_REGEX.match(reference.replace(" ", ""))
            if match is None:
                raise BibleReferenceError(f"the reference, {reference} does not match the expected regex pattern, {self._PASSAGE_REGEX}")
            groups = match.groupdict()
            book_name_start = match.group["book_name_start"]
            book_start = self.book(book_name_start) if book_name_start is not None else self.book(number=1)
            book_name_end = match.group["book_name_end"]
            book_end = self.book(book_name_end) if book_name_end is not None else self.book(number=max(self))
        else:
            if int_reference is None:
                raise ValueError("either reference or int_reference must be not None")
            match = self._INT_PASSAGE_REGEX.match(int_reference.replace(" ", ""))
            if match is None:
                raise BibleReferenceError(f"the int_reference, {int_reference} does not match the expected regex pattern, {self._INT_PASSAGE_REGEX}")
            groups = match.groupdict()
            book_start = self.book(number=match.group["book_number_start"] or 1)
            book_end = self.book(number=match.group["book_number_end"] or max(self))
        chapter_start = book.chapter(match.group["chapter_number_start"] or 1)
        verse_start = chapter_start.verse(match.group["verse_number_start"] or 1)
        chapter_end = book_end.chapter(match.group["chapter_number_end"] or max(book_end))
        verse_end = chapter_end.verse(match.group["verse_number_end"] or max(chapter_end))
        if (book_end.number < book_start.number) or (chapter_end.number < chapter_start.number) or (verse_end.number <= verse_start.number):
            raise BibleReferenceError(f"the requested passage range is invalid; the right hand side of the range must be greater than the left")
        return Passage(book_start, chapter_start, verse_start, book_end, chapter_end, verse_end)


class Passage(object):
    def __init__(self, book_start, chapter_start, verse_start, book_end, chapter_end, verse_end):
        self.book_start = book_start
        self.chapter_start = chapter_start
        self.verse_start = verse_start
        self.book_end = book_end
        self.chapter_end = chapter_end
        self.verse_end = verse_end
        # TODO: Implement some sort of list of objects on demand, e.g. list of all books, chapters and verses encapsulated by the range?

    def audio(self):
        raise NotImplementedError()

    def text(self):
        raise NotImplementedError()
        # TODO: FYI, the cacheing of data in _text or similar is the translation subpackage's job, not the standard API.
        # TODO: FYI, Also, if text() will return some translation-specific text object with various attributes and special __len__ behaviour for
        # counting words etc. for meta analysis, that is also the translation subpackage's job, not the standard API.
