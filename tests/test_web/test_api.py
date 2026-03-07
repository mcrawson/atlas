"""Integration tests for ATLAS REST API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from atlas.web.app import create_app


class TestAPIStatus:
    """Test /api/status endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client with mocked managers."""
        mock_agent_manager = MagicMock()
        mock_agent_manager.get_all_status.return_value = {
            "architect": {"status": "idle", "name": "Architect"},
            "mason": {"status": "idle", "name": "Mason"},
            "oracle": {"status": "idle", "name": "Oracle"},
        }

        mock_project_manager = MagicMock()
        mock_project_manager.get_stats = AsyncMock(return_value={
            "total_projects": 5,
            "completed_projects": 2,
            "in_progress_projects": 3,
            "total_tasks": 10,
            "completed_tasks": 5,
        })

        app = create_app(
            agent_manager=mock_agent_manager,
            project_manager=mock_project_manager,
        )
        return TestClient(app)

    def test_status_returns_ok(self, client):
        """Test that status endpoint returns ok."""
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_status_includes_agents(self, client):
        """Test that status includes agent info."""
        response = client.get("/api/status")
        data = response.json()
        assert "agents" in data
        assert "architect" in data["agents"]

    def test_status_includes_projects(self, client):
        """Test that status includes project stats."""
        response = client.get("/api/status")
        data = response.json()
        assert "projects" in data
        assert data["projects"]["total_projects"] == 5


class TestAPIAgents:
    """Test /api/agents endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client with mocked agent manager."""
        mock_agent_manager = MagicMock()
        mock_agent_manager.get_all_status.return_value = {
            "architect": {
                "status": "idle",
                "name": "Architect",
                "description": "System designer",
                "icon": "🏗️",
                "color": "blue",
            },
            "mason": {
                "status": "working",
                "name": "Mason",
                "description": "Code builder",
                "icon": "🔨",
                "color": "green",
            },
            "oracle": {
                "status": "idle",
                "name": "Oracle",
                "description": "Code reviewer",
                "icon": "🔮",
                "color": "purple",
            },
        }

        app = create_app(agent_manager=mock_agent_manager)
        return TestClient(app)

    def test_agents_returns_all_agents(self, client):
        """Test that agents endpoint returns all agents."""
        response = client.get("/api/agents")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert len(data["agents"]) == 3

    def test_agents_includes_status(self, client):
        """Test that agent data includes status."""
        response = client.get("/api/agents")
        data = response.json()
        assert data["agents"]["mason"]["status"] == "working"


class TestAPIProjects:
    """Test /api/projects endpoints."""

    @pytest.fixture
    def mock_project(self):
        """Create a mock project."""
        from datetime import datetime

        project = MagicMock()
        project.id = 1
        project.name = "Test Project"
        project.description = "A test project"
        project.status = "active"
        project.tags = ["python", "test"]
        project.created_at = datetime.now()
        project.to_dict.return_value = {
            "id": 1,
            "name": "Test Project",
            "description": "A test project",
            "status": "active",
            "tags": ["python", "test"],
            "created_at": datetime.now().isoformat(),
            "tasks": [],
        }
        return project

    @pytest.fixture
    def client(self, mock_project):
        """Create test client with mocked project manager."""
        mock_project_manager = MagicMock()
        mock_project_manager.get_projects = AsyncMock(return_value=[mock_project])
        mock_project_manager.get_project = AsyncMock(return_value=mock_project)
        mock_project_manager.create_project = AsyncMock(return_value=mock_project)
        mock_project_manager.get_stats = AsyncMock(return_value={})

        app = create_app(project_manager=mock_project_manager)
        return TestClient(app)

    def test_get_projects_returns_list(self, client):
        """Test that projects endpoint returns a list."""
        response = client.get("/api/projects")
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert "total" in data
        assert data["total"] == 1

    def test_get_project_by_id(self, client):
        """Test getting a single project."""
        response = client.get("/api/projects/1")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["project"]["name"] == "Test Project"

    def test_create_project(self, client):
        """Test creating a new project."""
        response = client.post(
            "/api/projects",
            json={
                "name": "New Project",
                "description": "A new project",
                "tags": ["python"],
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True

    def test_create_project_validates_name(self, client):
        """Test that project creation requires a name."""
        response = client.post(
            "/api/projects",
            json={"name": "", "description": "No name"}
        )
        assert response.status_code == 422  # Validation error


class TestAPITask:
    """Test /api/task endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client with mocked agent manager."""
        mock_output = MagicMock()
        mock_output.to_dict.return_value = {"content": "Result"}

        mock_agent_manager = MagicMock()
        mock_agent_manager.execute_workflow = AsyncMock(return_value={
            "architect": mock_output,
            "mason": mock_output,
            "oracle": mock_output,
        })
        mock_agent_manager.get_all_status.return_value = {}

        app = create_app(agent_manager=mock_agent_manager)
        return TestClient(app)

    def test_execute_task(self, client):
        """Test executing a task."""
        response = client.post(
            "/api/task",
            json={"task": "Build a hello world app"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "results" in data

    def test_execute_task_with_mode(self, client):
        """Test executing a task with specific mode."""
        response = client.post(
            "/api/task",
            json={
                "task": "Build a hello world app",
                "mode": "direct_build"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "direct_build"

    def test_execute_task_validates_input(self, client):
        """Test that task execution validates input."""
        response = client.post(
            "/api/task",
            json={"task": ""}
        )
        assert response.status_code == 422  # Validation error

    def test_execute_task_rejects_whitespace_only(self, client):
        """Test that whitespace-only tasks are rejected."""
        response = client.post(
            "/api/task",
            json={"task": "   "}
        )
        assert response.status_code == 422


class TestAPIProjectTasks:
    """Test /api/projects/{id}/tasks endpoints."""

    @pytest.fixture
    def mock_task(self):
        """Create a mock task."""
        task = MagicMock()
        task.id = 1
        task.project_id = 1
        task.title = "Test Task"
        task.description = "A test task"
        task.priority = 1
        task.status = "pending"
        task.to_dict.return_value = {
            "id": 1,
            "project_id": 1,
            "title": "Test Task",
            "description": "A test task",
            "priority": 1,
            "status": "pending",
        }
        return task

    @pytest.fixture
    def client(self, mock_task):
        """Create test client with mocked project manager."""
        mock_project_manager = MagicMock()
        mock_project_manager.add_task = AsyncMock(return_value=mock_task)
        mock_project_manager.get_stats = AsyncMock(return_value={})

        app = create_app(project_manager=mock_project_manager)
        return TestClient(app)

    def test_add_task_to_project(self, client):
        """Test adding a task to a project."""
        response = client.post(
            "/api/projects/1/tasks",
            json={
                "title": "New Task",
                "description": "Task description",
                "priority": 2,
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True

    def test_add_task_validates_title(self, client):
        """Test that task creation requires a title."""
        response = client.post(
            "/api/projects/1/tasks",
            json={"title": "", "description": "No title"}
        )
        assert response.status_code == 422


class TestAPIErrorHandling:
    """Test API error handling."""

    @pytest.fixture
    def client(self):
        """Create test client without managers."""
        app = create_app()
        return TestClient(app)

    def test_status_without_managers(self, client):
        """Test status endpoint works without managers."""
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_projects_without_manager(self, client):
        """Test projects endpoint without manager."""
        response = client.get("/api/projects")
        assert response.status_code == 200
        data = response.json()
        assert data["projects"] == []

    def test_agents_without_manager(self, client):
        """Test agents endpoint without manager."""
        response = client.get("/api/agents")
        assert response.status_code == 200
        data = response.json()
        assert data["agents"] == {}


class TestHealthCheck:
    """Test /api/health endpoint."""

    @pytest.fixture
    def client_with_managers(self):
        """Create test client with mocked managers."""
        mock_agent_manager = MagicMock()
        mock_agent_manager.get_all_status.return_value = {
            "architect": {"status": "idle"},
            "mason": {"status": "idle"},
            "oracle": {"status": "idle"},
        }

        mock_project_manager = MagicMock()
        mock_project_manager.get_stats = AsyncMock(return_value={})

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True

        app = create_app(
            agent_manager=mock_agent_manager,
            project_manager=mock_project_manager,
            providers={"ollama": mock_provider},
        )
        return TestClient(app)

    @pytest.fixture
    def client_without_managers(self):
        """Create test client without managers."""
        app = create_app()
        return TestClient(app)

    def test_health_check_returns_ok(self, client_with_managers):
        """Test that health check returns healthy status."""
        response = client_with_managers.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "checks" in data

    def test_health_check_includes_database(self, client_with_managers):
        """Test that health check includes database status."""
        response = client_with_managers.get("/api/health")
        data = response.json()
        assert "database" in data["checks"]
        assert data["checks"]["database"]["status"] == "ok"

    def test_health_check_includes_agents(self, client_with_managers):
        """Test that health check includes agent status."""
        response = client_with_managers.get("/api/health")
        data = response.json()
        assert "agents" in data["checks"]
        assert data["checks"]["agents"]["status"] == "ok"
        assert data["checks"]["agents"]["count"] == 3

    def test_health_check_includes_providers(self, client_with_managers):
        """Test that health check includes provider status."""
        response = client_with_managers.get("/api/health")
        data = response.json()
        assert "providers" in data["checks"]
        assert "ollama" in data["checks"]["providers"]["available"]

    def test_health_check_without_managers(self, client_without_managers):
        """Test health check works without managers."""
        response = client_without_managers.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["checks"]["database"]["status"] == "not_configured"
