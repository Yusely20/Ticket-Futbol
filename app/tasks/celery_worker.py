import logging
import json
from datetime import datetime
from celery import Celery
from celery.signals import after_setup_task_logger
from app.core.config import settings
from app.db.database import SessionLocal
from app.models.ticket import Ticket
from app.services.ticket_generator import ticket_generator_service
import redis

# Initialize Celery app
celery_app = Celery(
    "tasks", 
    broker=settings.CELERY_BROKER_URL, 
    backend=settings.CELERY_RESULT_BACKEND
)

# Optional configuration overrides
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_concurrency=4 # Performance & concurrency limit control
)

logger = logging.getLogger(__name__)

# Redis client for DLQ
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
    decode_responses=True
)

@after_setup_task_logger.connect
def setup_task_logger(logger, *args, **kwargs):
    # Customize log format to show task name and standard info
    formatter = logging.Formatter(
        '[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s'
    )
    for handler in logger.handlers:
        handler.setFormatter(formatter)

@celery_app.task(
    name="tasks.generate_ticket_task",
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True, # Exponential backoff: 2s, 4s, 8s...
    retry_backoff_max=600
)
def generate_ticket_task(self, ticket_id: int, correlation_id: str = None):
    """
    Celery task that runs asynchronously to generate a QR Code ticket by calling
    the simulated Serverless Lambda component.
    """
    cid_prefix = f"[{correlation_id}] " if correlation_id else "[N/A] "
    logger.info(f"{cid_prefix}Asynchronous task started: generating ticket ID {ticket_id}")
    
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            logger.error(f"{cid_prefix}Ticket ID {ticket_id} not found in database. Generation aborted.")
            return False

        ticket_url = f"/t/{ticket.ticket_uuid}"
        
        # Invoke Lambda Generator passing correlation ID in task execution context
        qr_url = ticket_generator_service.generate_qr_code_lambda(
            ticket.ticket_uuid, 
            ticket_url, 
            correlation_id=correlation_id
        )
        
        # Save to database
        ticket.qr_code_url = qr_url
        db.commit()
        
        logger.info(f"{cid_prefix}Asynchronous QR generation complete for ticket ID {ticket_id}. Path: {qr_url}")
        return True
        
    except Exception as exc:
        db.rollback()
        logger.error(f"{cid_prefix}Error in Celery worker task for ticket ID {ticket_id} (Attempt {self.request.retries}/{self.max_retries}): {exc}")
        
        # Dead Letter Queue (DLQ) if max retries are exceeded
        if self.request.retries >= self.max_retries:
            logger.error(f"{cid_prefix}Max retries reached for ticket ID {ticket_id}. Moving message to Dead Letter Queue (DLQ: dlq:tickets_fallidos)")
            try:
                dlq_payload = json.dumps({
                    "ticket_id": ticket_id,
                    "correlation_id": correlation_id,
                    "error": str(exc),
                    "failed_at": datetime.utcnow().isoformat()
                })
                redis_client.rpush("dlq:tickets_fallidos", dlq_payload)
            except Exception as redis_err:
                logger.error(f"{cid_prefix}Failed to push ticket {ticket_id} to DLQ: {redis_err}")
        
        # Re-raise the exception to trigger the Celery retry mechanism
        raise exc
    finally:
        db.close()
