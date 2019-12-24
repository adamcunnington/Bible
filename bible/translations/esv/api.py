from bible import _api

import requests


class ESVAPI(object):
    _AUTH_HEADER = {"Authorization": "Token 8334f7ff2c3ca64e05da7afa4e47eaf9efba59cb"}
    _BASE_URL = "https://api.esv.org/v3/passage/"
    _GET_TEXT_URI_TEMPLATE = "text/?q={reference}"

    def audio(self):
        pass

    def text(self):
        return requests.get(self._BASE_URL + self._GET_TEXT_URI_TEMPLATE.format(reference=str(self)), headers=self._AUTH_HEADER).json()["passages"][0]


class Translation(ESVAPI, _api.Translation):
    pass


class Book(ESVAPI, _api.Book):
    pass


class Chapter(ESVAPI, _api.Chapter):
    pass


class Verse(ESVAPI, _api.Verse):
    pass


class Passage(ESVAPI, _api.Passage):
    pass


# TODO: FYI, the cacheing of data in _text or similar is the translation subpackage's job, not the standard API.
# TODO: FYI, Also, if text() will return some translation-specific text object with various attributes and special __len__ behaviour for
# counting words etc. for meta analysis, that is also the translation subpackage's job, not the standard API.
