"""
Canary API - FastAPI Example with Full Observability
Demonstrates OpenTelemetry tracing, StatsD metrics, and structured logging
"""

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional

import statsd
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.propagate import inject
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode
from pydantic import BaseModel, Field

# Environment configuration
SERVICE_NAME = os.getenv("SERVICE_NAME", "canary-api")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")
OTLP_ENDPOINT = os.getenv("OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
STATSD_HOST = os.getenv("STATSD_HOST", "localhost")
STATSD_PORT = int(os.getenv("STATSD_PORT", "8125"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# In-memory storage for demo purposes
nest_storage: Dict[str, dict] = {}

# Pydantic models for request/response validation
class NestCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(default="standard", pattern="^(standard|deluxe|premium)$")
    material: Optional[str] = Field(default="twigs", max_length=50)
    
class NestResponse(BaseModel):
    id: str
    name: str
    type: str
    material: str
    created_at: str
    
class ChirpResponse(BaseModel):
    status: str
    timestamp: str
    service_name: str
    service_version: str

# Setup structured logging with JSON formatter
class JSONFormatter(logging.Formatter):
    def format(self, record):
        # Get trace context if available
        span = trace.get_current_span()
        trace_id = ""
        span_id = ""
        
        if span and span.is_recording():
            ctx = span.get_span_context()
            trace_id = format(ctx.trace_id, '032x')
            span_id = format(ctx.span_id, '016x')
        
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": SERVICE_NAME,
            "service_version": SERVICE_VERSION,
            "message": record.getMessage(),
            "logger": record.name,
            "trace_id": trace_id,
            "span_id": span_id,
        }
        
        # Add any extra fields
        if hasattr(record, 'extra_fields'):
            log_record.update(record.extra_fields)
            
        return json.dumps(log_record)

# Configure logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.handlers = [handler]
logger.setLevel(getattr(logging, LOG_LEVEL))

# Initialize telemetry providers
def init_telemetry():
    """Initialize OpenTelemetry tracing"""
    # Create resource with service information
    resource = Resource.create({
        "service.name": SERVICE_NAME,
        "service.version": SERVICE_VERSION,
        "service.instance.id": os.getenv("HOSTNAME", "local"),
        "deployment.environment": os.getenv("ENVIRONMENT", "development")
    })
    
    # Setup tracer provider
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)
    
    # Configure OTLP exporter
    otlp_exporter = OTLPSpanExporter(endpoint=OTLP_ENDPOINT)
    span_processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(span_processor)
    
    # Enable logging instrumentation
    LoggingInstrumentor().instrument()
    
    return provider

# Initialize StatsD client
statsd_client = statsd.StatsClient(
    host=STATSD_HOST,
    port=STATSD_PORT,
    prefix=f'{SERVICE_NAME.replace("-", "_")}'
)

# Get tracer instance
tracer = trace.get_tracer(__name__, SERVICE_VERSION)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifecycle"""
    # Startup
    logger.info("Starting Canary API", extra={"extra_fields": {
        "event": "startup",
        "otlp_endpoint": OTLP_ENDPOINT,
        "statsd_endpoint": f"{STATSD_HOST}:{STATSD_PORT}"
    }})
    
    # Initialize telemetry
    provider = init_telemetry()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Canary API", extra={"extra_fields": {"event": "shutdown"}})
    
    # Ensure all telemetry is flushed
    if provider:
        provider.shutdown()

# Create FastAPI app
app = FastAPI(
    title="Canary API",
    description="Example API with full observability integration",
    version=SERVICE_VERSION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instrument FastAPI for automatic tracing
FastAPIInstrumentor.instrument_app(app)

@app.get("/chirp", response_model=ChirpResponse)
async def chirp():
    """Health check endpoint that returns service status"""
    start_time = time.time()
    
    with tracer.start_as_current_span("chirp_handler") as span:
        # Record metrics
        statsd_client.incr('requests', tags=['endpoint:chirp', 'method:GET'])
        
        # Add span attributes
        span.set_attributes({
            "http.route": "/chirp",
            "health.status": "healthy"
        })
        
        # Log the request
        logger.info("Handling chirp request", extra={"extra_fields": {
            "endpoint": "/chirp",
            "method": "GET"
        }})
        
        # Simulate some processing
        await asyncio.sleep(0.01)
        
        response = ChirpResponse(
            status="alive",
            timestamp=datetime.utcnow().isoformat() + "Z",
            service_name=SERVICE_NAME,
            service_version=SERVICE_VERSION
        )
        
        # Record response time
        elapsed = (time.time() - start_time) * 1000
        statsd_client.timing('request_duration', elapsed, tags=['endpoint:chirp', 'method:GET'])
        
        return response

@app.post("/nest", response_model=NestResponse, status_code=201)
async def create_nest(nest: NestCreate):
    """Create a new nest resource with trace propagation"""
    start_time = time.time()
    
    with tracer.start_as_current_span("nest_handler") as span:
        # Record metrics
        statsd_client.incr('requests', tags=['endpoint:nest', 'method:POST'])
        
        # Add span attributes
        span.set_attributes({
            "http.route": "/nest",
            "nest.type": nest.type,
            "nest.material": nest.material,
            "request.size": len(nest.json())
        })
        
        # Log the request
        logger.info("Creating nest entry", extra={"extra_fields": {
            "endpoint": "/nest",
            "method": "POST",
            "nest_type": nest.type,
            "request_size": len(nest.json())
        }})
        
        try:
            # Create nested span for business logic
            with tracer.start_as_current_span("create_nest_logic") as logic_span:
                # Generate unique ID
                nest_id = f"nest_{int(time.time() * 1000)}_{len(nest_storage)}"
                
                # Simulate some processing
                await asyncio.sleep(0.02)
                
                # Store the nest
                nest_data = {
                    "id": nest_id,
                    "name": nest.name,
                    "type": nest.type,
                    "material": nest.material,
                    "created_at": datetime.utcnow().isoformat() + "Z"
                }
                nest_storage[nest_id] = nest_data
                
                # Record custom metric
                statsd_client.gauge('nest_count', len(nest_storage))
                statsd_client.incr('nests_created', tags=[f'type:{nest.type}'])
                
                logic_span.set_attribute("nest.id", nest_id)
                
            # Create response
            response = NestResponse(**nest_data)
            
            # Log success
            logger.info("Nest created successfully", extra={"extra_fields": {
                "nest_id": nest_id,
                "nest_type": nest.type
            }})
            
        except Exception as e:
            # Handle errors with proper span status
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            statsd_client.incr('errors', tags=['endpoint:nest', 'method:POST'])
            logger.error(f"Error creating nest: {str(e)}", extra={"extra_fields": {
                "error": str(e),
                "endpoint": "/nest"
            }})
            raise HTTPException(status_code=500, detail="Failed to create nest")
        
        finally:
            # Record response time
            elapsed = (time.time() - start_time) * 1000
            statsd_client.timing('request_duration', elapsed, tags=['endpoint:nest', 'method:POST'])
        
        return response

@app.get("/flock", response_model=List[NestResponse])
async def list_nests(
    limit: int = Query(default=10, ge=1, le=100, description="Number of nests to return"),
    offset: int = Query(default=0, ge=0, description="Number of nests to skip")
):
    """List nest resources with pagination"""
    start_time = time.time()
    
    with tracer.start_as_current_span("flock_handler") as span:
        # Record metrics
        statsd_client.incr('requests', tags=['endpoint:flock', 'method:GET'])
        
        # Add span attributes
        span.set_attributes({
            "http.route": "/flock",
            "pagination.limit": limit,
            "pagination.offset": offset,
            "flock.total_size": len(nest_storage)
        })
        
        # Log the request
        logger.info("Listing nests", extra={"extra_fields": {
            "endpoint": "/flock",
            "method": "GET",
            "limit": limit,
            "offset": offset,
            "total_nests": len(nest_storage)
        }})
        
        # Create nested span for data retrieval
        with tracer.start_as_current_span("retrieve_nests") as data_span:
            # Get paginated results
            all_nests = list(nest_storage.values())
            paginated_nests = all_nests[offset:offset + limit]
            
            data_span.set_attributes({
                "result.count": len(paginated_nests),
                "result.has_more": (offset + limit) < len(all_nests)
            })
            
            # Simulate some processing
            await asyncio.sleep(0.01)
        
        # Convert to response models
        response = [NestResponse(**nest) for nest in paginated_nests]
        
        # Record response metrics
        statsd_client.gauge('flock_query_size', len(response))
        
        # Record response time
        elapsed = (time.time() - start_time) * 1000
        statsd_client.timing('request_duration', elapsed, tags=['endpoint:flock', 'method:GET'])
        
        return response

@app.get("/metrics/health")
async def health_check():
    """Internal health check for monitoring systems"""
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "telemetry": {
            "tracing": "enabled",
            "metrics": "enabled",
            "logging": "enabled"
        }
    }

# Error handler with telemetry
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler with telemetry"""
    span = trace.get_current_span()
    if span and span.is_recording():
        span.set_status(Status(StatusCode.ERROR, str(exc)))
        span.record_exception(exc)
    
    statsd_client.incr('unhandled_errors')
    logger.error(f"Unhandled exception: {str(exc)}", extra={"extra_fields": {
        "error": str(exc),
        "path": request.url.path
    }})
    
    return {"detail": "Internal server error"}, 500

if __name__ == "__main__":
    # Run with uvicorn for production-ready async server
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        log_config=None,  # Use our custom logging
        reload=os.getenv("RELOAD", "false").lower() == "true"
    )
