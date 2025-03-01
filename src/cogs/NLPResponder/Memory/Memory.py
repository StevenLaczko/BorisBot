import datetime
import json
import uuid
from copy import deepcopy

from scipy.spatial.distance import cosine

from src.helpers.GPTHelper import getEmbedding
from src.helpers.logging_config import logger


# Custom encoder to serialize datetime objects
class MemoryEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Memory):
            d = deepcopy(obj.__dict__)
            d["timestamp"] = obj.timestamp.isoformat()
            return d
        return super().default(obj)


# Custom decoder to deserialize datetime objects
def memory_decoder(obj):
    if "embedding" in obj:
        obj["timestamp"] = datetime.datetime.fromisoformat(obj["timestamp"])
        m = Memory("", embedding=[])
        m.__dict__.update(obj)
        return m
    else:
        new_obj = {}
        for k in obj.keys():
            new_obj[int(k)] = obj[k]
    return new_obj


def fnv1a_32(s: bytes) -> int:
    """
    Implementation of FNV-1a 32-bit hash function.
    """
    # FNV-1a constants
    FNV_OFFSET = 2166136261
    FNV_PRIME = 16777619

    # Initialize the hash value with the offset basis
    hash_value = FNV_OFFSET

    # XOR and multiply each byte in the input string with the hash value
    for b in s:
        hash_value ^= b
        hash_value *= FNV_PRIME

    # Return the hash value as a 32-bit unsigned integer
    return hash_value & 0xffffffff


def get_32_int_guid() -> int:
    # convert the UUID to a SHA-256 hash digest, then to an int
    my_uuid = str(uuid.uuid4()).encode('utf-8')
    uuid_int = fnv1a_32(my_uuid)
    return uuid_int


def cosine_similarity(v1, v2):
    """Returns the cosine similarity between two vectors"""
    return 1 - cosine(v1, v2)


def update_mem_scores(compare_embed, memories: list):
    logger.info("Updating memory scores.")
    logger.info("Memory scores before:")
    [logger.info(f"{m.score} - {m.string}") for m in memories]
    logger.info("Memory scores after:")
    [m.update_memory_score_from_embedding(compare_embed) for m in memories]
    [logger.info(f"{m.score} - {m.string}") for m in memories]


class Memory:
    def __init__(self, string, timestamp=None, embedding=None, mem_id=None):
        self.string: str = string.strip()
        self.timestamp: datetime.datetime = timestamp if timestamp else datetime.datetime.now()
        self.embedding: list = embedding if embedding is not None else self.generate_embedding()
        self.id: int = mem_id if mem_id else get_32_int_guid()
        self.score: float = 0

    def update_memory_score_from_embedding(self, compare_embed: list):
        sim = cosine_similarity(compare_embed, self.embedding)
        self.score += sim
        self.score /= 2

    def generate_embedding(self) -> list:
        e = getEmbedding(self.string)
        self.embedding = e
        return self.embedding

    def __len__(self):
        return len(self.embedding)

    def __getitem__(self, i):
        return self.embedding[i]

    def __repr__(self):
        return f"id: {self.id}, timestamp: {self.timestamp}, score: {self.score}, text: '{self.string}'"
