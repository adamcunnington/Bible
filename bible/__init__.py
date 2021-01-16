import dotenv

from bible import utils
from bible.translations.esv import api as esv_api


dotenv.load_dotenv()


def esv():
    return utils.load_translation(translation_cls=esv_api.Translation, book_cls=esv_api.Book, chapter_cls=esv_api.Chapter, verse_cls=esv_api.Verse,
                                  passage_cls=esv_api.Passage)
