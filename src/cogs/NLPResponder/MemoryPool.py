import datetime
import json
import pickle

import hnswlib
import numpy as np
from Memory import Memory
from src.helpers.logging_config import logger

DIM = 1536
MAX_MEMORIES = 10000
DISTANCE_FUNC = 'l2'
#DISTANCE_FUNC = 'cosine'
EF = 20
EF_CONSTRUCTION = 200
M = 16

HNSW_PKL_PATH = "data/hnsw.pkl"
MEMORY_DICT_PATH = "data/memories_dict.pkl"


def init_hnsw():
    # possible options are l2, cosine or ip
    hnsw = hnswlib.Index(space=DISTANCE_FUNC, dim=DIM)
    # Controlling the recall by setting ef:
    # higher ef leads to better accuracy, but slower search
    hnsw.set_ef(EF)

    # Initializing index
    # max_elements - the maximum number of elements (capacity). Will throw an exception if exceeded
    # during insertion of an element.
    # The capacity can be increased by saving/loading the index, see below.
    #
    # ef_construction - controls index search speed/build speed tradeoff
    #
    # M - is tightly connected with internal dimensionality of the data. Strongly affects memory consumption (~M)
    # Higher M leads to higher accuracy/run_time at fixed ef/efConstruction
    hnsw.init_index(max_elements=MAX_MEMORIES // 2, ef_construction=EF_CONSTRUCTION, M=M)

    return hnsw


class MemoryPool:
    def __init__(self, memory_file_path=None, hnsw_file_path=None):
        """
        MemoryPool() -> empty memory pool
        MemoryPool(path) -> loads pool from file at path
        :param memory_file_path: path to file with JSON dict[int memory id, Memory]
        """
        self.memory_file_path = memory_file_path
        self.hnsw_file_path = hnsw_file_path
        # Declaring index
        self.hnsw = None
        self.memories: dict = {}
        try:
            self.load_memories()
        except Exception as e:
            logger.warning(f"Could not load memories. Initializing new memory pool.\nError: {e}")
            self.hnsw = init_hnsw()
            self.memories: dict[int, Memory] = {}

    def get_similar(self, memory: Memory, k=5):
        labels, distances = self.hnsw.knn_query(memory, k=k, filter=None)
        return labels, distances

    def get_memory(self, memory_id):
        return self.memories[memory_id]

    def get_strings(self, memory_ids: list):
        return [m.string for m in [self.get_memory(x) for x in memory_ids]]

    def add_memories(self, memories: list[Memory]):
        pass

    def add(self, memory: Memory):
        self.memories[memory.id] = memory
        m_arr = np.array([memory])
        ids = np.array([memory.id])
        self.hnsw.add_items(m_arr, ids)
        self.save_memories()

    def save_memories(self):
        with open(self.hnsw_file_path, 'wb') as f:
            pickle.dump(self.hnsw, f)
        with open(self.memory_file_path, 'w') as f:
            json.dump(self.memories, f)

    def load_memories(self):
        with open(self.hnsw_file_path, 'rb') as f:
            self.hnsw = pickle.load(f)
        with open(self.memory_file_path, 'w') as f:
            self.memories = json.load(f)

    def __setitem__(self, key, value):
        raise TypeError("Cannot use [] to set item in MemoryPool. Use add_memory(string).")


def demo():
    m = MemoryPool()
    m.add(Memory("Steven is a butt", datetime.datetime.now()))
    m.add(Memory("Steven eats shoes", datetime.datetime.now()))
    m.add(Memory("Kristian likes forests", datetime.datetime.now()))
    m.add(Memory("I want to help Steven", datetime.datetime.now()))
    m.add(Memory("I like trains", datetime.datetime.now()))
    m.add(Memory("Alec smiles when he gets a crazy idea", datetime.datetime.now()))
    m.add(Memory("Rock-climbing is a Kristian thing", datetime.datetime.now()))
    m.add(Memory("I want to tell Kristian about Apple inc", datetime.datetime.now()))
    m.add(Memory("I want to make an impression on people", datetime.datetime.now()))
    m.add(Memory("Whenever Steven compliments me, I wink", datetime.datetime.now()))
    m.add(Memory("Bouldering is awesome", datetime.datetime.now()))
    m.add(Memory("Kristian's shoes were eaten", datetime.datetime.now()))
    labels, distances = m.get_similar(Memory("""Boris
    BOT
     — 04/09/2023 4:34 PM
    Oh yeah, I remember that! You were pretty impressed with my toki pona skills, weren't ya? I gotta say, it's a pretty neat language.
    I'll give you a jan S∅ja! — 04/09/2023 4:35 PM
    YOU'RE AMAZIBG AT IT BORIS
    Boris
    BOT
     — 04/09/2023 4:35 PM
    Aw shucks, Steven, you're makin' me blush! I'm just doin' my best to impress ya.
    TenebumbilicalSeashanty — 04/09/2023 4:35 PM
    Awwwww""", datetime.datetime.now()), 3)

    indices = np.argsort(distances, axis=1)[:, ::-1][0]
    distances = distances[:, indices]
    labels = labels[:, indices]
    for i in range(labels.shape[1]):
        print(f"{m.memories[labels[0, i]]}: {distances[0, i]}")
