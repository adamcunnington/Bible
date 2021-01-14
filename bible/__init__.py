import dotenv

from bible import utils
import bible.translations.esv.api


dotenv.load_dotenv()


def esv():
    return utils.load_translation(bible.translations.esv.api)
