import regex as re  # we need variable-width lookbehind assertions

from bible import utils


_range = "(?P<range>-)?"


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

    def __repr__(self):
        return (f"{self.__class__.__module__}.{self.__class__.__name__}(number={self.number}, chapter={self.chapter.number}, "
                f"book={self.book.name}, translation={self.translation.name})")

    def __str__(self):
        return utils.reference(self.book.name, self.chapter.number, self.number)

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
    def int_reference(self):
        return utils.int_reference(self.book.number, self.chapter.number, self.number)

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
                    return next_chapter.first()
            return None
        return self.chapter[self.number + 1]

    def previous(self, overspill=True):
        if self.is_last:
            if overspill:
                previous_chapter = self.chapter.previous()
                if previous_chapter is not None:
                    return previous_chapter.last()
            return None
        return self.chapter[self.number - 1]

    def text(self):
        raise NotImplementedError()


class Chapter(object):
    _NAME_REGEX = re.compile(r"^(?P<chapter_number>\d+)$")
    _PASSAGE_REGEX = re.compile(f"^{utils.fetch_pattern(Verse)}?{_range}{utils.fetch_pattern(Verse, '_end')}?$", flags=re.ASCII | re.IGNORECASE)

    def __init__(self, number, book):
        self._number = number
        book._register_chapter(self)
        self._book = book
        self._translation = self.book.translation
        self._verses = {}

    def __contains__(self, item):
        return item in self._verses.values()

    def __getitem__(self, key):
        try:
            return self._verses[key]
        except KeyError:
            raise BibleReferenceError(f"{key} is not between {str(self.first())} and {str(self.last())}")

    def __iter__(self):
        return utils.unique_value_iterating_dict(self._verses)

    def __len__(self):
        return len(self._verses)

    def __repr__(self):
        return (f"{self.__class__.__module__}.{self.__class__.__name__}(number={self.number}, book={self.book.name}, "
                f"translation={self.translation.name})")

    def __str__(self):
        return utils.reference(self.book.name, self.number)

    def _register_verse(self, verse):
        if verse.number in self._verses:
            raise BibleSetupError(f"there is already a verse registered in this chapter ({self}) with the number, {verse.number}")
        self._verses[verse.number] = verse

    @property
    def book(self):
        return self._book

    @property
    def int_reference(self):
        return utils.int_reference(self.book.number, self.number)

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

    def audio(self):
        raise NotImplementedError()

    def first(self):
        return self[1]

    def last(self):
        return self[len(self)]

    def next(self, overspill=True):
        if self.is_last:
            if overspill:
                next_book = self.book.next()
                if next_book is not None:
                    return next_book.first()
            return None
        return self.book[self.number + 1]

    def passage(self, reference="-"):
        match = self._PASSAGE_REGEX.match(reference)
        if match is None:
            raise BibleReferenceError(f"the reference, '{reference}'' does not match the expected regex pattern, {self._PASSAGE_REGEX}")
        groups = match.groupdict()
        verse_start = self[utils.safe_int(groups["verse_number_start"]) or 1]
        if groups["range"] is None:
            verse_end = verse_start
        else:
            verse_end = self[utils.safe_int(groups["verse_number_end"]) or len(self)]
        if int(verse_end.int_reference) < int(verse_start.int_reference):
            raise BibleReferenceError("the requested passage range is invalid; the right hand side of the range must be greater than the left")
        return utils.module_of_instance(self).Passage(self.book, self, verse_start, self.book, self, verse_end)

    def previous(self, overspill=True):
        if self.is_last:
            if overspill:
                previous_book = self.book.previous()
                if previous_book is not None:
                    return previous_book.last()
            return None
        return self.book[self.number - 1]

    def text(self):
        raise NotImplementedError()

    def verses(self):
        yield from self._verses.values()


