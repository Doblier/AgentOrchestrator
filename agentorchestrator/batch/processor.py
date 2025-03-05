"""Batch processing module for AgentOrchestrator.

Handles batch processing of agent requests with async execution.
"""

import asyncio
import threading
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from redis import Redis


class BatchJob(BaseModel):
    """Batch job model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    agent: str
    inputs: list[dict[str, Any]]
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    results: list[dict[str, Any]] = []
    error: str | None = None


class BatchProcessor:
    """Async batch processor for agent requests."""

    def __init__(self, redis_client: Redis):
        """Initialize batch processor.

        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client
        self._processing = False
        self._processor_thread = None
        self._event_loop = None

    def _get_job_key(self, job_id: str) -> str:
        """Generate Redis key for job.

        Args:
            job_id: Job ID

        Returns:
            str: Redis key
        """
        return f"batch:job:{job_id}"

    async def submit_job(self, agent: str, inputs: list[dict[str, Any]]) -> BatchJob:
        """Submit a new batch job.

        Args:
            agent: Name of the agent to execute
            inputs: List of input data for each request

        Returns:
            BatchJob: Created batch job
        """
        job = BatchJob(agent=agent, inputs=inputs)

        # Save job to Redis
        self.redis.set(self._get_job_key(job.id), job.json())

        # Add to processing queue
        self.redis.lpush("batch:queue", job.id)

        return job

    async def get_job(self, job_id: str) -> BatchJob | None:
        """Get job status and results.

        Args:
            job_id: Job ID to retrieve

        Returns:
            Optional[BatchJob]: Job data if found
        """
        job_data = self.redis.get(self._get_job_key(job_id))
        if job_data:
            return BatchJob.parse_raw(job_data)
        return None

    async def process_job(self, job: BatchJob, workflow_func) -> BatchJob:
        """Process a single batch job.

        Args:
            job: Batch job to process
            workflow_func: Agent workflow function

        Returns:
            BatchJob: Updated job with results
        """
        try:
            job.status = "processing"
            await self._save_job(job)

            # Process each input
            results = []
            for input_data in job.inputs:
                try:
                    result = await workflow_func(input_data)
                    results.append({"status": "success", "data": result})
                except Exception as e:
                    results.append({"status": "error", "error": str(e)})

            job.results = results
            job.status = "completed"
            job.completed_at = datetime.utcnow()

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            job.completed_at = datetime.utcnow()

        await self._save_job(job)
        return job

    async def _save_job(self, job: BatchJob) -> None:
        """Save job to Redis."""
        await self.redis.set(self._get_job_key(job.id), job.model_dump_json())

    def _processor_loop(self, get_workflow_func):
        """Background processor loop.

        Args:
            get_workflow_func: Function to get agent workflow
        """
        self._event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._event_loop)

        async def process_loop():
            while self._processing:
                # Get next job from queue
                job_id = await self.redis.rpop("batch:queue")
                if not job_id:
                    await asyncio.sleep(1)
                    continue

                # Get job data
                job_data = await self.redis.get(self._get_job_key(job_id))
                if not job_data:
                    continue

                job = BatchJob.parse_raw(job_data)

                # Get workflow function
                workflow_func = get_workflow_func(job.agent)
                if not workflow_func:
                    job.status = "failed"
                    job.error = f"Agent {job.agent} not found"
                    await self._save_job(job)
                    continue

                # Process job
                await self.process_job(job, workflow_func)

        self._event_loop.run_until_complete(process_loop())
        self._event_loop.close()

    async def start_processing(self, get_workflow_func):
        """Start processing jobs from queue.

        Args:
            get_workflow_func: Function to get agent workflow
        """
        if self._processing:
            return

        self._processing = True
        self._processor_thread = threading.Thread(
            target=self._processor_loop,
            args=(get_workflow_func,),
            daemon=True,
        )
        self._processor_thread.start()

    async def stop_processing(self):
        """Stop processing jobs."""
        if not self._processing:
            return

        self._processing = False
        if self._processor_thread:
            self._processor_thread.join(timeout=5)
            self._processor_thread = None
