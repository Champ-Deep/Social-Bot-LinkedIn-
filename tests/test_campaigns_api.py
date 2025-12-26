"""
Essential Campaign API Tests

Focus: Critical paths only (5 tests per MVP requirements)
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
import uuid
from datetime import datetime

# Test fixtures and utilities
pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def sample_campaign_data():
    """Sample campaign creation data."""
    return {
        "name": "Test Campaign",
        "description": "Test description",
        "target_urls": ["https://linkedin.com/posts/test-123"],
        "account_ids": [str(uuid.uuid4())],
        "actions": {"like": True, "comment": False},
        "priority": 1
    }


@pytest.fixture
def sample_campaign_response():
    """Sample campaign response data."""
    campaign_id = uuid.uuid4()
    return {
        "id": str(campaign_id),
        "name": "Test Campaign",
        "description": "Test description",
        "status": "draft",
        "target_urls": ["https://linkedin.com/posts/test-123"],
        "account_ids": [str(uuid.uuid4())],
        "actions": {"like": True, "comment": False},
        "priority": 1,
        "progress": {
            "total_tasks": 1,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "pending_tasks": 1,
            "completion_percent": 0.0
        },
        "scheduled_start_at": None,
        "started_at": None,
        "completed_at": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }


class TestCampaignCreation:
    """Tests for campaign creation endpoint."""

    async def test_create_campaign_success(self, sample_campaign_data):
        """
        TEST 1: Create campaign successfully

        Verifies:
        - POST /api/v1/campaigns with valid payload returns 201
        - Campaign is returned with draft status
        - Idempotency key is required
        """
        from src.api.main import app
        from src.campaigns.service import CampaignService
        from src.campaigns.models import Campaign, CampaignStatusEnum
        from src.campaigns.schemas import CampaignActions

        # Create mock campaign
        mock_campaign = MagicMock(spec=Campaign)
        mock_campaign.id = uuid.uuid4()
        mock_campaign.name = sample_campaign_data["name"]
        mock_campaign.description = sample_campaign_data["description"]
        mock_campaign.status = CampaignStatusEnum.DRAFT.value
        mock_campaign.target_urls = sample_campaign_data["target_urls"]
        mock_campaign.account_ids = sample_campaign_data["account_ids"]
        mock_campaign.actions = sample_campaign_data["actions"]
        mock_campaign.priority = 1
        mock_campaign.total_tasks = 1
        mock_campaign.completed_tasks = 0
        mock_campaign.failed_tasks = 0
        mock_campaign.completion_percent = 0.0
        mock_campaign.scheduled_start_at = None
        mock_campaign.started_at = None
        mock_campaign.completed_at = None
        mock_campaign.created_at = datetime.utcnow()
        mock_campaign.updated_at = datetime.utcnow()

        with patch.object(
            CampaignService,
            'create_campaign',
            new_callable=AsyncMock,
            return_value=mock_campaign
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                idempotency_key = str(uuid.uuid4())
                response = await client.post(
                    "/api/v1/campaigns",
                    json=sample_campaign_data,
                    headers={"X-Idempotency-Key": idempotency_key}
                )

                # Verify response
                assert response.status_code == 201
                data = response.json()
                assert data["name"] == sample_campaign_data["name"]
                assert data["status"] == "draft"

    async def test_create_campaign_missing_idempotency_key(self, sample_campaign_data):
        """
        TEST 1b: Create campaign without idempotency key fails

        Verifies:
        - POST without X-Idempotency-Key returns 422 (validation error)
        """
        from src.api.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/campaigns",
                json=sample_campaign_data
                # No idempotency key header
            )

            # FastAPI returns 422 for missing required headers
            assert response.status_code == 422
            # Validate that error mentions the missing header
            detail = response.json()["detail"]
            assert any("x-idempotency-key" in str(err).lower() for err in detail)


class TestIdempotency:
    """Tests for idempotency behavior."""

    async def test_idempotency_replay(self, sample_campaign_data):
        """
        TEST 2: Idempotency prevents duplicate creation

        Verifies:
        - POST twice with same X-Idempotency-Key returns same campaign
        - No duplicate campaign is created
        """
        from src.api.main import app
        from src.campaigns.service import CampaignService, IdempotencyKeyExistsError
        from src.campaigns.models import Campaign, CampaignStatusEnum

        campaign_id = uuid.uuid4()

        # Create mock campaign for first call
        mock_campaign = MagicMock(spec=Campaign)
        mock_campaign.id = campaign_id
        mock_campaign.name = sample_campaign_data["name"]
        mock_campaign.description = sample_campaign_data["description"]
        mock_campaign.status = CampaignStatusEnum.DRAFT.value
        mock_campaign.target_urls = sample_campaign_data["target_urls"]
        mock_campaign.account_ids = sample_campaign_data["account_ids"]
        mock_campaign.actions = sample_campaign_data["actions"]
        mock_campaign.priority = 1
        mock_campaign.total_tasks = 1
        mock_campaign.completed_tasks = 0
        mock_campaign.failed_tasks = 0
        mock_campaign.completion_percent = 0.0
        mock_campaign.scheduled_start_at = None
        mock_campaign.started_at = None
        mock_campaign.completed_at = None
        mock_campaign.created_at = datetime.utcnow()
        mock_campaign.updated_at = datetime.utcnow()

        idempotency_key = str(uuid.uuid4())

        # First call creates, second call raises IdempotencyKeyExistsError
        call_count = 0

        async def mock_create_campaign(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_campaign
            else:
                raise IdempotencyKeyExistsError(
                    resource_id=campaign_id,
                    response_body={"id": str(campaign_id)}
                )

        with patch.object(
            CampaignService,
            'create_campaign',
            side_effect=mock_create_campaign
        ), patch.object(
            CampaignService,
            'get_campaign',
            new_callable=AsyncMock,
            return_value=mock_campaign
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                # First request
                resp1 = await client.post(
                    "/api/v1/campaigns",
                    json=sample_campaign_data,
                    headers={"X-Idempotency-Key": idempotency_key}
                )

                # Second request with same key
                resp2 = await client.post(
                    "/api/v1/campaigns",
                    json=sample_campaign_data,
                    headers={"X-Idempotency-Key": idempotency_key}
                )

                # Both should succeed and return same campaign ID
                assert resp1.status_code == 201
                assert resp2.status_code == 201
                assert resp1.json()["id"] == resp2.json()["id"]


class TestCampaignExecution:
    """Tests for campaign execution."""

    async def test_start_campaign_submits_tasks(self):
        """
        TEST 3: Start campaign submits tasks to orchestrator

        Verifies:
        - POST /api/v1/campaigns/{id}/start submits tasks
        - Response includes task count
        - Campaign status changes to running
        """
        from src.api.main import app
        from src.campaigns.service import CampaignService
        from src.campaigns.schemas import StartCampaignResponse, CampaignStatus

        campaign_id = uuid.uuid4()
        mock_response = StartCampaignResponse(
            campaign_id=campaign_id,
            status=CampaignStatus.RUNNING,
            tasks_created=5,
            message="Campaign started with 5 tasks"
        )

        with patch.object(
            CampaignService,
            'start_campaign',
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    f"/api/v1/campaigns/{campaign_id}/start",
                    headers={"X-Idempotency-Key": str(uuid.uuid4())}
                )

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "running"
                assert data["tasks_created"] == 5
                assert str(campaign_id) == data["campaign_id"]


class TestValidation:
    """Tests for input validation."""

    async def test_invalid_url_rejected(self):
        """
        TEST 5: Invalid LinkedIn URL is rejected

        Verifies:
        - POST with non-LinkedIn URL returns 422
        - Error message indicates invalid URL
        """
        from src.api.main import app

        invalid_data = {
            "name": "Bad Campaign",
            "target_urls": ["https://twitter.com/someuser/status/123"],
            "account_ids": [str(uuid.uuid4())],
            "actions": {"like": True}
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/campaigns",
                json=invalid_data,
                headers={"X-Idempotency-Key": str(uuid.uuid4())}
            )

            assert response.status_code == 422
            detail = response.json()["detail"]
            # Check that validation error mentions invalid URL
            assert any("linkedin" in str(err).lower() for err in detail)


class TestCampaignStatus:
    """Tests for campaign status endpoint."""

    async def test_get_campaign_status(self):
        """
        TEST 4: Get campaign progress

        Verifies:
        - GET /api/v1/campaigns/{id}/status returns progress
        - Response includes task counts
        """
        from src.api.main import app
        from src.campaigns.service import CampaignService
        from src.campaigns.schemas import CampaignProgress

        campaign_id = uuid.uuid4()
        mock_progress = CampaignProgress(
            total_tasks=10,
            completed_tasks=7,
            failed_tasks=1,
            pending_tasks=2,
            completion_percent=70.0
        )

        with patch.object(
            CampaignService,
            'get_campaign_progress',
            new_callable=AsyncMock,
            return_value=mock_progress
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.get(
                    f"/api/v1/campaigns/{campaign_id}/status"
                )

                assert response.status_code == 200
                data = response.json()
                assert data["total_tasks"] == 10
                assert data["completed_tasks"] == 7
                assert data["completion_percent"] == 70.0


# Integration test helper for manual curl testing
def print_curl_examples():
    """Print curl examples for manual testing."""
    print("""
    === Campaign API curl Examples ===

    # Create campaign
    curl -X POST http://localhost:8000/api/v1/campaigns \\
      -H "Content-Type: application/json" \\
      -H "X-Idempotency-Key: $(uuidgen)" \\
      -d '{
        "name": "Test Campaign",
        "target_urls": ["https://linkedin.com/posts/example-123"],
        "account_ids": ["<your-account-uuid>"],
        "actions": {"like": true, "comment": false}
      }'

    # List campaigns
    curl http://localhost:8000/api/v1/campaigns

    # Get campaign
    curl http://localhost:8000/api/v1/campaigns/<campaign-id>

    # Start campaign
    curl -X POST http://localhost:8000/api/v1/campaigns/<campaign-id>/start \\
      -H "X-Idempotency-Key: $(uuidgen)"

    # Get campaign status
    curl http://localhost:8000/api/v1/campaigns/<campaign-id>/status

    # Pause campaign
    curl -X POST http://localhost:8000/api/v1/campaigns/<campaign-id>/pause

    # Delete campaign
    curl -X DELETE http://localhost:8000/api/v1/campaigns/<campaign-id>
    """)


if __name__ == "__main__":
    print_curl_examples()
