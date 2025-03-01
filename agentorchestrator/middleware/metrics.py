"""Metrics middleware for AgentOrchestrator.

Collects and exposes Prometheus metrics.
"""
import time
from typing import Optional, Callable
from fastapi import Request
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel


class MetricsConfig(BaseModel):
    """Configuration for metrics collection."""
    enabled: bool = True
    prefix: str = "ao"  # AgentOrchestrator prefix


class MetricsCollector:
    """Prometheus metrics collector."""
    
    def __init__(self, config: Optional[MetricsConfig] = None):
        """Initialize metrics collector.
        
        Args:
            config: Metrics configuration
        """
        self.config = config or MetricsConfig()
        
        # Initialize metrics
        self.requests_total = Counter(
            f"{self.config.prefix}_requests_total",
            "Total number of requests",
            ["method", "path", "status"]
        )
        
        self.request_duration_seconds = Histogram(
            f"{self.config.prefix}_request_duration_seconds",
            "Request duration in seconds",
            ["method", "path"]
        )
        
        self.agent_invocations_total = Counter(
            f"{self.config.prefix}_agent_invocations_total",
            "Total number of agent invocations",
            ["agent", "status"]
        )
        
        self.agent_duration_seconds = Histogram(
            f"{self.config.prefix}_agent_duration_seconds",
            "Agent execution duration in seconds",
            ["agent"]
        )
        
        self.cache_hits_total = Counter(
            f"{self.config.prefix}_cache_hits_total",
            "Total number of cache hits",
            ["path"]
        )
        
        self.rate_limits_total = Counter(
            f"{self.config.prefix}_rate_limits_total",
            "Total number of rate limit hits",
            ["path"]
        )


class MetricsMiddleware:
    """Prometheus metrics middleware."""
    
    def __init__(self, app: Callable, config: Optional[MetricsConfig] = None):
        """Initialize metrics middleware.
        
        Args:
            app: ASGI application
            config: Metrics configuration
        """
        self.app = app
        self.config = config or MetricsConfig()
        self.collector = MetricsCollector(self.config)

    async def handle_metrics_request(self, send):
        """Handle /metrics endpoint request.
        
        Args:
            send: ASGI send function
        """
        metrics_data = generate_latest()
        
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", CONTENT_TYPE_LATEST.encode()),
                (b"content-length", str(len(metrics_data)).encode()),
            ],
        })
        
        await send({
            "type": "http.response.body",
            "body": metrics_data,
        })

    async def __call__(self, scope, receive, send):
        """ASGI middleware handler.
        
        Args:
            scope: ASGI scope
            receive: ASGI receive function
            send: ASGI send function
            
        Returns:
            Response from next middleware
        """
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
            
        request = Request(scope)
        
        # Handle /metrics endpoint
        if request.url.path == "/metrics":
            return await self.handle_metrics_request(send)
            
        # Skip metrics collection if disabled
        if not self.config.enabled:
            return await self.app(scope, receive, send)
            
        method = request.method
        path = request.url.path
        start_time = time.time()
        
        # Capture response
        status_code = 0
        
        async def metrics_send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)
            
        try:
            response = await self.app(scope, receive, metrics_send)
            
            # Record metrics
            duration = time.time() - start_time
            self.collector.requests_total.labels(
                method=method,
                path=path,
                status=status_code
            ).inc()
            
            self.collector.request_duration_seconds.labels(
                method=method,
                path=path
            ).observe(duration)
            
            # Record agent metrics if applicable
            if path.startswith("/api/v1/agent/"):
                agent_name = path.split("/")[-1]
                self.collector.agent_invocations_total.labels(
                    agent=agent_name,
                    status="success" if status_code < 400 else "error"
                ).inc()
                
                self.collector.agent_duration_seconds.labels(
                    agent=agent_name
                ).observe(duration)
                
            return response
            
        except Exception:
            # Record error metrics
            self.collector.requests_total.labels(
                method=method,
                path=path,
                status=500
            ).inc()
            raise 