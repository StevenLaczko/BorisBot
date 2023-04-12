import hashlib
import uuid

from src.cogs.NLPResponder import GPTHelper


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


def get_32_int_guid():
    # convert the UUID to a SHA-256 hash digest, then to an int
    my_uuid = str(uuid.uuid4()).encode('utf-8')
    uuid_int = fnv1a_32(my_uuid)
    return uuid_int


class Memory:
    def __init__(self, string, timestamp, embedding=None):
        self.string = string
        self.timestamp = timestamp
        self.embedding = embedding if embedding is not None else self.get_embedding()
        self.id = get_32_int_guid()

    def get_embedding(self):
        return GPTAPI.getEmbedding(self.string)

    def __len__(self):
        return len(self.embedding)

    def __getitem__(self, i):
        return self.embedding[i]

    def __repr__(self):
        return f"{self.embedding[0:3]}... [{self.timestamp}]: {self.string}`"
