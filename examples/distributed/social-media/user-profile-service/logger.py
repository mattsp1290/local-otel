"""
Structured logging configuration with trace context
"""

import logging
import json
import sys
from datetime import datetime
from opentelemetry import trace
from pythonjsonlogger import jsonlogger

# Custom JSON formatter that includes trace context
class TraceContextFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        # Add service info
        log_record['service'] = 'user-profile-service'
        log_record['service_version'] = '1.0.0'
        
        # Add trace context if available
        span = trace.get_current_span()
        if span and span.is_recording():
            ctx = span.get_span_context()
            log_record['trace_id'] = format(ctx.trace_id, '032x')
            log_record['span_id'] = format(ctx.span_id, '016x')
        
        # Add log level
        log_record['level'] = record.levelname
        
        # Remove internal fields
        for field in ['color_message', 'asctime']:
            log_record.pop(field, None)

def setup_logging():
    """Configure structured JSON logging"""
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    logger.handlers = []
    
    # Create console handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    formatter = TraceContextFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Set log level from environment
    import os
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    return logger

# Create logger instance
logger = setup_logging()
