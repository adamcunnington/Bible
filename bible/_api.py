import re


# TODO: Add magic methods; __len__, __repr__, __str__, max(); __iter__


def _extract_pattern(cls, group_suffix=None):
    name_pattern = getattr(cls, "_NAME_REGEX").pattern
    if group_suffix is not None:
        name_pattern = name_pattern.replace(">", f"{group_suffix}>")
    return name_pattern[1:-1]


class BibleReferenceError(Exception):
    pass


class BibleSetupError(Exception):
    pass


class Verse(object):
    _NAME_REGEX = re.compile(r"^(?P<verse>\d+)$", flags=re.ASCII | re.IGNORECASE)

    def __init__(self, number, chapter):
        self.number = number
        self.chapter._register_verse(self)
        self.chapter = chapter
        self.name = f"{self.chapter.name}:{self.number}"
        self.book = self.chapter.book
        self.translation = self.book.translation
        self.is_first = self.number == 1

    @property
    def is_last(self):
        return self.number == max(self.chapter._verses)

    def audio(self):
        pass

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
                    return previous_chapter.verse(max(previous_chapter._verses))
            return None
        return self.chapter.verse(self.number - 1)

    def text(self):
        pass


class Chapter(object):
    _NAME_REGEX = re.compile(r"^(?P<chapter>\d+)$", flags=re.ASCII | re.IGNORECASE)
    _PASSAGE_REGEX = re.compile(fr"^{_extract_pattern(Verse)}?-{_extract_pattern(Verse, '_end')}?$", flags=re.ASCII | re.IGNORECASE)

    def __init__(self, number, book):
        self.number = number
        self.book._register_chapter(self)
        self.book = book
        self.name = f"{self.book.name} {self.number}"
        self.translation = self.book.translation
        self.is_first = self.number == 1
        self._verses = {}

    def _register_verse(self, verse):
        if verse.number in self._verses:
            raise BibleSetupError(f"there is already a verse registered in this chapter ({self.name}) with the number, {book.verse}")
        self._verses[verse.number] = verse

    @property
    def is_last(self):
        return self.number == max(self.book._chapters)

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
        verse_number = match.group["verse"]
        if verse_number is not None and verse_number not in self._verses:
            raise BibleReferenceError(f"the reference, {reference} is out of range")
        verse = self.verse(verse_number or 1)
        verse_end_number = match.group["verse_end"]
        if verse_end_number is not None and verse_end_number not in self._verses:
            raise BibleReferenceError(f"the reference, {reference} is out of range")
        verse_end = self.verse(verse_end_number or max(self._verses))
        if verse_end.number <= verse.number:
            raise BibleReferenceError(f"the requested passage range is invalid; the right hand side of the range must be chronologically later")
        return Passage(self.book, self, verse, self.book, self, verse_end)

    def previous(self, overspill=True):
        if self.is_last:
            if overspill:
                previous_book = self.book.previous()
                if previous_book is not None:
                    return previous_book.chapter(max(previous_book._chapters))
            return None
        return self.book.chapter(self.number - 1)

    def verse(self, number):
        self.number = number


