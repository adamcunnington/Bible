import itertools
import re

import requests
import vlc

from bible import _api


class ESVError(Exception):
    pass


class ESVAPIMixin(object):
    _AUTH_HEADER = {"Authorization": "Token 8334f7ff2c3ca64e05da7afa4e47eaf9efba59cb"}
    _BASE_URL = "https://api.esv.org/v3/passage/"
    _GET_AUDIO_URL_TEMPLATE = "https://audio.esv.org/hw/{reference}.mp3"
    _GET_SEARCH_ENDPOINT_TEMPLATE = "search/?q={query}&page-size={page_size}&page={page}"
    _GET_TEXT_ENDPOINT_TEMPLATE = ("text/?q={reference}&include-passage-references=false&include-verse-numbers=false&"
                                   "include-first-verse-numbers=false&include-footnotes=true&included-footnote-body=true&include-headings=true&"
                                   "include-short-copyright=false&include-passage-horizontal-lines=false&include-heading-horizontal-lines=false&"
                                   "include-selahs=true&indent-paragraphs=0&indent-poetry=false&indent-declares=0&indent-psalm-doxology=0&"
                                   "line-length=0")
    _MAX_VERSES_PER_AUDIO_QUERY = 500
    _MAX_VERSES_PER_TEXT_QUERY = 400

    def __init__(self, *args, **kwargs):
        self._text = None
        super().__init__(*args, **kwargs)

    def _get(self, endpoint_uri):
        return requests.get(self._BASE_URL + endpoint_uri, headers=self._AUTH_HEADER).json()


class Verse(ESVAPIMixin, _api.Verse):
    def audio(self):
        vlc.MediaPlayer(self._GET_AUDIO_URL_TEMPLATE.format(reference=int(self))).play()

    def text(self):
        if self._text is None:
            self._text = Text(self._get(self._GET_TEXT_ENDPOINT_TEMPLATE.format(reference=str(self)))["passages"][0])
        return self._text


class Chapter(_api.Chapter):
    pass


class Book(_api.Book):
    pass


class Translation(ESVAPIMixin, _api.Translation):
    def search(self, query, page_size=100):
        page = 1
        while page is not None:
            response = self._get(self._GET_SEARCH_ENDPOINT_TEMPLATE.format(query=query, page_size=page_size, page=page))
            for result in response["results"]:
                book, chapter_verse = result["reference"].rsplit(" ", 1)
                chapter_number, verse_number = chapter_verse.split(":")
                verse = self[book][int(chapter_number)][int(verse_number)]
                verse._text = Text(result["content"])
                yield verse
            page = page + 1 if page != response["total_pages"] else None


class Passage(ESVAPIMixin, _api.Passage):
    @staticmethod
    def _chunk(iterable, size):
        iterator = iter(iterable)
        for first in iterator:
            yield itertools.chain([first], itertools.islice(iterator, size - 1))

    def audio(self):
        vlc.MediaPlayer(self._GET_AUDIO_URL_TEMPLATE.format(reference=str(self))).play()

    def text(self):
        verses = list(self.verses())
        textless_verses = [verse for verse in verses if verse._text is None]
        for chunk_index, verse_chunk in enumerate(self._chunk(textless_verses, self._MAX_VERSES_PER_TEXT_QUERY)):
            query = ",".join(str(int(verse)) for verse in verse_chunk)
            passages = self._get(self._GET_TEXT_ENDPOINT_TEMPLATE.format(reference=query))["passages"]
            for verse_index, passage in enumerate(passages):
                textless_verses[(chunk_index * self._MAX_VERSES_PER_TEXT_QUERY) + verse_index]._text = Text(passage)
        return " ".join(verse.text().body for verse in verses)


class Text(object):
    _TEXT_REGEX = re.compile(r"^(?:(?P<title>.+?\w)\n\n)?(?:(?P<body>.+?)\n\n)(?:Footnotes\n\n(?P<footnotes>.+?)\n)?$", flags=re.DOTALL)

    def __init__(self, raw_text):
        self._raw_text = raw_text
        match = self._TEXT_REGEX.match(raw_text)
        if match is None:
            print(self._TEXT_REGEX.pattern, repr(raw_text))
            raise ESVError("the raw_text did not match the expected pattern")
        groups = match.groupdict()
        self._title = groups["title"]
        self._body = groups["body"].replace("\n", "")
        footnotes = groups["footnotes"]
        self._footnotes = (footnotes.split("\n\n") if footnotes is not None else None)

    def __len__(self):
        return self._body.split()

    def __repr__(self):
        return self._body

    @property
    def body(self):
        return self._body

    @property
    def footnotes(self):
        return self._footnotes

    @property
    def title(self):
        return self._title


# TODO: Add a base.json which includes translation-agnostic historic details (author, chronology, original language - what about characters etc.)
