from fuzzywuzzy import fuzz


class FuzzyDefaultDict(dict):
    def __init__(self, *args, **kwargs):
        self.ratio_threshold = kwargs.pop("ratio_threshold", 60)
        self.default_factory = kwargs.pop("default_factory", None)
        super().__init__(*args, **kwargs)

    def __contains__(self, key):
        return self.search(key, return_first=True)[0]

    def __getitem__(self, key):
        matched, closest_key, closest_value, ratio = self.search(key)
        if not matched:
            return self.__missing__(key, closest_key, ratio)
        return closest_value

    def __missing__(self, key, closest_key, ratio):
        if self.default_factory is None:
            if closest_key is None:
                raise KeyError(key)
            raise KeyError(f"'{key}'. The closest match was {closest_key} but with a ratio ({ratio}) < the threshold ({self.ratio_threshold})")
        value = self[key] = self.default_factory()
        return value

    def search(self, key, return_first=False, ratio_threshold_override=None):
        if super().__contains__(key):
            return (True, key, super().__getitem__(key), 1)
        if not isinstance(key, str):
            return (False, key, None, 0)
        closest_key = None
        closest_ratio = 0
        ratio_threshold = ratio_threshold_override or self.ratio_threshold
        for existing_key in self:
            if not isinstance(existing_key, str):
                continue
            ratio = fuzz.partial_ratio(key, existing_key)
            if ratio > closest_ratio:  # if it's the same, we will favour the one found first; deterministic as python dicts retain order from 3.7
                closest_ratio = ratio
                closest_key = existing_key
                if return_first and closest_ratio >= ratio_threshold:
                    break
        return (closest_ratio >= ratio_threshold, closest_key, self.get(closest_key), closest_ratio)