class Book(object):
    _NAME_REGEX = re.compile(r"^(?P<book>(?:\d{1})?[a-z]+)$")
    _PASSAGE_REGEX = re.compile(fr"^{_extract_pattern(Chapter)}?(?::{_extract_pattern(Verse)})?"
        fr"-{_extract_pattern(Chapter, '_end')}?(?::{_extract_pattern(Verse, '_end')})?$", flags=re.ASCII | re.IGNORECASE)

    def __init__(self, name, number, translation):
        # TODO: Need to implement other_names; the book should be findable from any of the names.
        # TODO: Need to implement categories; these should become methods on the translation object. Enum? How to access on book object?
        if not self._NAME_REGEX.match(name):
            raise BibleSetupError(f"the name, {name} does not match the expected regular expression pattern, {self._NAME_REGEX}")
        self.name = name
        self.number = number
        self.translation._register_book(self)
        self.translation = translation
        self.is_first = self.number == 1
        self._chapters = {}

    def _register_chapter(self, chapter):
        if chapter.number in self._chapters:
            raise BibleSetupError(f"there is already a chapter registered in this book ({self.name}) with the number, {book.chapter}")
        self._chapters[chapter.number] = chapter

    @property
    def is_last(self):
        return self.number == max(self.translation._books_by_number)

    def chapter(self, number):
        pass

    def next(self):
        if self.is_last:
            return None
        return self.translation.book(number=self.number + 1)

    def passage(self, reference="-"):
        match = self._PASSAGE_REGEX.match(reference.replace(" ", ""))
        if match is None:
            raise BibleReferenceError(f"the reference, {reference} does not match the expected regular expression pattern, {self._PASSAGE_REGEX}")
        groups = match.groupdict()
        chapter_number = match.group["chapter"]
        if chapter_number is not None and chapter_number not in self._chapters:
            raise BibleReferenceError(f"the reference, {reference} is out of range")
        chapter = self.chapter(chapter_number or 1)
        verse_number = match.group["verse"]
        if verse_number is not None and verse_number not in chapter._verses:
            raise BibleReferenceError(f"the reference, {reference} is out of range")
        verse = chapter.verse(verse_number or 1)
        chapter_end_number = match.group["chapter_end"]
        if chapter_end_number is not None and chapter_end_number not in self._chapters:
            raise BibleReferenceError(f"the reference, {reference} is out of range")
        chapter_end = self.chapter(chapter_end_number or max(self._chapters))
        verse_end_number = match.group["verse_end"]
        if verse_end_number is not None and verse_end_number not in chapter_end._verses:
            raise BibleReferenceError(f"the reference, {reference} is out of range")
        verse_end = chapter_end.verse(verse_end_number or max(chapter_end._verses))
        if (chapter_end.number < chapter.number) or (verse_end.number <= verse.number):
            raise BibleReferenceError(f"the requested passage range is invalid; the right hand side of the range must be chronologically later")
        return Passage(self, chapter, verse, self, chapter_end, verse_end)

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
            return self._books_by_name[name]
        if number is None:
            raise ValueError("Either name or number must be not None.")
        return self._books_by_number[number]

    def passage(self, reference="-"):
        match = self._PASSAGE_REGEX.match(reference.replace(" ", ""))
        if match is None:
            raise BibleReferenceError(f"the reference, {reference} does not match the expected regular expression pattern, {self._PASSAGE_REGEX}")
        groups = match.groupdict()
        book_number = match.group["book"]
        if book_number is not None and book_number not in self._books:
            raise BibleReferenceError(f"the reference, {reference} is out of range")
        book = self.book(number=book_number or 1)
        chapter_number = match.group["chapter"]
        if chapter_number is not None and chapter_number not in book._chapters:
            raise BibleReferenceError(f"the reference, {reference} is out of range")
        chapter = book.chapter(chapter_number or 1)
        verse_number = match.group["verse"]
        if verse_number is not None and verse_number not in chapter._verses:
            raise BibleReferenceError(f"the reference, {reference} is out of range")
        verse = chapter.verse(verse_number or 1)
        book_end_number = match.group["book_end"]
        if book_end_number is not None and book_end_number not in self._books:
            raise BibleReferenceError(f"the reference, {reference} is out of range")
        book_end = self.book(number=book_end_number or max(self._books_by_number))
        chapter_end_number = match.group["chapter_end"]
        if chapter_end_number is not None and chapter_end_number not in book_end._chapters:
            raise BibleReferenceError(f"the reference, {reference} is out of range")
        chapter_end = book_end.chapter(chapter_end_number or max(book_end._chapters))
        verse_end_number = match.group["verse_end"]
        if verse_end_number is not None and verse_end_number not in chapter_end._verses:
            raise BibleReferenceError(f"the reference, {reference} is out of range")
        verse_end = chapter_end.verse(verse_end_number or max(chapter_end._verses))
        if (book_end.number < book.number) or (chapter_end.number < chapter.number) or (verse_end.number <= verse.number):
            raise BibleReferenceError(f"the requested passage range is invalid; the right hand side of the range must be chronologically later")
        return Passage(book, chapter, verse, book_end, chapter_end, verse_end)


class Passage(object):
    def __init__(self, book, chapter, verse, book_end=None, chapter_end=None, verse_end=None):
        self.book = book
        self.chapter = chapter
        self.verse = verse
        self.book_end = book_end
        self.chapter_end = chapter_end
        self.verse_end = verse_end

    def audio(self):
        pass

    def text(self):
        pass
