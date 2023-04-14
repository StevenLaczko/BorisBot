import abc


class Command(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def _parse(self, input: str):
        pass

    @abc.abstractmethod
    def _execute(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        self._execute(args, kwargs)
