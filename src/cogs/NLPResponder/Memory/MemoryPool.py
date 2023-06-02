import datetime
import json
import os.path
import pickle
from copy import deepcopy

import hnswlib
import numpy as np
from src.cogs.NLPResponder.Memory.Memory import Memory
from src.helpers.logging_config import logger
from src.helpers.StringMatchHelp import fuzzyMatchString
from tqdm import tqdm

DIM = 1536
MAX_MEMORIES = 10000
DISTANCE_FUNC = 'cosine'
EF = 20
EF_CONSTRUCTION = 200
M = 16

HNSW_FILENAME = "hnsw.pkl"
MEMORY_FILENAME = "memories_dict.json"


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


def get_similarity(hnsw, vec: list) -> float:
    result = hnsw.knn_query(vec, k=1, filter=None)
    return result[1].flatten()[0]


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
    def __init__(self, save_path="data/",
                 memory_list_init_path=None):
        """
        MemoryPool() -> empty memory pool
        MemoryPool(path) -> loads pool from file at path
        :param memory_file_path: path to file with JSON dict[int memory id, Memory]
        """
        self.save_path = save_path
        self.memory_file_path = save_path + MEMORY_FILENAME
        self.hnsw_file_path = save_path + HNSW_FILENAME
        # Declaring index
        self.hnsw = None
        self.memories: dict[int, Memory] = {}
        try:
            self.load_memories()
        except Exception as e:
            logger.warning(f"Could not load memories. Initializing new memory pool.\nError: {e}")
            self.hnsw = init_hnsw()
        if memory_list_init_path:
            with open(memory_list_init_path, 'r') as f:
                lines = f.read().split('\n')
                lines = [l for l in lines if l != ""]
                print(f"Loading init memories from {memory_list_init_path}.")
                # If you want each memory to be a number of contiguous lines in the init file,
                # this number controls how many extra lines are in the memory.
                LINE_CONTEXT_LEN = 0
                for i in tqdm(range(len(lines))):
                    if i < LINE_CONTEXT_LEN:
                        continue
                    context_lines = lines[i - LINE_CONTEXT_LEN:i + 1]
                    line = '\n'.join(context_lines)
                    self.add(Memory(line))
                print("Done.")

        # self.clear_duplicate_memories()

    def get_num_memories(self):
        return len(self.memories)

    def delete_memory(self, mem_id):
        del self.memories[mem_id]
        self.hnsw.mark_deleted(mem_id)

    def get_memory_from_id(self, memory_id):
        return self.memories[memory_id] if memory_id in self.memories else None

    def get_strings(self, memory_ids: list):
        return [m.string for m in [self.get_memory_from_id(x) for x in memory_ids]]

    def clear_duplicate_memories(self):
        delete_ids = []
        traversed_ids = []
        keys = list(self.memories.keys())
        count_sad = 0
        for m_id in self.hnsw.get_ids_list():
            if m_id not in self.memories:
                count_sad += 1
                try:
                    self.hnsw.mark_deleted(m_id)
                except Exception as e:
                    print(e)
        for k in keys:
            if not self.memories[k]:
                del self.memories[k]
        for m in self.memories.values():
            similar = self.get_similar(m.embedding, k=5, filter=lambda x: x not in traversed_ids and x != m.id)
            flag = True
            i = 0
            while flag and i < len(similar):
                m2_tuple = similar[i]
                m2_id = m2_tuple[0]
                m2 = self.memories[m2_id]
                if fuzzyMatchString(m.string, m2.string)[1] > 0.95:
                    print(f"Match: {m.id}: {m.string} ==== {m2.id}: {m2.string}\nDeleting.")
                    self.hnsw.mark_deleted(m.id)
                    traversed_ids.append(m.id)
                    delete_ids.append(m.id)
                    flag = False
                i += 1

        for x in delete_ids:
            self.memories[x] = None
        self.save_memories()

    def get_similar(self, vec: list, k=5, **kwargs) -> list:
        _k = min(k, self.get_num_memories())
        result = self.hnsw.knn_query(vec, k=_k, **kwargs)
        result = result[0].flatten(), result[1].flatten()
        label_dist_list = list(zip(*result))
        return label_dist_list

    def get_similar_mem_ids(self, vec: list, k=5, **kwargs) -> list:
        # turn this into a normal list
        result = self.get_similar(vec, k=k, **kwargs)
        return [x[0] for x in result]

    def get_memory_from_id(self, memory_id):
        return self.memories[memory_id]

    def get_strings(self, memory_ids: list):
        return [m.string for m in [self.get_memory_from_id(x) for x in memory_ids]]

    def add_memories(self, memories: list[Memory]):
        pass

    def add(self, memory: Memory):
        self.memories[memory.id] = memory
        m_arr = np.array([memory.embedding])
        ids = np.array([memory.id])
        self.hnsw.add_items(m_arr, ids)
        self.save_memories()

    def save_memories(self, backup=False):
        if backup:
            hnsw_path = os.path.join(self.save_path, "backup_" + HNSW_FILENAME)
            memory_path = os.path.join(self.save_path, "backup_" + MEMORY_FILENAME)
        else:
            hnsw_path = self.hnsw_file_path
            memory_path = self.memory_file_path
        with open(hnsw_path, 'wb') as f:
            pickle.dump(self.hnsw, f)
        with open(memory_path, 'w') as f:
            json.dump(self.memories, f, cls=MemoryEncoder)

    def load_memories(self):
        with open(self.hnsw_file_path, 'rb') as f:
            self.hnsw = pickle.load(f)
        with open(self.memory_file_path, 'r') as f:
            self.memories = json.load(f, object_hook=memory_decoder)
        self.save_memories(backup=True)


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
    labels_distances = m.get_similar(Memory("""Boris
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
    Awwwww""").embedding, 3)

    labels_distances = sorted(labels_distances, key=lambda x: x[1], reverse=True)
    for t in labels_distances:
        print(f"{m.memories[t[0]]}: {t[1]}")
