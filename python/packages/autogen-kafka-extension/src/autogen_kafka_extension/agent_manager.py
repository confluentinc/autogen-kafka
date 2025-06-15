import inspect
import warnings
from typing import Dict, Callable, Awaitable, cast, TypeVar, Type

from autogen_core import (
    AgentRuntime, Agent, AgentId, AgentInstantiationContext, AgentType
)
from autogen_core._single_threaded_agent_runtime import type_func_alias
from autogen_kafka_extension.agent_registry import AgentRegistry

T = TypeVar("T", bound=Agent)


class AgentManager:
    """Manages agent factories, instances, and registration."""
    
    def __init__(self, runtime: AgentRuntime):
        self._runtime = runtime
        self._agent_factories: Dict[
            str, Callable[[], Agent | Awaitable[Agent]] | Callable[[AgentRuntime, AgentId], Agent | Awaitable[Agent]]
        ] = {}
        self._instantiated_agents: Dict[AgentId, Agent] = {}
        self._agent_instance_types: Dict[str, Type[Agent]] = {}
    
    async def register_factory(
        self,
        type: str | AgentType,
        agent_factory: Callable[[], T | Awaitable[T]],
        agent_registry: AgentRegistry,
        *,
        expected_class: type[T] | None = None
    ) -> AgentType:
        """Register a factory for creating agents of a given type."""
        if isinstance(type, str):
            type = AgentType(type)

        if type.type in self._agent_factories:
            raise ValueError(f"Agent with type {type} already exists.")
        if agent_registry.is_registered(type):
            raise ValueError(f"Agent type {type.type} already registered")

        async def factory_wrapper() -> T:
            maybe_agent_instance = agent_factory()
            if inspect.isawaitable(maybe_agent_instance):
                agent_instance = await maybe_agent_instance
            else:
                agent_instance = maybe_agent_instance

            if expected_class is not None and type_func_alias(agent_instance) != expected_class:
                raise ValueError("Factory registered using the wrong type.")

            return agent_instance

        self._agent_factories[type.type] = factory_wrapper
        await agent_registry.register_agent(type)
        return type
    
    async def register_instance(self, agent_instance: Agent, agent_id: AgentId) -> AgentId:
        """Register a specific agent instance with a given ID."""
        def agent_factory() -> Agent:
            raise RuntimeError(
                "Agent factory was invoked for an agent instance that was not registered. This is likely due to the agent type being incorrectly subscribed to a topic. If this exception occurs when publishing a message to the DefaultTopicId, then it is likely that `skip_class_subscriptions` needs to be turned off when registering the agent."
            )

        if agent_id in self._instantiated_agents:
            raise ValueError(f"Agent with id {agent_id} already exists.")

        if agent_id.type not in self._agent_factories:
            self._agent_factories[agent_id.type] = agent_factory
            self._agent_instance_types[agent_id.type] = type_func_alias(agent_instance)
        else:
            if self._agent_factories[agent_id.type].__code__ != agent_factory.__code__:
                raise ValueError("Agent factories and agent instances cannot be registered to the same type.")
            if self._agent_instance_types[agent_id.type] != type_func_alias(agent_instance):
                raise ValueError("Agent instances must be the same object type.")

        await agent_instance.bind_id_and_runtime(id=agent_id, runtime=self._runtime)
        self._instantiated_agents[agent_id] = agent_instance
        return agent_id
    
    async def get_agent(self, agent_id: AgentId) -> Agent:
        """Retrieve or instantiate an agent by its ID."""
        if agent_id in self._instantiated_agents:
            return self._instantiated_agents[agent_id]

        if agent_id.type not in self._agent_factories:
            raise ValueError(f"Agent with name {agent_id.type} not found.")

        agent_factory = self._agent_factories[agent_id.type]
        agent = await self._invoke_agent_factory(agent_factory, agent_id)
        self._instantiated_agents[agent_id] = agent
        return agent
    
    async def try_get_underlying_agent_instance(self, id: AgentId, type: Type[T] = Agent) -> T:  # type: ignore[assignment]
        if id.type not in self._agent_factories:
            raise LookupError(f"Agent with name {id.type} not found.")

        agent_instance = await self.get_agent(id)
        if not isinstance(agent_instance, type):
            raise TypeError(f"Agent with name {id.type} is not of type {type.__name__}")

        return agent_instance
    
    async def _invoke_agent_factory(
        self,
        agent_factory: Callable[[], T | Awaitable[T]] | Callable[[AgentRuntime, AgentId], T | Awaitable[T]],
        agent_id: AgentId,
    ) -> T:
        """Invoke an agent factory, supporting both 0-arg and 2-arg signatures."""
        with AgentInstantiationContext.populate_context((self._runtime, agent_id)):
            params = inspect.signature(agent_factory).parameters
            if len(params) == 0:
                factory_one = cast(Callable[[], T], agent_factory)
                agent = factory_one()
            elif len(params) == 2:
                warnings.warn(
                    "Agent factories that take two arguments are deprecated. Use AgentInstantiationContext instead. Two arg factories will be removed in a future version.",
                    stacklevel=2,
                )
                factory_two = cast(Callable[[AgentRuntime, AgentId], T], agent_factory)
                agent = factory_two(self._runtime, agent_id)
            else:
                raise ValueError("Agent factory must take 0 or 2 arguments.")

            if inspect.isawaitable(agent):
                agent = cast(T, await agent)

        return agent 