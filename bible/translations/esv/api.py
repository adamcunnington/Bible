import itertools
import os
import re

import requests
import vlc

from bible import api


# ENVIRONMENT VARIABLES
_ESV_API_TOKEN_ENV_VAR = "ESV_API_TOKEN"


# INTERNALS
_AUDIO_CACHE_FILE_PATH_TEMPLATE = "/tmp/bible/{file_name}.mp3"

_default_page_size = 100


class ESVError(Exception):
    pass


class ESVAPIMixin:
    _BASE_URL = "https://api.esv.org/v3/passage/"
    _GET_AUDIO_ENDPOINT_TEMPLATE = "audio/?q={query}"
    _GET_SEARCH_ENDPOINT_TEMPLATE = "search/?q={query}&page-size={page_size}&page={page}"
    _GET_TEXT_ENDPOINT_TEMPLATE = ("text/?q={reference}&include-passage-references=false&include-verse-numbers=true&"
                                   "include-first-verse-numbers=true&include-footnotes=true&included-footnote-body=true&include-headings=true&"
                                   "include-short-copyright=false&include-passage-horizontal-lines=false&include-heading-horizontal-lines=false&"
                                   "include-selahs=true&indent-paragraphs=0&indent-poetry=false&indent-declares=0&indent-psalm-doxology=0&"
                                   "line-length=0")
    _MAX_VERSES_PER_AUDIO_QUERY = 500
    _MAX_VERSES_PER_TEXT_QUERY = 400

    def __init__(self, *args, **kwargs):
        self._text = None
        self._api_token = kwargs.pop("api_token", None)
        super().__init__(*args, **kwargs)

    @staticmethod
    def _chunk(iterable, size):
        iterator = iter(iterable)
        for first in iterator:
            yield itertools.chain([first], itertools.islice(iterator, size - 1))

    def _audio(self, reference):
        audio_file_path = _AUDIO_CACHE_FILE_PATH_TEMPLATE.format(file_name=reference)
        if not os.path.isfile(audio_file_path):
            os.makedirs(os.path.dirname(audio_file_path), exist_ok=True)
            with open(audio_file_path, "wb") as f:
                f.write(self._get_bytes(self._GET_AUDIO_ENDPOINT_TEMPLATE.format(query=reference)))
        vlc.MediaPlayer(audio_file_path).play()

    def _get(self, endpoint_uri):
        token = os.getenv(_ESV_API_TOKEN_ENV_VAR)
        if token is None:
            raise ESVError(f"the environment variable, {_ESV_API_TOKEN_ENV_VAR} is not set")
        response = requests.get(self._BASE_URL + endpoint_uri, headers={"Authorization": f"Token {token}"})
        if not response.ok:
            response.raise_for_status()
        return response

    def _get_bytes(self, endpoint_uri):
        return self._get(endpoint_uri).content

    def _get_json(self, endpoint_uri):
        return self._get(endpoint_uri).json()

    def audio(self):
        self._audio(self.int_reference)

    def text(self):
        textless_verses = [verse for verse in self.verses() if verse._text is None]
        for chunk_index, verse_chunk in enumerate(self._chunk(textless_verses, self._MAX_VERSES_PER_TEXT_QUERY)):
            query = ",".join(verse.int_reference for verse in verse_chunk)
            passages = self._get_json(self._GET_TEXT_ENDPOINT_TEMPLATE.format(reference=query))["passages"]
            for verse_index, passage in enumerate(passages):
                verse = textless_verses[(chunk_index * self._MAX_VERSES_PER_TEXT_QUERY) + verse_index]
                verse._text = ESVText(passage, verse.chapter.number if verse.number == 1 else None)
        return " ".join(verse.text().body for verse in self.verses())


class ESVText:
    _TEXT_REGEX = re.compile(r"^(?P<title>.+?)?(?P<body>\[\d+\].+?)(?:Footnotes(?P<footnotes>.+))?$")
    _FOOTNOTES_REGEX = re.compile(r"\((\d+)\) \d+:\d+ (.+?)(?=\(\d+\) |$)")

    def __init__(self, raw_text, chapter=None):
        self._raw_text = raw_text
        match = self._TEXT_REGEX.match(raw_text.replace("\n", ""))
        if match is None:
            raise ESVError("the raw_text from the response did not match the expected pattern")
        groups = match.groupdict()
        self._title = groups["title"]
        self._body = (f"{{{chapter}}}" if chapter else '') + groups["body"]
        footnotes = groups["footnotes"]
        self._footnotes = dict(self._FOOTNOTES_REGEX.findall(footnotes)) if footnotes is not None else {}

    def __len__(self):
        return len(self._body.split())

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


class Verse(ESVAPIMixin, api.Verse):
    def text(self):
        if self._text is None:
            self._text = ESVText(self._get_json(self._GET_TEXT_ENDPOINT_TEMPLATE.format(reference=str(self)))["passages"][0])
        return self._text


class Chapter(ESVAPIMixin, api.Chapter):
    pass


class Book(ESVAPIMixin, api.Book):
    pass


class Translation(ESVAPIMixin, api.Translation):
    def audio(self):
        raise NotImplementedError()

    def search(self, query):
        page = 1
        while page is not None:
            response = self._get_json(self._GET_SEARCH_ENDPOINT_TEMPLATE.format(query=query, page_size=_default_page_size, page=page))
            for result in response["results"]:
                book, chapter_verse = result["reference"].rsplit(" ", 1)
                chapter_verse_split = chapter_verse.split(":")
                if len(chapter_verse_split) == 1:
                    chapter_number = 1
                    verse_number = chapter_verse_split[0]
                else:
                    chapter_number, verse_number = chapter_verse_split
                verse = self[book][int(chapter_number)][int(verse_number)]
                verse._text = ESVText(result["content"])
                yield verse
            page = page + 1 if page != response["total_pages"] else None

    def text(self):
        raise NotImplementedError()


class Passage(ESVAPIMixin, api.Passage):
    def audio(self):
        self._audio(self.int_reference)


class Character(api.Character):
    pass

