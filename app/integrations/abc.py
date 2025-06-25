from abc import ABC, abstractmethod


class IntegrationConfig(ABC):
    name = None
    available_tools = None
    system_prompt = None
    request_types = None

    @abstractmethod
    def __init__(self):
        pass

    @classmethod
    def from_name(cls, name):
        subclasses = {subclass.name: subclass for subclass in cls.__subclasses__()}
        subclass = subclasses.get(name)

        if subclass is None:
            # Default to 'graph-chat' if unknown
            subclass = subclasses.get('graph-chat')

        return subclass()

    @classmethod
    def list_integrations(cls):
        return [subclass.name for subclass in cls.__subclasses__()]