class Book(object):
    _NAME_REGEX = re.compile(r"^(?P<book_name>(?:\d{1})?[A-Z]+)$", flags=re.ASCII | re.IGNORECASE)
    _PASSAGE_REGEX = re.compile(fr"^{utils.fetch_pattern(Chapter)}?:?{utils.fetch_pattern(Verse)}?{_range}"
                                fr"(?P<chapter_number_end>(?<!:.*-)\d+|(?=\d*:)\d+)?:?{utils.fetch_pattern(Verse, '_end')}?$",
                                flags=re.ASCII | re.IGNORECASE)

    def __init__(self, name, number, translation, author, language, alt_names=(), categories=()):
        _id = utils.slugify(name)
        if not self._NAME_REGEX.match(_id):
            raise BibleSetupError(f"the derived id, '{_id}' does not match the expected regex pattern, {self._NAME_REGEX}")
        self._name = name
        self._id = _id
        self._number = number
        self._author = author
        self._language = language
        self._alt_names = sorted(alt_names)
        self._alt_ids = sorted(utils.slugify(alt_name) for alt_name in alt_names)
        self._categories = sorted(categories)
        translation._register_book(self)
        self._translation = translation
        self._chapters = {}

    def __contains__(self, item):
        return item in self._chapters.values()

    def __getitem__(self, key):
        try:
            return self._chapters[key]
        except KeyError:
            raise BibleReferenceError(f"{key} is not between {str(self.first())} and {str(self.last())}")

    def __iter__(self):
        return utils.unique_value_iterating_dict(self._chapters)

    def __len__(self):
        return len(self._chapters)

    def __repr__(self):
        return f"{self.__class__.__module__}.{self.__class__.__name__}(name={self.name}, number={self.number}, translation={self.translation.name})"

    def __str__(self):
        return utils.reference(self.name)

    def _register_chapter(self, chapter):
        if chapter.number in self._chapters:
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
    def id(self):
        return self._id

    @property
    def int_reference(self):
        return utils.int_reference(self.book.number)

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

    def audio(self):
        raise NotImplementedError()

    def chapters(self):
        yield from self._chapters.values()

    def first(self):
        return self[1]

    def last(self):
        return self[len(self)]

    def next(self):
        if self.is_last:
            return None
        return self.translation[self.number + 1]

    def passage(self, reference="-"):
        match = self._PASSAGE_REGEX.match(reference)
        if match is None:
            raise BibleReferenceError(f"the reference, '{reference}' does not match the expected regex pattern, {self._PASSAGE_REGEX}")
        groups = match.groupdict()
        chapter_start = self[utils.safe_int(groups["chapter_number_start"]) or 1]
        verse_number_start = utils.safe_int(groups["verse_number_start"])
        verse_start = chapter_start[verse_number_start or 1]
        if groups["range"] is None:
            chapter_end = chapter_start
            verse_end = verse_start
        else:
            chapter_end = self[utils.safe_int(groups["chapter_number_end"]) or len(self)]
            verse_end = chapter_end[utils.safe_int(groups["verse_number_end"]) or len(chapter_end)]
        if int(verse_end.int_reference) < int(verse_start.int_reference):
            raise BibleReferenceError("the requested passage range is invalid; the right hand side of the range must be greater than the left")
        return utils.module_of_instance(self).Passage(self, chapter_start, verse_start, self, chapter_end, verse_end)

    def previous(self):
        if self.is_first:
            return None
        return self.translation[self.number - 1]

    def text(self):
        raise NotImplementedError()

    def verses(self):
        next_verse = self.first().first()
        verse_end_int_reference = int(self.last().last().int_reference)
        while next_verse is not None and int(next_verse.int_reference) <= verse_end_int_reference:
            yield next_verse
            next_verse = next_verse.next()


