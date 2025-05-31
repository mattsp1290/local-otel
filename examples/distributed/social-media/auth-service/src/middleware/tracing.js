const opentelemetry = require('@opentelemetry/api');
const { SemanticAttributes } = require('@opentelemetry/semantic-conventions');

// Middleware to add tracing context to requests
function tracingMiddleware(req, res, next) {
  const tracer = opentelemetry.trace.getTracer('auth-service');
  
  // Extract trace context from headers
  const parentContext = opentelemetry.propagation.extract(
    opentelemetry.context.active(),
    req.headers
  );

  // Start a new span with the parent context
  const span = tracer.startSpan(
    `${req.method} ${req.path}`,
    {
      kind: opentelemetry.SpanKind.SERVER,
      attributes: {
        [SemanticAttributes.HTTP_METHOD]: req.method,
        [SemanticAttributes.HTTP_ROUTE]: req.route?.path || req.path,
        [SemanticAttributes.HTTP_URL]: req.url,
        [SemanticAttributes.HTTP_TARGET]: req.originalUrl,
        [SemanticAttributes.HTTP_HOST]: req.hostname,
        [SemanticAttributes.HTTP_SCHEME]: req.protocol,
        [SemanticAttributes.HTTP_USER_AGENT]: req.get('user-agent'),
        [SemanticAttributes.NET_PEER_IP]: req.ip,
      },
    },
    parentContext
  );

  // Add trace ID to request for logging
  const spanContext = span.spanContext();
  req.traceId = spanContext.traceId;
  req.spanId = spanContext.spanId;
  req.span = span;

  // Add trace headers to response for correlation
  res.setHeader('X-Trace-Id', spanContext.traceId);
  res.setHeader('X-Span-Id', spanContext.spanId);

  // Handle response
  const originalSend = res.send;
  res.send = function (data) {
    // Set response attributes
    span.setAttributes({
      [SemanticAttributes.HTTP_STATUS_CODE]: res.statusCode,
      'http.response_content_length': Buffer.byteLength(data || ''),
    });

    // Set span status based on HTTP status
    if (res.statusCode >= 400) {
      span.setStatus({
        code: opentelemetry.SpanStatusCode.ERROR,
        message: `HTTP ${res.statusCode}`,
      });
    }

    span.end();
    originalSend.call(this, data);
  };

  // Handle errors
  res.on('error', (err) => {
    span.recordException(err);
    span.setStatus({
      code: opentelemetry.SpanStatusCode.ERROR,
      message: err.message,
    });
    span.end();
  });

  // Continue with context
  opentelemetry.context.with(
    opentelemetry.trace.setSpan(parentContext, span),
    () => {
      next();
    }
  );
}

module.exports = { tracingMiddleware };
