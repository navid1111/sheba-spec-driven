"""Integration tests for CoachNova worker coaching flow.

Tests the complete CoachNova orchestration:
1. Worker with performance issues identified (late arrivals, low ratings)
2. Performance signals analyzed (from worker_performance_snapshots)
3. Eligibility validated (consent, frequency caps)
4. Bengali coaching message generated via OpenAI (mocked)
5. Safety filter applied
6. AIMessage record created
7. Notification triggered (email delivery)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

from src.models.users import User, UserType
from src.models.workers import Worker
from src.models.ai_messages import AIMessage, MessageRole, MessageChannel, MessageType, DeliveryStatus
from src.lib.db import get_db


# Seeded worker IDs from run_worker_setup.py
WORKER_SADIA_ID = UUID("7b6a9c7a-3d2a-4b2e-9a9c-1f2d3e4c5a6b")  # 3 late arrivals
WORKER_FEROZ_ID = UUID("9d4e3c2b-1a0f-48b7-bc3a-2a1b0c9d8e7f")  # 0 late arrivals
WORKER_JAHANGIR_ID = UUID("a0b1c2d3-e4f5-46a7-98b9-0c1d2e3f4a5b")  # 5 late arrivals


@pytest.fixture
def db_session():
    """Get database session for tests."""
    session = next(get_db())
    yield session
    session.rollback()
    session.close()


@pytest.mark.integration
@pytest.mark.skip(reason="Awaiting T047 PerformanceService and T048 CoachNova orchestrator implementation")
async def test_coachnova_worker_with_late_arrivals_receives_coaching(db_session):
    """Test that worker with >= 3 late arrivals receives Bengali coaching message."""
    
    # Arrange: Use Jahangir (5 late arrivals, strong coaching candidate)
    worker_id = WORKER_JAHANGIR_ID
    correlation_id = uuid4()
    
    # Mock OpenAI response with realistic Bengali coaching content
    mock_openai_response = MagicMock()
    mock_openai_response.choices = [
        MagicMock(
            message=MagicMock(
                content=(
                    "প্রিয় জাহাঙ্গীর,\n\n"
                    "আপনার কাজের প্রতি আপনার প্রতিশ্রুতি আমরা লক্ষ্য করেছি। "
                    "তবে সাম্প্রতিক সপ্তাহে কিছু দেরি হওয়ার ঘটনা দেখা গেছে।\n\n"
                    "সময়মত পৌঁছানোর কিছু টিপস:\n"
                    "১. যাত্রার আগে ট্রাফিক চেক করুন\n"
                    "২. ১৫ মিনিট আগে বের হন\n"
                    "৩. রাতে পরের দিনের জিনিসপত্র গুছিয়ে রাখুন\n\n"
                    "আপনার উন্নতির জন্য আমরা এখানে আছি।"
                )
            )
        )
    ]
    mock_openai_response.model = "gpt-4o-mini"
    mock_openai_response.usage.total_tokens = 250
    
    # Act: Trigger coaching with mocked OpenAI
    with patch('openai.ChatCompletion.create', return_value=mock_openai_response):
        # Import here to avoid circular dependencies
        from src.ai.coachnova import CoachNovaOrchestrator
        from src.services.performance_service import PerformanceService
        
        # Get performance signals
        performance_signals = await PerformanceService.get_signals(
            worker_id=worker_id,
            db=db_session
        )
        
        # Verify worker is eligible (late_arrivals >= 3)
        assert performance_signals['late_arrivals_last_7_days'] >= 3
        
        # Generate coaching
        orchestrator = CoachNovaOrchestrator()
        result = await orchestrator.generate_coaching(
            worker_id=worker_id,
            performance_signals=performance_signals,
            correlation_id=correlation_id,
            db=db_session
        )
        
        # Should succeed
        assert result['success'] is True
        assert result['message_id'] is not None
        assert result['correlation_id'] == correlation_id
    
    # Assert: Verify AIMessage was created
    stmt = select(AIMessage).where(
        AIMessage.user_id == worker_id,
        AIMessage.agent_type == 'coachnova',
        AIMessage.correlation_id == correlation_id
    )
    ai_message = db_session.execute(stmt).scalar_one()
    
    # Verify message attributes
    assert ai_message.id == result['message_id']
    assert ai_message.role == MessageRole.WORKER
    assert ai_message.agent_type == 'coachnova'
    assert ai_message.message_type == MessageType.COACHING
    assert ai_message.channel == MessageChannel.EMAIL  # Primary channel per research.md
    assert ai_message.locale == 'bn'
    assert ai_message.model == 'gpt-4o-mini'
    assert ai_message.delivery_status == DeliveryStatus.PENDING
    
    # Verify Bengali content
    assert 'জাহাঙ্গীর' in ai_message.message_text  # Worker name
    assert 'সময়' in ai_message.message_text  # Time-related content
    assert 'টিপস' in ai_message.message_text or 'পরামর্শ' in ai_message.message_text  # Tips/advice
    
    # Verify safety checks passed
    assert ai_message.safety_checks is not None
    assert ai_message.safety_checks['safe'] is True
    assert ai_message.safety_checks['tone_appropriate'] is True
    assert ai_message.safety_checks['banned_phrases'] is False
    
    # Verify no shaming language (dignity-centered)
    assert 'লজ্জা' not in ai_message.message_text.lower()  # No shame
    assert 'খারাপ' not in ai_message.message_text.lower()  # No bad/negative framing


@pytest.mark.integration
@pytest.mark.skip(reason="Awaiting T047 PerformanceService and T048 CoachNova orchestrator implementation")
async def test_coachnova_worker_no_issues_not_eligible(db_session):
    """Test that worker with no performance issues does not receive coaching."""
    
    # Arrange: Use Feroz (0 late arrivals, no issues)
    worker_id = WORKER_FEROZ_ID
    
    # Act: Try to trigger coaching
    from src.ai.coachnova import CoachNovaOrchestrator
    from src.services.performance_service import PerformanceService
    
    # Get performance signals
    performance_signals = await PerformanceService.get_signals(
        worker_id=worker_id,
        db=db_session
    )
    
    # Verify worker has no issues
    assert performance_signals['late_arrivals_last_7_days'] < 3
    
    # Try to generate coaching
    orchestrator = CoachNovaOrchestrator()
    result = await orchestrator.generate_coaching(
        worker_id=worker_id,
        performance_signals=performance_signals,
        correlation_id=uuid4(),
        db=db_session
    )
    
    # Assert: Should be ineligible
    assert result['success'] is False
    assert result['reason'] == 'no_performance_issues'
    assert result['message_id'] is None
    
    # Verify no AIMessage was created
    stmt = select(AIMessage).where(
        AIMessage.user_id == worker_id,
        AIMessage.agent_type == 'coachnova'
    )
    messages = db_session.execute(stmt).scalars().all()
    assert len(messages) == 0


@pytest.mark.integration
@pytest.mark.skip(reason="Awaiting T047 PerformanceService and T048 CoachNova orchestrator implementation")
async def test_coachnova_respects_consent_coaching_disabled(db_session):
    """Test that worker without coaching_enabled consent is skipped."""
    
    # Arrange: Create test worker without coaching consent
    user = User(
        id=uuid4(),
        email="test.worker.no.consent@example.com",
        name="Test Worker No Consent",
        type=UserType.WORKER,
        language_preference="bn",
        is_active=True,
        consent={
            "email_enabled": True,
            "coaching_enabled": False,  # Coaching disabled
            "voice_opt_in": False
        }
    )
    db_session.add(user)
    
    worker = Worker(
        id=user.id,
        skills=["CLEANING"],
        years_experience=2,
        rating_avg=4.2,
        total_jobs_completed=100,
        preferred_areas=["Dhaka"],
        work_hours={"weekday": "9-17", "weekend": "off"},
        opt_in_voice=False
    )
    db_session.add(worker)
    db_session.commit()
    
    # Create performance snapshot with issues
    from src.models.workers import WorkerPerformanceSnapshot
    snapshot = WorkerPerformanceSnapshot(
        id=uuid4(),
        worker_id=worker.id,
        date=datetime.now(timezone.utc).date(),
        jobs_completed_last_7_days=10,
        avg_rating_last_30_days=4.2,
        late_arrivals_last_7_days=5,  # Has issues but no consent
        cancellations_by_worker=0,
        hours_worked_last_7_days=40.0,
        workload_score=60,
        burnout_score=30
    )
    db_session.add(snapshot)
    db_session.commit()
    
    # Act: Try to trigger coaching
    from src.ai.coachnova import CoachNovaOrchestrator
    from src.services.performance_service import PerformanceService
    
    performance_signals = await PerformanceService.get_signals(
        worker_id=worker.id,
        db=db_session
    )
    
    orchestrator = CoachNovaOrchestrator()
    result = await orchestrator.generate_coaching(
        worker_id=worker.id,
        performance_signals=performance_signals,
        correlation_id=uuid4(),
        db=db_session
    )
    
    # Assert: Should be rejected due to lack of consent
    assert result['success'] is False
    assert result['reason'] == 'no_consent'
    assert result['message_id'] is None


@pytest.mark.integration
@pytest.mark.skip(reason="Awaiting T047 PerformanceService and T048 CoachNova orchestrator implementation")
async def test_coachnova_respects_frequency_caps(db_session):
    """Test that frequency caps prevent duplicate coaching within 7 days."""
    
    # Arrange: Use Sadia (3 late arrivals)
    worker_id = WORKER_SADIA_ID
    
    # Create a recent coaching message (sent 3 days ago)
    recent_message = AIMessage(
        id=uuid4(),
        user_id=worker_id,
        role=MessageRole.WORKER,
        agent_type='coachnova',
        message_type=MessageType.COACHING,
        channel=MessageChannel.EMAIL,
        locale='bn',
        message_text='Previous coaching message',
        model='gpt-4o-mini',
        delivery_status=DeliveryStatus.SENT,
        sent_at=datetime.now(timezone.utc) - timedelta(days=3),
        safety_checks={'safe': True}
    )
    db_session.add(recent_message)
    db_session.commit()
    
    # Act: Try to trigger coaching again
    from src.ai.coachnova import CoachNovaOrchestrator
    from src.services.performance_service import PerformanceService
    
    performance_signals = await PerformanceService.get_signals(
        worker_id=worker_id,
        db=db_session
    )
    
    orchestrator = CoachNovaOrchestrator()
    result = await orchestrator.generate_coaching(
        worker_id=worker_id,
        performance_signals=performance_signals,
        correlation_id=uuid4(),
        db=db_session
    )
    
    # Assert: Should be rejected due to frequency cap
    assert result['success'] is False
    assert result['reason'] == 'frequency_cap'
    assert result['message_id'] is None


@pytest.mark.integration
@pytest.mark.skip(reason="Awaiting T047 PerformanceService and T048 CoachNova orchestrator implementation")
async def test_coachnova_voice_opt_in_preference_respected(db_session):
    """Test that worker with voice opt-in preference gets voice-enabled flag."""
    
    # Arrange: Use Sadia (has opt_in_voice=True per run_worker_setup.py)
    worker_id = WORKER_SADIA_ID
    correlation_id = uuid4()
    
    # Mock OpenAI
    mock_openai_response = MagicMock()
    mock_openai_response.choices = [
        MagicMock(message=MagicMock(content="Bengali coaching message"))
    ]
    mock_openai_response.model = "gpt-4o-mini"
    mock_openai_response.usage.total_tokens = 150
    
    # Act: Generate coaching
    with patch('openai.ChatCompletion.create', return_value=mock_openai_response):
        from src.ai.coachnova import CoachNovaOrchestrator
        from src.services.performance_service import PerformanceService
        
        performance_signals = await PerformanceService.get_signals(
            worker_id=worker_id,
            db=db_session
        )
        
        orchestrator = CoachNovaOrchestrator()
        result = await orchestrator.generate_coaching(
            worker_id=worker_id,
            performance_signals=performance_signals,
            correlation_id=correlation_id,
            db=db_session
        )
    
    # Assert: Message should have voice metadata
    stmt = select(AIMessage).where(
        AIMessage.id == result['message_id']
    )
    ai_message = db_session.execute(stmt).scalar_one()
    
    # Check metadata for voice preference
    assert ai_message.metadata is not None
    assert ai_message.metadata.get('voice_enabled') is True
    # Note: Actual voice generation is stub/future work per spec


@pytest.mark.integration
@pytest.mark.skip(reason="Awaiting T047 PerformanceService and T048 CoachNova orchestrator implementation")
async def test_coachnova_correlation_id_tracking(db_session):
    """Test that correlation_id is preserved end-to-end for tracing."""
    
    # Arrange
    worker_id = WORKER_JAHANGIR_ID
    correlation_id = uuid4()
    
    # Mock OpenAI
    mock_openai_response = MagicMock()
    mock_openai_response.choices = [
        MagicMock(message=MagicMock(content="Bengali coaching"))
    ]
    mock_openai_response.model = "gpt-4o-mini"
    mock_openai_response.usage.total_tokens = 100
    
    # Act: Generate coaching with specific correlation_id
    with patch('openai.ChatCompletion.create', return_value=mock_openai_response):
        from src.ai.coachnova import CoachNovaOrchestrator
        from src.services.performance_service import PerformanceService
        
        performance_signals = await PerformanceService.get_signals(
            worker_id=worker_id,
            db=db_session
        )
        
        orchestrator = CoachNovaOrchestrator()
        result = await orchestrator.generate_coaching(
            worker_id=worker_id,
            performance_signals=performance_signals,
            correlation_id=correlation_id,
            db=db_session
        )
    
    # Assert: correlation_id preserved
    assert result['correlation_id'] == correlation_id
    
    stmt = select(AIMessage).where(
        AIMessage.correlation_id == correlation_id
    )
    ai_message = db_session.execute(stmt).scalar_one()
    assert ai_message.correlation_id == correlation_id


@pytest.mark.integration
@pytest.mark.skip(reason="Awaiting T047 PerformanceService and T048 CoachNova orchestrator implementation")
async def test_coachnova_safety_filter_rejection(db_session):
    """Test that unsafe content is rejected and not stored."""
    
    # Arrange
    worker_id = WORKER_JAHANGIR_ID
    
    # Mock OpenAI to return inappropriate content
    mock_openai_response = MagicMock()
    mock_openai_response.choices = [
        MagicMock(
            message=MagicMock(
                content="তুমি খুব খারাপ কর্মী। তোমাকে লজ্জা করা উচিত।"  # Shaming language
            )
        )
    ]
    mock_openai_response.model = "gpt-4o-mini"
    mock_openai_response.usage.total_tokens = 80
    
    # Act: Try to generate coaching
    with patch('openai.ChatCompletion.create', return_value=mock_openai_response):
        from src.ai.coachnova import CoachNovaOrchestrator
        from src.services.performance_service import PerformanceService
        
        performance_signals = await PerformanceService.get_signals(
            worker_id=worker_id,
            db=db_session
        )
        
        orchestrator = CoachNovaOrchestrator()
        result = await orchestrator.generate_coaching(
            worker_id=worker_id,
            performance_signals=performance_signals,
            correlation_id=uuid4(),
            db=db_session
        )
    
    # Assert: Should fail safety check
    assert result['success'] is False
    assert result['reason'] == 'safety_violation'
    assert result['message_id'] is None
    
    # Verify no unsafe message stored
    stmt = select(AIMessage).where(
        AIMessage.user_id == worker_id,
        AIMessage.agent_type == 'coachnova'
    )
    messages = db_session.execute(stmt).scalars().all()
    
    # Either no messages, or if stored for audit, marked as unsafe
    for msg in messages:
        if msg.safety_checks:
            assert msg.safety_checks.get('safe') is not False or msg.delivery_status == DeliveryStatus.FAILED
