
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntime, GrpcWorkerAgentRuntimeHost

from packages.exemple.sample import Sample


class GRPCSample(Sample):

    def __init__(self):
        super().__init__(runtime=GrpcWorkerAgentRuntime("localhost:50051"))

        host = GrpcWorkerAgentRuntimeHost(address="localhost:50051")
        host.start()  # Start a host service in the background.

    async def _start(self):
        await self._runtime.start()

    async def stop(self):
        await self._runtime.stop()
