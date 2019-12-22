import re


def _extract_pattern(cls, group_suffix="_start"):
    name_pattern = getattr(cls, "_NAME_REGEX").pattern
    if group_suffix is not None:
        name_pattern = name_pattern.replace(">", f"{group_suffix}>")
    return name_pattern[1:-1]


def _int_reference(book_number, chapter_number=1, verse_number=1):
    return f"{book_number:01d}{chapter_number:03d}{verse_number:03d}"


def _str_reference(book_name, chapter_number=None, verse_number=None):
    return f"{book_name}{(f' {chapter_number}') if chapter_number else ''}{(f':{verse_number}') if verse_number else ''}"


class BibleReferenceError(Exception):
    pass


class BibleSetupError(Exception):
    pass


class Verse(object):
    _NAME_REGEX = re.compile(r"^(?P<verse>\d+)$")

    def __init__(self, number, chapter):
        self.number = number
        chapter._register_verse(self)
        self.chapter = chapter
        self.book = self.chapter.book
        self.translation = self.book.translation
        self.is_first = self.number == 1

    def __int__(self):
        return _int_reference(self.book.number, self.chapter.number, self.number)

    def __repr__(self):
        return f"{self.__class__.__module__}.{self.__class__.__name__}(number={self.number!r}, chapter={self.chapter!r})"

    def __str__(self):
        return _str_reference(self.book.name, self.chapter.number, self.number)

    @property
    def is_last(self):
        return self.number == max(self.chapter)

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
    _NAME_REGEX = re.compile(r"^(?P<chapter>\d+)$")
    _PASSAGE_REGEX = re.compile(fr"^{_extract_pattern(Verse)}?-{_extract_pattern(Verse, '_end')}?$", flags=re.ASCII | re.IGNORECASE)

    def __init__(self, number, book):
        self.number = number
        book._register_chapter(self)
        self.book = book
        self.name = f"{self.book.name} {self.number}"
        self.translation = self.book.translation
        self.is_first = self.number == 1
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
        return _str_reference(self.book.name, self.number)

    def _register_verse(self, verse):
        if verse.number in self._verses:
            raise BibleSetupError(f"there is already a verse registered in this chapter ({self.name}) with the number, {book.verse}")
        self._verses[verse.number] = verse

    @property
    def is_last(self):
        return self.number == max(self.book)

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
            raise BibleReferenceError(f"the reference, {reference} does not match the expected regular expression pattern, {self._PASSAGE_REGEX}")
        groups = match.groupdict()
        verse_start = self.verse(match.group["verse_start"] or 1)
        verse_end = self.verse(match.group["verse_end"] or max(self))
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
    _NAME_REGEX = re.compile(r"^(?P<book>(?:\d{1})?[a-z]+)$", flags=re.ASCII | re.IGNORECASE)
    _PASSAGE_REGEX = re.compile(fr"^{_extract_pattern(Chapter)}?(?::{_extract_pattern(Verse)})?"
        fr"-{_extract_pattern(Chapter, '_end')}?(?::{_extract_pattern(Verse, '_end')})?$", flags=re.ASCII | re.IGNORECASE)

    def __init__(self, name, number, translation, alt_names=None, categories=None):
        # TODO: Need to implement other_names; the book should be findable from any of the names.
        # TODO: Need to implement categories; these should become methods on the translation object. Enum? How to access on book object? Testaments?
        if not self._NAME_REGEX.match(name):
            raise BibleSetupError(f"the name, {name} does not match the expected regular expression pattern, {self._NAME_REGEX}")
        self.name = name
        self.number = number
        translation._register_book(self)
        self.translation = translation
        self.is_first = self.number == 1
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
        return _str_reference(self.name)

    def _register_chapter(self, chapter):
        if chapter.number in self._chapters:
            raise BibleSetupError(f"there is already a chapter registered in this book ({self.name}) with the number, {book.chapter}")
        self._chapters[chapter.number] = chapter

    @property
    def is_last(self):
        return self.number == max(self.translation)

    def chapter(self, number):
        if number not in self._chapters:
            raise BibleReferenceError(f"the number, {number} is out of range of this book's chapters")

    def next(self):
        if self.is_last:
            return None
        return self.translation.book(number=self.number + 1)

    def passage(self, reference):
        match = self._PASSAGE_REGEX.match(reference.replace(" ", ""))
        if match is None:
            raise BibleReferenceError(f"the reference, {reference} does not match the expected regular expression pattern, {self._PASSAGE_REGEX}")
        groups = match.groupdict()
        chapter_start = self.chapter(match.group["chapter_start"] or 1)
        verse_start = chapter.verse(match.group["verse_start"] or 1)
        chapter_end = self.chapter(match.group["chapter_end"] or max(self))
        verse_end = chapter_end.verse(match.group["verse_end"] or max(chapter_end))
        if (chapter_end.number < chapter_start.number) or (verse_end.number <= verse_start.number):
            raise BibleReferenceError(f"the requested passage range is invalid; the right hand side of the range must be greater than the left")
        return Passage(self, chapter_start, verse_start, self, chapter_end, verse_end)

    def previous(self):
        if self.is_first:
            return None
        return self.translation.book(number=self.number - 1)


class Translation(object):
    _PASSAGE_REGEX = re.compile(fr"^{_extract_pattern(Book)}?(?:{_extract_pattern(Chapter)}?(?::{_extract_pattern(Verse)})?)?"
        fr"(?:-{_extract_pattern(Book, '_end')}?(?:{_extract_pattern(Chapter, '_end')}?(?::{_extract_pattern(Verse, '_end')})?)?)?$",
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
            raise BibleSetupError(f"there is already a book registered in this translation ({self.name}) with the name, {book.name}")
        elif book.number in self._books_by_number:
            raise BibleSetupError(f"there is already a book registered in this translation ({self.name}) with the number, {book.number}")
        self._books_by_name[book.name] = book
        self._books_by_number[book.number] = book

    def book(self, name=None, number=None):
        if name is not None:
            if number is not None:
                raise ValueError("name and number are mutually exclusive arguments; only 1 should be not None")
            if name not in self._books_by_name:
                raise BibleReferenceError(f"the name, {name} is out of range of this translation's books")
            return self._books_by_name[name]
        if number is None:
            raise ValueError("Either name or number must be not None.")
        if number not in self._books_by_number:
            raise BibleReferenceError(f"the number, {number} is out of range of this translation's books")
        return self._books_by_number[number]

    def passage(self, reference="-"):
        match = self._PASSAGE_REGEX.match(reference.replace(" ", ""))
        if match is None:
            raise BibleReferenceError(f"the reference, {reference} does not match the expected regular expression pattern, {self._PASSAGE_REGEX}")
        groups = match.groupdict()
        book_start = self.book(number=match.group["book_start"] or 1)
        chapter_start = book.chapter(match.group["chapter_start"] or 1)
        verse_start = chapter.verse(match.group["verse_start"] or 1)
        book_end = self.book(number=match.group["book_end"] or max(self))
        chapter_end = book_end.chapter(match.group["chapter_end"] or max(book_end))
        verse_end = chapter_end.verse(match.group["verse_end"] or max(chapter_end))
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
