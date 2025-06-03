require('dotenv').config();
const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const passport = require('passport');
const rateLimit = require('express-rate-limit');
const { initTelemetry } = require('./telemetry');
const { logger } = require('./utils/logger');
const { statsClient } = require('./utils/metrics');
const { connectDB, pool } = require('./db');
const { redisClient } = require('./cache/redis');
const authRoutes = require('./routes/auth');
const validateRoutes = require('./routes/validate');
const { tracingMiddleware } = require('./middleware/tracing');
const { errorHandler } = require('./middleware/errorHandler');

// Initialize telemetry
const tracer = initTelemetry();

const app = express();
const PORT = process.env.PORT || 3001;

// Security middleware
app.use(helmet());
app.use(cors({
  origin: process.env.FRONTEND_URL || 'http://localhost:3000',
  credentials: true
}));

// Body parsing
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Tracing middleware
app.use(tracingMiddleware);

// Rate limiting (using memory store for now)
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: 'Too many requests from this IP',
  standardHeaders: true,
  legacyHeaders: false,
});

app.use('/api/', limiter);

// Passport initialization
app.use(passport.initialize());
require('./oauth/google');
require('./oauth/github');

// Routes
app.use('/api/auth', authRoutes);
app.use('/api/validate', validateRoutes);

// Health check
app.get('/health', (req, res) => {
  const span = tracer.startSpan('health-check');
  
  const health = {
    status: 'healthy',
    service: 'auth-service',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    redis: redisClient.isReady ? 'connected' : 'disconnected',
  };

  span.setAttribute('health.status', health.status);
  span.setAttribute('health.redis', health.redis);
  span.end();

  statsClient.increment('health_check');
  res.json(health);
});

// Error handling
app.use(errorHandler);

// Start server
async function start() {
  try {
    // Connect to database
    await connectDB();
    logger.info('Database connected');

    // Connect to Redis
    await redisClient.connect();
    logger.info('Redis connected');

    app.listen(PORT, () => {
      logger.info(`Auth service listening on port ${PORT}`);
      statsClient.increment('service_started');
    });
  } catch (error) {
    logger.error('Failed to start service', error);
    process.exit(1);
  }
}

// Graceful shutdown
process.on('SIGTERM', async () => {
  logger.info('SIGTERM signal received');
  
  // Close connections
  await redisClient.quit();
  await pool.end();
  
  process.exit(0);
});

start();
