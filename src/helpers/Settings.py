import json
from configparser import ConfigParser


def lazy_property(func):
    attr_name = func.__name__

    @property
    def _lazy_property(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, func(self))
        return getattr(self, attr_name)

    return _lazy_property


class Settings:
    _instance = None
    
    def __new__(cls, config_file='data/settings.json'):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config_file = config_file
            cls._instance._cache_settings()
        return cls._instance

    def _cache_settings(self):
        with open(self._config_file, 'r') as f:
            self._config = json.load(f)

        self._id_name_dict = {int(k): v for k, v in self._config['id_name_dict'].items()}
        self._ignore_list = {int(k): v for k, v in self._config['ignore_list'].items()}
        self._log_level = self._config['log_level']
        self._max_context_words = self._config['conversation']['max_context_words']
        self._max_convo_words = self._config['conversation']['max_convo_words']
        self._max_memory_words = self._config['conversation']['max_memory_words']
        self._num_messages_per_request = self._config['conversation']['num_messages_per_request']
        self._context_path = self._config['conversation']['num_messages_per_request']
        self._prefix = self._config["prefix"]
        self._memory_match_prob = self._config["memory_match_prob"]
        self._opus = self._config["opus"]
        self._api_timeout = self._config["api_timeout"]
        self._chat_temperature = self._config["chat_temperature"]

    @property
    def id_name_dict(self):
        return self._id_name_dict

    @property
    def ignore_list(self):
        return self._ignore_list

    @property
    def log_level(self):
        return self._log_level

    @property
    def max_context_words(self):
        return self._max_context_words

    @property
    def max_convo_words(self):
        return self._max_convo_words

    @property
    def max_memory_words(self):
        return self._max_memory_words

    @property
    def num_messages_per_request(self):
        return self._num_messages_per_request

    @property
    def context_path(self):
        return self._context_path

    @property
    def prefix(self):
        return self._prefix

    @property
    def memory_match_prob(self):
        return self._memory_match_prob

    @property
    def opus(self):
        return self._opus

    @property
    def api_timeout(self):
        return self._api_timeout

    @property
    def chat_temperature(self):
        return self._chat_temperature

settings = Settings()
