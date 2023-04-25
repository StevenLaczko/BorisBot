import datetime
import math
import uuid

from src.cogs.NLPResponder import GPTHelper
from src.cogs.NLPResponder.GPTHelper import getEmbedding
from src.helpers.logging_config import logger


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
    dot_product = sum(x * y for x, y in zip(v1, v2))
    magnitude_v1 = math.sqrt(sum(x ** 2 for x in v1))
    magnitude_v2 = math.sqrt(sum(x ** 2 for x in v2))
    return dot_product / (magnitude_v1 * magnitude_v2)


def update_mem_scores(response_embed, memories: list):
    [m.update_memory_score_from_response_embedding(response_embed) for m in memories]
    logger.info("Memory scores updated:")
    [logger.info(f"{m.score} - {m.string}") for m in memories]


class Memory:
    def __init__(self, string, timestamp=None, embedding=None, mem_id=None):
        self.string: str = string.strip()
        self.timestamp: datetime.datetime = timestamp if timestamp else datetime.datetime.now()
        self.embedding: list = embedding if embedding is not None else self.generate_embedding()
        self.id: int = mem_id if mem_id else get_32_int_guid()
        self.score: float = 0

    def update_memory_score_from_response_embedding(self, response_embed: list):
        sim = cosine_similarity(self.embedding, response_embed)
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
        return f"'{self.string}', timestamp: {self.timestamp}, score: {self.score}, embedding: {self.embedding[0:2]}..."
