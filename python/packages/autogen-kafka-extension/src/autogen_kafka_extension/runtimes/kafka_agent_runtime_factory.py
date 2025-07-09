from .kafka_agent_runtime import KafkaAgentRuntime
from autogen_kafka_extension import KafkaAgentRuntimeConfig

class KafkaAgentRuntimeFactory:

    @staticmethod
    async def create_runtime(config: dict, timeout : int = 30) -> KafkaAgentRuntime:
        """
        Create a KafkaAgentRuntime instance from the provided configuration.

        Args:
            config (dict): The configuration dictionary containing Kafka settings.
            timeout (int): Optional timeout for starting the runtime. Defaults to 0 (no timeout).

        Returns:
            KafkaAgentRuntime: An instance of KafkaAgentRuntime configured with the provided settings.
        """
        return await KafkaAgentRuntimeFactory.create_runtime_from_config(KafkaAgentRuntimeConfig.from_dict(config), timeout)

    @staticmethod
    async def create_runtime_from_file(file_path: str, timeout: int = 30) -> KafkaAgentRuntime:
        """
        Create a KafkaAgentRuntime instance from a configuration file.

        Args:
            file_path (str): The path to the configuration file.
            timeout (int): Optional timeout for starting the runtime. Defaults to 30 seconds.

        Returns:
            KafkaAgentRuntime: An instance of KafkaAgentRuntime configured with the settings from the file.
        """
        return await KafkaAgentRuntimeFactory.create_runtime_from_config(KafkaAgentRuntimeConfig.from_file(file_path), timeout)

    @staticmethod
    async def create_runtime_from_config(runtime_confing: KafkaAgentRuntimeConfig, timeout: int = 30) -> KafkaAgentRuntime:
        """
        Create a KafkaAgentRuntime instance from a KafkaAgentRuntimeConfig object.

        Args:
            runtime_confing (KafkaAgentRuntimeConfig): The configuration object for the Kafka agent runtime.
            timeout (int): Optional timeout for starting the runtime. Defaults to 30 seconds.

        Returns:
            KafkaAgentRuntime: An instance of KafkaAgentRuntime configured with the provided settings.
        """
        runtime = KafkaAgentRuntime(runtime_confing)
        if timeout > 0:
            await runtime.start_and_wait_for(timeout=timeout)

        return runtime
