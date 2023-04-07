import json
import uuid
from Memory import Memory


class MemoryPool(dict[uuid.UUID, Memory]):
    def __init__(self, path=None):
        """
        MemoryPool() -> empty memory pool
        MemoryPool(path) -> loads dict from json file at path
        :param path:
        """
        super().__init__()
        if path:
            self.create(path)

    def create(self, path):
        with open(path, 'r') as f:
            self.update(json.load(f))

    def add_memory(self, string):
        guid = uuid.uuid4()
        self[guid] = string
        return guid

    def __setitem__(self, key, value):
        raise TypeError("Cannot use [] to set item in MemoryPool. Use add_memory(string).")

    def get_strings(self, id_list):
        memories = [self[k].string for k in id_list]
