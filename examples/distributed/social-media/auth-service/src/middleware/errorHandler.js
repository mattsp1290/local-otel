const { logger } = require('../utils/logger');
const opentelemetry = require('@opentelemetry/api');

function errorHandler(err, req, res, next) {
  // Get the current span
  const span = req.span || opentelemetry.trace.getActiveSpan();
  
  if (span) {
    // Record the exception in the span
    span.recordException(err);
    span.setStatus({
      code: opentelemetry.SpanStatusCode.ERROR,
      message: err.message
    });
    
    // Add error attributes
    span.setAttributes({
      'error.type': err.name || 'Error',
      'error.message': err.message,
      'error.stack': err.stack
    });
  }

  // Log the error with trace context
  logger.error('Request error', {
    error: err.message,
    stack: err.stack,
    path: req.path,
    method: req.method,
    traceId: req.traceId,
    spanId: req.spanId
  });

  // Determine status code
  const statusCode = err.statusCode || err.status || 500;

  // Send error response
  res.status(statusCode).json({
    error: {
      message: err.message || 'Internal server error',
      code: err.code || 'INTERNAL_ERROR',
      ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
    },
    traceId: req.traceId
  });
}

module.exports = { errorHandler };
