from typing import Type, Dict, List
from backend.agents.categories import CategoryType, CategoryManager
from backend.agents.base import AgentBase


class AgentRegistry:
    _agents: Dict[CategoryType, Dict[str, Type[AgentBase]]] = {
        cat: {} for cat in CategoryType
    }

    @classmethod
    def register(cls, category: CategoryType, name: str, agent_class: Type[AgentBase]):
        if category not in cls._agents:
            cls._agents[category] = {}
        cls._agents[category][name] = agent_class

    @classmethod
    def get_agents(cls, category: CategoryType) -> List[Type[AgentBase]]:
        return list(cls._agents.get(category, {}).values())

    @classmethod
    def get_agent(cls, category: CategoryType, name: str) -> Type[AgentBase]:
        return cls._agents.get(category, {}).get(name)
