import importlib
import json
import os
import sys

from fuzzywuzzy import fuzz
import jsonmerge


# INTERNALS
_json_merge_schema = {
    "properties": {
        "books": {
            "mergeStrategy": "arrayMergeByIndex"
        }
    }
}


class FuzzyDict(dict):
    def __init__(self, *args, **kwargs):
        self.ratio_threshold = kwargs.pop("ratio_threshold", 60)
        super().__init__(*args, **kwargs)

    def __getitem__(self, key):
        matched, closest_key, closest_value, ratio = self.search(key)
        if not matched:
            if closest_key is None:
                raise KeyError(key)
            raise KeyError(f"'{key}'. The closest match was {closest_key} but with a ratio ({ratio}) < the threshold ({self.ratio_threshold})")
        return closest_value

    def search(self, key, return_first=False, ratio_threshold_override=None):
        if key in self:
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


def module_of_instance(self):
    return sys.modules[self.__class__.__module__]


def load_translation(module_name):
    with open(os.path.join(os.path.dirname(__file__), "data", "base.json")) as f:
        base_data = json.load(f)
    module = sys.modules[module_name]
    module_package_name = module_name.rsplit(".", 1)[1]
    file_path = os.path.join(os.path.dirname(module.__file__), "data", f"{module_package_name}.json")
    api_module = importlib.import_module(f"{module_name}.api")
    with open(file_path) as f:
        translation_data = json.load(f)
    data = jsonmerge.Merger(_json_merge_schema).merge(base_data, translation_data)
    translation = api_module.Translation(data["translation_meta"]["name"])
    for book_index, book_data in enumerate(data["books"]):
        book = api_module.Book(book_data["name"], book_index + 1, translation, book_data["author"], book_data["language"],
                               alt_names=book_data.get("alt_names", ()), categories=book_data.get("categories", ()))
        for chapter_index, verse_count in enumerate(book_data["chapter_verses"]):
            chapter = api_module.Chapter(chapter_index + 1, book)
            for verse_index in range(verse_count):
                _ = api_module.Verse(verse_index + 1, chapter)
    return translation


def unique_value_iterating_dict(d):
    iter(dict.fromkeys(d.values()))  # ordered set from dict values
