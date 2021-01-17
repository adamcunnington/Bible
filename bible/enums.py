import enum


class CharacterGender(enum.Enum):
    MALE = "Male"
    FEMALE = "Female"


class CharacterCauseOfDeath(enum.Enum):
    MURDERED_BY_CAIN = "Murdered by Cain"
    OLD_AGE = "Old Age"
    TAKEN_TO_HEAVEN = "Taken to Heaven"


class CharacterNationality(enum.Enum):
    EARTH = "Earth"
    EDEN = "Eden"


class CharacterPlaceOfDeath(enum.Enum):
    pass


class CharacterPrimaryOccupation(enum.Enum):
    pass
