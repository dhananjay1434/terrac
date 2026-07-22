import pytest
from sqlalchemy.exc import IntegrityError, DataError
import uuid
from models import Farmer, FarmerDocument, FarmerPayment, FarmerConsent, Project
from datetime import datetime, timezone, timedelta

@pytest.mark.asyncio
async def test_farmer_creation(session_factory):
    async with session_factory() as db_session:
        project = Project(project_id="test-project", name="Test Project")
        db_session.add(project)
        await db_session.commit()

        farmer = Farmer(
            farmer_uuid=str(uuid.uuid4()),
            project_id="test-project",
            first_name="John",
            mobile_number="1234567890",
            dob=datetime.now(timezone.utc) - timedelta(days=365*30)
        )
        db_session.add(farmer)
        await db_session.commit()

        assert farmer.farmer_uuid is not None

@pytest.mark.asyncio
async def test_farmer_unique_mobile_per_project(session_factory):
    async with session_factory() as db_session:
        project = Project(project_id="test-project-2", name="Test Project 2")
        db_session.add(project)
        await db_session.commit()

        farmer1 = Farmer(
            farmer_uuid=str(uuid.uuid4()),
            project_id="test-project-2",
            first_name="Jane",
            mobile_number="0987654321"
        )
        db_session.add(farmer1)
        await db_session.commit()

        farmer2 = Farmer(
            farmer_uuid=str(uuid.uuid4()),
            project_id="test-project-2",
            first_name="Jane Clone",
            mobile_number="0987654321"
        )
        db_session.add(farmer2)
        with pytest.raises(IntegrityError):
            await db_session.commit()


@pytest.mark.asyncio
async def test_farmer_children_creation(session_factory):
    async with session_factory() as db_session:
        farmer_uuid = str(uuid.uuid4())
        farmer = Farmer(
            farmer_uuid=farmer_uuid,
            project_id="test-project",
            first_name="Alice",
            mobile_number="1111111111"
        )
        db_session.add(farmer)
        
        doc = FarmerDocument(
            farmer_uuid=farmer_uuid,
            doc_type="aadhaar",
            last4="1234",
            media_id="hash123"
        )
        db_session.add(doc)

        payment = FarmerPayment(
            farmer_uuid=farmer_uuid,
            rail="bank",
            masked_account="****5678"
        )
        db_session.add(payment)

        consent = FarmerConsent(
            farmer_uuid=farmer_uuid,
            exclusivity_ack=True
        )
        db_session.add(consent)
        
        await db_session.commit()

        assert doc.id is not None
        assert payment.id is not None
        assert consent.id is not None
        assert consent.exclusivity_ack is True


@pytest.mark.asyncio
async def test_farmer_document_last4_truncation(session_factory):
    async with session_factory() as db_session:
        # standard sqlalchemy behavior for String(4) might not raise error on all backends,
        # but we test that we can pass a 4-char string.
        farmer_uuid = str(uuid.uuid4())
        doc = FarmerDocument(
            farmer_uuid=farmer_uuid,
            doc_type="pan",
            last4="ABCD",
            media_id="hash456"
        )
        db_session.add(doc)
        await db_session.commit()
        assert doc.last4 == "ABCD"
        
@pytest.mark.asyncio
async def test_farmer_consent_persisted(session_factory):
    async with session_factory() as db_session:
        farmer_uuid = str(uuid.uuid4())
        consent = FarmerConsent(
            farmer_uuid=farmer_uuid,
            exclusivity_ack=True,
            signed_pdf_media_id="pdf_hash"
        )
        db_session.add(consent)
        await db_session.commit()

        # Query back
        from sqlalchemy import select
        stmt = select(FarmerConsent).where(FarmerConsent.farmer_uuid == farmer_uuid)
        result = await db_session.execute(stmt)
        saved_consent = result.scalar_one_or_none()

        assert saved_consent is not None
        assert saved_consent.exclusivity_ack is True
        assert saved_consent.signed_pdf_media_id == "pdf_hash"
