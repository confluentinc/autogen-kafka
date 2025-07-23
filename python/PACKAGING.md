# Packaging and Publishing to PyPi

## Package the library for publication:

1. Make sure you have the latest `build` lib with: `python3 -m pip install --upgrade build`
2. Go to the autogen-kafka package folder: `cd python/packages/autogen-kafka`
3. Update the `pyproject.toml` file as required (version number and dependencies)
4. Build the package: `python -m build`, this adds distribution files to the `dist` folder.
5. You can test the build by installing it directly:
    ```shell
    mkvirtualenv testpypi
    pip install dist/autogen_kafka-0.1.5-py3-none-any.whl
    python
    >>> import autogen_kafka
    >>> modules = dir(autogen_kafka); print(modules)
   ['BackgroundTaskManager', 'BaseConfig', 'KafkaAgentConfig', 'KafkaAgentRuntime', 'KafkaAgentRuntimeConfig', 'KafkaAgentRuntimeFactory', 'KafkaConfig', 'KafkaMemory', 'KafkaMemoryConfig', 'KafkaMemoryError', 'KafkaStreamingAgent', 'KafkaUtils', 'MessagingClient', 'SchemaRegistryConfig', 'ServiceBaseConfig', 'StreamingService', 'StreamingServiceConfig', 'StreamingWorkerBase', 'SubscriptionService', 'TopicDeletionTimeoutError', '__all__', '__builtins__', '__cached__', '__doc__', '__file__', '__loader__', '__name__', '__package__', '__path__', '__spec__', '__version__', 'agent', 'config', 'memory', 'runtimes', 'shared']
    >>> 
    ```

## Push to PyPi

1. Make sure you have the latest `twine` lib with: `python3 -m pip install --upgrade twine`
2. Update your local `$HOME/.pypirc` file with the proper token following instructions on the `Onboarding Python Project to PyPi
` document of the Internal wiki.
3. Publish: `python3 -m twine upload dist/*`