class Translation(object):
    _INT_PASSAGE_REGEX = re.compile(fr"^(?:(?P<book_number_start>\d{{1,2}})(?P<chapter_number_start>\d{{3}})(?P<verse_number_start>\d{{3}}))?{_range}"
                                    r"(?:(?P<book_number_end>\d{1,2})(?P<chapter_number_end>\d{3})(?P<verse_number_end>\d{3}))?$")
    _PASSAGE_REGEX = re.compile(fr"^{utils.fetch_pattern(Book)}?{utils.fetch_pattern(Chapter)}?:?{utils.fetch_pattern(Verse)}?{_range}"
                                fr"{utils.fetch_pattern(Book, '_end')}?(?P<chapter_number_end>(?<!:.*-)\d+|(?=\d*:)\d+)?:?"
                                fr"{utils.fetch_pattern(Verse, '_end')}?$", flags=re.ASCII | re.IGNORECASE)

    def __init__(self, name):
        self.name = name
        self._books = utils.FuzzyDict()
        self._categories = utils.FuzzyDict()

    def __contains__(self, item):
        return item in set(self._books.values())

    def __getitem__(self, key):
        try:
            return self._books[utils.slugify(key)]
        except KeyError:
            raise BibleReferenceError(f"{key} is not between {str(self.first())} and {str(self.last())}")

    def __iter__(self):
        return utils.unique_value_iterating_dict(self._books)

    def __len__(self):
        return len(set(self._books.values()))

    def __repr__(self):
        return f"{self.__class__.__module__}.{self.__class__.__name__}(name={self.name})"

    def _register_book(self, book):
        book_ids = (book.number, book.id, *book.alt_ids)
        existing_book_ids = [book_id for book_id in book_ids if book_id in self._books]
        if existing_book_ids:
            raise BibleSetupError(f"there is already a book registered in this translation ({self}) with the key(s), {','.join(existing_book_ids)}")
        self._books.update(dict.fromkeys(book_ids, book))
        for category in book.categories:
            existing_category = self._categories.get(category)
            if existing_category is None:
                existing_category = self._categories[category] = []
            existing_category.append(book)

    @property
    def categories(self):
        return self._categories

    def books(self):
        yield from utils.unique_value_iterating_dict(self._books)

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
                raise BibleReferenceError(f"the reference, '{reference}' does not match the expected regex pattern, {self._PASSAGE_REGEX}")
            book_start_group = "book_name_start"
            book_end_group = "book_name_end"
        else:
            if int_reference is None:
                raise ValueError("either reference or int_reference must be not None")
            match = self._INT_PASSAGE_REGEX.match(utils.slugify(int_reference))
            if match is None:
                raise BibleReferenceError(f"the int_reference, {int_reference} does not match the expected regex pattern, {self._INT_PASSAGE_REGEX}")
            book_start_group = "book_number_start"
            book_end_group = "book_number_end"
        groups = match.groupdict()
        book_start = self._books[utils.safe_int(groups[book_start_group]) or 1]
        chapter_number_start = utils.safe_int(groups["chapter_number_start"])
        chapter_start = book_start[chapter_number_start or 1]
        verse_number_start = utils.safe_int(groups["verse_number_start"])
        verse_start = chapter_start[verse_number_start or 1]
        if groups["range"] is None:
            book_end = book_start
            chapter_end = chapter_start
            verse_end = verse_start
        else:
            book_end = self._books[utils.safe_int(groups[book_end_group]) or len(self)]
            chapter_end = book_end[utils.safe_int(groups["chapter_number_end"]) or len(book_end)]
            verse_end = chapter_end[utils.safe_int(groups["verse_number_end"]) or len(chapter_end)]
        if int(verse_end.int_reference) < int(verse_start.int_reference):
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
        return (f"{utils.reference(self.book_start.name, self.chapter_start.number, self.verse_start.number)} - "
                f"{utils.reference(self.book_end.name, self.chapter_end.number, self.verse_end.number)}")

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
        return (f"{self.verse_start.int_reference}-{self.verse_end.int_reference}")

    @property
    def verse_end(self):
        return self._verse_end

    @property
    def verse_start(self):
        return self._verse_start

    def audio(self):
        raise NotImplementedError()

    def books(self):
        next_book = self.book_start
        book_end_int_reference = int(self.book_end.int_reference)
        while next_book is not None and int(next_book.int_reference) <= book_end_int_reference:
            yield next_book
            next_book = next_book.next()

    def chapters(self):
        next_chapter = self.chapter_start
        chapter_end_int_reference = int(self.chapter_end.int_reference)
        while next_chapter is not None and int(next_chapter.int_reference) <= chapter_end_int_reference:
            yield next_chapter
            next_chapter = next_chapter.next()

    def text(self):
        raise NotImplementedError()

    def verses(self):
        next_verse = self.verse_start
        verse_end_int_reference = int(self.verse_end.int_reference)
        while next_verse is not None and int(next_verse.int_reference) <= verse_end_int_reference:
            yield next_verse
            next_verse = next_verse.next()


class Character(object):
    def __init__(self):
        pass
