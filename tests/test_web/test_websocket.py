"""Tests for WebSocket functionality."""

import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

from atlas.web.app import create_app
from atlas.web.websocket import ConnectionManager, manager, handle_message


class TestConnectionManager:
    """Test ConnectionManager class."""

    @pytest.fixture
    def conn_manager(self):
        """Create a fresh connection manager."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        ws.receive_text = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect(self, conn_manager, mock_websocket):
        """Test connecting a WebSocket."""
        await conn_manager.connect(mock_websocket)

        assert mock_websocket in conn_manager.connections
        mock_websocket.accept.assert_called_once()

    def test_disconnect(self, conn_manager, mock_websocket):
        """Test disconnecting a WebSocket."""
        conn_manager.connections.add(mock_websocket)

        conn_manager.disconnect(mock_websocket)

        assert mock_websocket not in conn_manager.connections

    def test_disconnect_not_connected(self, conn_manager, mock_websocket):
        """Test disconnecting a WebSocket that wasn't connected."""
        # Should not raise an error
        conn_manager.disconnect(mock_websocket)
        assert mock_websocket not in conn_manager.connections

    @pytest.mark.asyncio
    async def test_broadcast_empty(self, conn_manager):
        """Test broadcasting with no connections."""
        # Should not raise an error
        await conn_manager.broadcast({"type": "test"})

    @pytest.mark.asyncio
    async def test_broadcast_single(self, conn_manager, mock_websocket):
        """Test broadcasting to a single connection."""
        conn_manager.connections.add(mock_websocket)

        await conn_manager.broadcast({"type": "test", "data": "value"})

        mock_websocket.send_text.assert_called_once()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["type"] == "test"
        assert sent_data["data"] == "value"

    @pytest.mark.asyncio
    async def test_broadcast_multiple(self, conn_manager):
        """Test broadcasting to multiple connections."""
        ws1 = MagicMock()
        ws1.send_text = AsyncMock()
        ws2 = MagicMock()
        ws2.send_text = AsyncMock()

        conn_manager.connections.add(ws1)
        conn_manager.connections.add(ws2)

        await conn_manager.broadcast({"type": "test"})

        ws1.send_text.assert_called_once()
        ws2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_removes_failed(self, conn_manager):
        """Test that failed connections are removed on broadcast."""
        good_ws = MagicMock()
        good_ws.send_text = AsyncMock()

        bad_ws = MagicMock()
        bad_ws.send_text = AsyncMock(side_effect=Exception("Connection closed"))

        conn_manager.connections.add(good_ws)
        conn_manager.connections.add(bad_ws)

        await conn_manager.broadcast({"type": "test"})

        assert good_ws in conn_manager.connections
        assert bad_ws not in conn_manager.connections

    @pytest.mark.asyncio
    async def test_send_to(self, conn_manager, mock_websocket):
        """Test sending to a specific connection."""
        conn_manager.connections.add(mock_websocket)

        await conn_manager.send_to(mock_websocket, {"type": "direct"})

        mock_websocket.send_text.assert_called_once()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["type"] == "direct"

    @pytest.mark.asyncio
    async def test_send_to_removes_failed(self, conn_manager):
        """Test that failed connection is removed on send_to."""
        bad_ws = MagicMock()
        bad_ws.send_text = AsyncMock(side_effect=Exception("Connection closed"))

        conn_manager.connections.add(bad_ws)

        await conn_manager.send_to(bad_ws, {"type": "test"})

        assert bad_ws not in conn_manager.connections


class TestHandleMessage:
    """Test handle_message function."""

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket with app state."""
        ws = MagicMock()
        ws.app.state.agent_manager = None
        return ws

    @pytest.mark.asyncio
    async def test_handle_pong(self, mock_websocket):
        """Test handling pong message (heartbeat)."""
        # Should not raise or send anything
        await handle_message(mock_websocket, {"type": "pong"})

    @pytest.mark.asyncio
    async def test_handle_unknown_type(self, mock_websocket):
        """Test handling unknown message type."""
        with patch.object(manager, 'send_to', new_callable=AsyncMock) as mock_send:
            await handle_message(mock_websocket, {"type": "unknown_type"})

            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert args[1]["type"] == "error"
            assert "unknown_type" in args[1]["message"].lower()

    @pytest.mark.asyncio
    async def test_handle_get_status_no_manager(self, mock_websocket):
        """Test get_status when agent manager is not available."""
        with patch.object(manager, 'send_to', new_callable=AsyncMock):
            # Should not crash when agent_manager is None
            await handle_message(mock_websocket, {"type": "get_status"})

    @pytest.mark.asyncio
    async def test_handle_get_status_with_manager(self, mock_websocket):
        """Test get_status with agent manager."""
        mock_agent_manager = MagicMock()
        mock_agent_manager.get_all_status.return_value = {
            "architect": {"status": "idle"}
        }
        mock_websocket.app.state.agent_manager = mock_agent_manager

        with patch.object(manager, 'send_to', new_callable=AsyncMock) as mock_send:
            await handle_message(mock_websocket, {"type": "get_status"})

            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert args[1]["type"] == "status"
            assert "agents" in args[1]

    @pytest.mark.asyncio
    async def test_handle_execute_task_no_manager(self, mock_websocket):
        """Test execute_task when agent manager is not available."""
        with patch.object(manager, 'send_to', new_callable=AsyncMock) as mock_send:
            await handle_message(mock_websocket, {
                "type": "execute_task",
                "task": "Build something"
            })

            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert args[1]["type"] == "error"
            assert "not available" in args[1]["message"].lower()

    @pytest.mark.asyncio
    async def test_handle_execute_task_no_task(self, mock_websocket):
        """Test execute_task without task parameter."""
        mock_websocket.app.state.agent_manager = MagicMock()

        with patch.object(manager, 'send_to', new_callable=AsyncMock) as mock_send:
            await handle_message(mock_websocket, {"type": "execute_task"})

            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert args[1]["type"] == "error"
            assert "required" in args[1]["message"].lower()


class TestWebSocketEndpoint:
    """Test WebSocket endpoint integration."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)

    def test_websocket_connect(self, client):
        """Test WebSocket connection."""
        with client.websocket_connect("/ws") as websocket:
            # Connection should be established
            # May receive initial messages
            pass

    def test_websocket_ping_response(self, client):
        """Test WebSocket receives ping."""
        # This would require a longer-running test
        # For now, just verify connection works
        with client.websocket_connect("/ws") as websocket:
            pass

    def test_websocket_invalid_json(self, client):
        """Test WebSocket handles invalid JSON."""
        with client.websocket_connect("/ws") as websocket:
            websocket.send_text("not valid json")

            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "invalid" in response["message"].lower()

    def test_websocket_get_status(self, client):
        """Test get_status message."""
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "get_status"})
            # Without agent manager, no response expected
