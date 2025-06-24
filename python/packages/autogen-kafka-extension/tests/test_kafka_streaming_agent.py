import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch

from autogen_core import MessageContext, JSON_DATA_CONTENT_TYPE
from kstreams import ConsumerRecord, Stream, Send

from autogen_kafka_extension.agent.kafka_streaming_agent import KafkaStreamingAgent
from autogen_kafka_extension.agent.kafka_agent_config import KafkaAgentConfig
from autogen_kafka_extension.agent.event.agent_event import AgentEvent


class TestKafkaStreamingAgent:
    """Test suite for KafkaStreamingAgent class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock KafkaAgentConfig for testing."""
        config = Mock(spec=KafkaAgentConfig)
        config.request_topic = "test_request_topic"
        config.response_topic = "test_response_topic"
        config.name = "test_agent"
        config.group_id = "test_group"
        config.client_id = "test_client"
        config.bootstrap_servers = ["localhost:9092"]
        return config

    @pytest.fixture
    def mock_message_context(self):
        """Create a mock MessageContext for testing."""
        context = Mock(spec=MessageContext)
        context.sender = Mock()
        context.sender.__str__ = Mock(return_value="test_sender")
        return context

    @pytest.fixture
    def test_message(self):
        """Create a test message for testing."""
        return {"content": "test message", "type": "text"}

    @pytest.fixture
    def agent(self, mock_config):
        """Create a KafkaStreamingAgent instance for testing."""
        with patch('autogen_kafka_extension.agent.kafka_streaming_agent.SerializationRegistry'), \
             patch('autogen_kafka_extension.agent.kafka_streaming_agent.StreamingWorkerBase.__init__'):
            
            agent = KafkaStreamingAgent(
                config=mock_config,
                description="Test agent description"
            )
            
            # Set the config attribute that would normally be set by StreamingWorkerBase
            agent._config = mock_config
            
            # Mock the serialization registry methods
            agent._serialization_registry = Mock()
            agent._serialization_registry.type_name = Mock(return_value="test_type")
            agent._serialization_registry.is_registered = Mock(return_value=True)
            agent._serialization_registry.serialize = Mock(return_value=b'{"test": "data"}')
            
            # Mock the background task manager
            agent._background_task_manager = Mock()
            agent._background_task_manager.add_task = Mock()
            agent._background_task_manager.wait_for_completion = AsyncMock()
            
            return agent

    def test_init(self, mock_config):
        """Test KafkaStreamingAgent initialization."""
        with patch('autogen_kafka_extension.agent.kafka_streaming_agent.SerializationRegistry'), \
             patch('autogen_kafka_extension.agent.kafka_streaming_agent.StreamingWorkerBase.__init__'):
            
            agent = KafkaStreamingAgent(
                config=mock_config,
                description="Test agent description"
            )
            
            # Set the config attribute that would normally be set by StreamingWorkerBase
            agent._config = mock_config
            
            # Verify initialization
            assert agent._config == mock_config
            assert agent._pending_requests == {}
            assert agent._next_request_id == 0
            assert agent._pending_requests_lock is not None
            assert agent._background_task_manager is not None

    @pytest.mark.asyncio
    async def test_get_new_request_id(self, agent):
        """Test request ID generation."""
        # Test sequential ID generation
        id1 = await agent._get_new_request_id()
        id2 = await agent._get_new_request_id()
        id3 = await agent._get_new_request_id()
        
        assert id1 == "1"
        assert id2 == "2"
        assert id3 == "3"
        assert agent._next_request_id == 3

    @pytest.mark.asyncio
    async def test_get_new_request_id_concurrent(self, agent):
        """Test request ID generation under concurrent access."""
        # Test concurrent access to ensure thread safety
        async def get_id():
            return await agent._get_new_request_id()
        
        # Run multiple concurrent requests
        tasks = [get_id() for _ in range(10)]
        ids = await asyncio.gather(*tasks)
        
        # Verify all IDs are unique (order may vary due to async execution)
        assert len(set(ids)) == 10  # All unique
        # Convert to integers, verify they are in the expected range
        int_ids = [int(id_str) for id_str in ids]
        assert min(int_ids) == 1
        assert max(int_ids) == 10
        assert len(int_ids) == 10

    @pytest.mark.asyncio
    async def test_on_message_impl_new_message_type(self, agent, test_message, mock_message_context):
        """Test on_message_impl with a new message type that needs registration."""
        # Setup mocks
        agent._serialization_registry.is_registered.return_value = False
        agent._serialization_registry.add_serializer = Mock()
        
        with patch('autogen_kafka_extension.agent.kafka_streaming_agent.try_get_known_serializers_for_type') as mock_serializers, \
             patch('autogen_kafka_extension.agent.kafka_streaming_agent.StreamingWorkerBase.send_message', new_callable=AsyncMock) as mock_send:
            
            mock_serializers.return_value = Mock()
            
            # Create a future that we can control and resolve immediately
            test_future = asyncio.get_event_loop().create_future()
            test_future.set_result({"test": "response"})
            
            # Mock the background task manager to not actually run the task
            agent._background_task_manager.add_task = Mock()
            
            # Replace the create_future call to return our controlled future
            with patch('asyncio.get_event_loop') as mock_loop:
                mock_loop.return_value.create_future.return_value = test_future
                
                # Now we can await the method
                result = await agent.on_message_impl(test_message, mock_message_context)
            
            # Verify serializer was added for new message type
            agent._serialization_registry.add_serializer.assert_called_once()
            
            # Verify serialization was called
            agent._serialization_registry.serialize.assert_called_once_with(
                message=test_message,
                type_name="test_type",
                data_content_type=JSON_DATA_CONTENT_TYPE
            )
            
            # Verify background task was scheduled
            agent._background_task_manager.add_task.assert_called_once()
            
            # Verify the result
            assert result == {"test": "response"}

    @pytest.mark.asyncio
    async def test_on_message_impl_existing_message_type(self, agent, test_message, mock_message_context):
        """Test on_message_impl with an already registered message type."""
        # Setup mocks
        agent._serialization_registry.is_registered.return_value = True
        
        with patch('autogen_kafka_extension.agent.kafka_streaming_agent.StreamingWorkerBase.send_message', new_callable=AsyncMock) as mock_send:
            
            # Create a future that we can control and resolve immediately
            test_future = asyncio.get_event_loop().create_future()
            test_future.set_result({"test": "response"})
            
            # Mock the background task manager to not actually run the task
            agent._background_task_manager.add_task = Mock()
            
            # Replace the create_future call to return our controlled future
            with patch('asyncio.get_event_loop') as mock_loop:
                mock_loop.return_value.create_future.return_value = test_future
                
                # Now we can await the method
                result = await agent.on_message_impl(test_message, mock_message_context)
            
            # Verify serializer was NOT added (already registered)
            assert not hasattr(agent._serialization_registry, 'add_serializer') or \
                   agent._serialization_registry.add_serializer.call_count == 0
                   
            # Verify background task was scheduled
            agent._background_task_manager.add_task.assert_called_once()
                   
            # Verify the result
            assert result == {"test": "response"}

    @pytest.mark.asyncio
    async def test_handle_event_valid_response(self, agent):
        """Test _handle_event with a valid response event."""
        # Setup test data
        request_id = "test_request_id"
        test_response = {"result": "success", "data": "test_data"}
        
        # Create a future and add it to pending requests
        future = asyncio.get_event_loop().create_future()
        agent._pending_requests[request_id] = future
        
        # Create test event
        event = AgentEvent(
            id=request_id,
            message=json.dumps(test_response).encode(),
            message_type="response"
        )
        
        # Create mock record
        record = Mock(spec=ConsumerRecord)
        record.value = event
        
        # Create mock stream and send
        stream = Mock(spec=Stream)
        send = Mock(spec=Send)
        
        # Call the method
        await agent._handle_event(record, stream, send)
        
        # Verify the future was resolved with the correct result
        assert future.done()
        assert future.result() == test_response
        
        # Verify the request was removed from pending requests
        assert request_id not in agent._pending_requests

    @pytest.mark.asyncio
    async def test_handle_event_invalid_json(self, agent):
        """Test _handle_event with invalid JSON in the response."""
        # Setup test data
        request_id = "test_request_id"
        
        # Create a future and add it to pending requests
        future = asyncio.get_event_loop().create_future()
        agent._pending_requests[request_id] = future
        
        # Create test event with invalid JSON
        event = AgentEvent(
            id=request_id,
            message=b'invalid json{',
            message_type="response"
        )
        
        # Create mock record
        record = Mock(spec=ConsumerRecord)
        record.value = event
        
        # Create mock stream and send
        stream = Mock(spec=Stream)
        send = Mock(spec=Send)
        
        # Call the method
        await agent._handle_event(record, stream, send)
        
        # Verify the future was resolved with an exception
        assert future.done()
        assert future.exception() is not None
        assert isinstance(future.exception(), json.JSONDecodeError)
        
        # Verify the request was removed from pending requests
        assert request_id not in agent._pending_requests

    @pytest.mark.asyncio
    async def test_handle_event_unknown_request_id(self, agent):
        """Test _handle_event with an unknown request ID."""
        # Setup test data
        unknown_request_id = "unknown_request_id"
        test_response = {"result": "success"}
        
        # Create test event
        event = AgentEvent(
            id=unknown_request_id,
            message=json.dumps(test_response).encode(),
            message_type="response"
        )
        
        # Create mock record
        record = Mock(spec=ConsumerRecord)
        record.value = event
        
        # Create mock stream and send
        stream = Mock(spec=Stream)
        send = Mock(spec=Send)
        
        # Call the method (should not raise exception)
        await agent._handle_event(record, stream, send)
        
        # Verify no pending requests were affected
        assert len(agent._pending_requests) == 0

    @pytest.mark.asyncio
    async def test_handle_event_none_value(self, agent):
        """Test _handle_event with None record value."""
        # Create mock record with None value
        record = Mock(spec=ConsumerRecord)
        record.value = None
        
        # Create mock stream and send
        stream = Mock(spec=Stream)
        send = Mock(spec=Send)
        
        # Call the method (should not raise exception)
        await agent._handle_event(record, stream, send)
        
        # Verify no pending requests were affected
        assert len(agent._pending_requests) == 0

    @pytest.mark.asyncio
    async def test_handle_event_invalid_message_type(self, agent):
        """Test _handle_event with invalid message type."""
        # Create mock record with invalid message type
        record = Mock(spec=ConsumerRecord)
        record.value = "invalid_message_type"
        
        # Create mock stream and send
        stream = Mock(spec=Stream)
        send = Mock(spec=Send)
        
        # Call the method (should not raise exception)
        await agent._handle_event(record, stream, send)
        
        # Verify no pending requests were affected
        assert len(agent._pending_requests) == 0

    @pytest.mark.asyncio
    async def test_save_state(self, agent):
        """Test save_state method."""
        # Test initial state
        result = await agent.save_state()
        assert result == {"next_request_id": 0}
        
        # Advance request ID and test again
        await agent._get_new_request_id()
        await agent._get_new_request_id()
        result = await agent.save_state()
        assert result == {"next_request_id": 2}

    @pytest.mark.asyncio
    async def test_load_state(self, agent):
        """Test load_state method."""
        # Test loading state with next_request_id
        test_state = {"next_request_id": 5}
        result = await agent.load_state(test_state)
        assert result is None
        
        # Verify the request ID was updated
        new_id = await agent._get_new_request_id()
        assert new_id == "6"
        
        # Test loading state with higher ID doesn't override current higher ID
        await agent._get_new_request_id()  # Should be 7
        test_state = {"next_request_id": 3}  # Lower than current
        await agent.load_state(test_state)
        new_id = await agent._get_new_request_id()
        assert new_id == "8"  # Should continue from current state

    @pytest.mark.asyncio
    async def test_close(self, agent):
        """Test close method."""
        # Call close method
        await agent.close()
        
        # Verify background task manager was called
        agent._background_task_manager.wait_for_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_pending_requests_cleanup_on_exception(self, agent):
        """Test that pending requests are cleaned up when exceptions occur."""
        # Setup test data
        request_id = "test_request_id"
        
        # Create a future and add it to pending requests
        future = asyncio.get_event_loop().create_future()
        agent._pending_requests[request_id] = future
        
        # Create test event with data that will cause an exception
        event = AgentEvent(
            id=request_id,
            message=b'invalid json{',
            message_type="response"
        )
        
        # Create mock record
        record = Mock(spec=ConsumerRecord)
        record.value = event
        
        # Create mock stream and send
        stream = Mock(spec=Stream)
        send = Mock(spec=Send)
        
        # Call the method
        await agent._handle_event(record, stream, send)
        
        # Verify the pending request was cleaned up even after exception
        assert request_id not in agent._pending_requests

    def test_inheritance(self, agent):
        """Test that KafkaStreamingAgent properly inherits from BaseAgent and StreamingWorkerBase."""
        from autogen_core import BaseAgent
        from autogen_kafka_extension.shared.streaming_worker_base import StreamingWorkerBase
        
        assert isinstance(agent, BaseAgent)
        assert isinstance(agent, StreamingWorkerBase)

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, agent):
        """Test handling multiple concurrent requests."""
        # Create multiple futures and add them to pending requests
        num_requests = 5
        futures = {}
        
        for i in range(num_requests):
            request_id = f"request_{i}"
            future = asyncio.get_event_loop().create_future()
            agent._pending_requests[request_id] = future
            futures[request_id] = future
        
        # Create and process events for all requests
        async def process_event(req_id, response_data):
            event = AgentEvent(
                id=req_id,
                message=json.dumps(response_data).encode(),
                message_type="response"
            )
            record = Mock(spec=ConsumerRecord)
            record.value = event
            stream = Mock(spec=Stream)
            send = Mock(spec=Send)
            
            await agent._handle_event(record, stream, send)
        
        # Process all events concurrently
        tasks = []
        for i in range(num_requests):
            request_id = f"request_{i}"
            response_data = {"request_id": request_id, "result": f"result_{i}"}
            tasks.append(process_event(request_id, response_data))
        
        await asyncio.gather(*tasks)
        
        # Verify all futures were resolved correctly
        for i, (request_id, future) in enumerate(futures.items()):
            assert future.done()
            result = future.result()
            assert result["request_id"] == request_id
            assert result["result"] == f"result_{i}"
        
        # Verify all pending requests were cleaned up
        assert len(agent._pending_requests) == 0 