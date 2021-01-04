import dotenv

from bible import utils
from bible.translations import esv as _esv


dotenv.load_dotenv()

esv = utils.load_translation(_esv.__name__)
