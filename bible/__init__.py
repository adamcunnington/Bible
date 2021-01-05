import dotenv

from bible import utils
import bible.translations.esv


dotenv.load_dotenv()

esv = utils.load_translation(bible.translations.esv.__name__)
