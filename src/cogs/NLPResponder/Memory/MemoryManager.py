from src.helpers import GPTHelper
from src.cogs.NLPResponder.Context import Context
from src.helpers.StringMatchHelp import fuzzyMatchString
from src.cogs.NLPResponder.Conversation import Conversation
from src.cogs.NLPResponder.Memory.Memory import Memory, update_mem_scores
from src.cogs.NLPResponder.Memory.MemoryPool import MemoryPool
from src.helpers.Settings import settings
from src.helpers.logging_config import logger
from src.cogs.NLPResponder.Memory.MemoryPool import get_similarity


class MemoryManager:
    def __init__(self, memory_file_path, hnsw_file_path, memory_list_init=None):
        self._memory_pool: MemoryPool = MemoryPool(memory_file_path=memory_file_path, hnsw_file_path=hnsw_file_path,
            memory_list_init_path=memory_list_init
        )

    def get_memory_from_id(self, memory_id):
        return self._memory_pool.get_memory_from_id(memory_id)

    def get_memories_from_ids(self, memory_ids: list):
        return [self.get_memory_from_id(x) for x in memory_ids]

    def getAllMemories(self) -> list[str]:
        return [m.string for m in self._memory_pool.memories.values()]

    def calculate_memory_score_from_similarity(self, memory: Memory, response):
        sim = get_similarity(self._memory_pool.hnsw, memory.embedding)
        memory.score += sim

    def get_memories_related(self, memory: Memory):
        self._memory_pool.get_similar(memory.embedding)

    def get_memory_list(self, num: int, newest=True):
        if newest:
            sorted_mems = sorted(self._memory_pool.memories.values(), key=lambda x: x.timestamp, reverse=True)
        else:
            sorted_mems = sorted(self._memory_pool.memories.values(), key=lambda x: x.timestamp)

        return sorted_mems[:num]

    def delete_memory(self, mem_id):
        self._memory_pool.delete_memory(mem_id)

    def get_similar_mem_ids_from_str(self, input_str: str, k=5, **kwargs) -> list:
        input_embed = GPTHelper.getEmbedding(input_str)
        return self.get_similar_mem_ids_from_embed(input_embed, k=k, **kwargs)

    def get_similar_mem_ids_from_embed(self, embed: list, k=5, **kwargs) -> list:
        return self._memory_pool.get_similar_mem_ids(embed, k=k, **kwargs)

    def get_strings_from_ids(self, memory_ids: list):
        return self._memory_pool.get_strings(memory_ids)

    # TODO Add separate memory pools for each context (once memory db is implemented)
    def getMemoryPools(self, pools: list[str]) -> list[Context]:
        result = []
        for p in pools:
            if p not in self.contexts:
                logging.error(f"Pool {p} does not exist in bot memory.")
            else:
                result.append(self.contexts[p])
        return result

    def update_memories_scores_from_ids(self, compare_embed: list, memory_ids: list[int]):
        memories = self.get_memories_from_ids(memory_ids)
        self.update_memories_score_from_memory_list(compare_embed, memories)

    def update_memories_score_from_memory_list(self, compare_embed: list, memories: list[Memory]):
        update_mem_scores(compare_embed, memories)

    def save_memories_to_json(self):
        self._memory_pool.save_memories()

    async def save_memory(self, mem_str: str, conversation: Conversation, memory_match_prob: float = None, shrink=True,
                          explain=True,
                          compare_str: str = None,
                          compare_embed: list = None):
        m = Memory(mem_str)
        if not memory_match_prob:
            memory_match_prob = settings.memory_match_prob
        m_id_dist_list = self._memory_pool.get_similar(m.embedding, 3, filter=lambda x: x != m.id)
        if len(m_id_dist_list) > 0:
            for similar_mem_tuple in m_id_dist_list:
                m_id = similar_mem_tuple[0]
                similarity = similar_mem_tuple[1]
                similar_mem: Memory = self.get_memory_from_id(m_id)
                fuzzy_match_similarity = fuzzyMatchString(similar_mem.string, m.string)[1]
                if fuzzy_match_similarity > memory_match_prob:
                    logger.info(
                        f"Not saving memory. Too close to {similar_mem.string}, similarity {similarity}, fuzzymatch: {fuzzy_match_similarity}")
                    return
        self._memory_pool.add(m)
        conversation.add_memory(m, compare_str=compare_str, compare_embed=compare_embed)
        return m

    def get_context_memories(self, embed: list, id_memory_dict=None, conversation=None, n=3) -> list[Memory]:
        memory_ids = None
        if id_memory_dict or conversation:
            memory_ids = id_memory_dict.keys() if id_memory_dict else conversation.get_memory_ids()
        if memory_ids:
            context_memories_ids = self.get_similar_mem_ids_from_embed(embed, k=n, filter=lambda x: x not in memory_ids)
        else:
            context_memories_ids = self.get_similar_mem_ids_from_embed(embed, k=n, filter=lambda x: x not in memory_ids)
        context_memories = self.get_memories_from_ids(context_memories_ids)
        logger.info("Contextual memories:\n" + '\n'.join([str(m) for m in context_memories]))
        return context_memories

    def get_reply_memories(self, conversation: Conversation,
                           context_memories=None,
                           context_string: str = None) -> list[Memory]:
        # context_memories: a list of Memory objects
        # context_string: the chatlog formatted as a str. will be used to find contextual memories in memory pool.
        # markdown: if true, will wrap the list of memories in a code block labeled 'memories'
        conversation_memories = self.get_memories_from_ids(conversation.get_memory_ids())
        id_memory_dict = {x.id: x for x in conversation_memories}
        if not context_memories and context_string:
            context_memories = self.get_context_memories(context_string, id_memory_dict=id_memory_dict)
        if context_memories:
            for m in context_memories:
                id_memory_dict[m.id] = m
        return list(id_memory_dict.values())

    def get_memories_string(self, memories: list[Memory], markdown=True):
        memory_strings = [m.string for m in memories]
        newline_memories = '\n'.join(memory_strings)
        if len(memory_strings) > 0:
            return f"```memories\n{newline_memories}\n```\n" if markdown else newline_memories + '\n'
        else:
            return ""
