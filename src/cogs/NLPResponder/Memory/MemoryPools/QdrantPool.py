import json
import os.path
import pickle

import numpy as np
from src.cogs.NLPResponder.Memory.Memory import Memory
from src.cogs.NLPResponder.Memory.MemoryPool import MemoryPool
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


class QdrantPool(MemoryPool):
    def __init__(self, save_path="data/qdrant",
                 memory_list_init_path=None):
        """
        MemoryPool() -> empty memory pool
        MemoryPool(path) -> loads pool from file at path
        :param memory_file_path: path to file with JSON dict[int memory id, Memory]
        """
        super().__init__()

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
