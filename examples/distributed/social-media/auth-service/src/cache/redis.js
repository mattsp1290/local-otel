const redis = require('redis');
const { logger } = require('../utils/logger');
const opentelemetry = require('@opentelemetry/api');

// Create Redis client
const redisClient = redis.createClient({
  url: process.env.REDIS_URL || 'redis://localhost:6379',
  socket: {
    reconnectStrategy: (retries) => {
      if (retries > 10) {
        logger.error('Redis reconnection limit reached');
        return false;
      }
      return Math.min(retries * 100, 3000);
    }
  }
});

// Redis event handlers
redisClient.on('error', (err) => {
  logger.error('Redis Client Error', err);
});

redisClient.on('connect', () => {
  logger.info('Redis Client Connected');
});

redisClient.on('ready', () => {
  logger.info('Redis Client Ready');
});

// Traced Redis operations
const tracedRedis = {
  async get(key) {
    const tracer = opentelemetry.trace.getTracer('auth-service');
    const span = tracer.startSpan('redis.get', {
      attributes: {
        'db.system': 'redis',
        'db.operation': 'get',
        'db.redis.key': key
      }
    });

    try {
      const value = await redisClient.get(key);
      span.setAttribute('cache.hit', value !== null);
      return value;
    } catch (error) {
      span.recordException(error);
      span.setStatus({
        code: opentelemetry.SpanStatusCode.ERROR,
        message: error.message
      });
      throw error;
    } finally {
      span.end();
    }
  },

  async set(key, value, options = {}) {
    const tracer = opentelemetry.trace.getTracer('auth-service');
    const span = tracer.startSpan('redis.set', {
      attributes: {
        'db.system': 'redis',
        'db.operation': 'set',
        'db.redis.key': key
      }
    });

    try {
      const result = await redisClient.set(key, value, options);
      return result;
    } catch (error) {
      span.recordException(error);
      span.setStatus({
        code: opentelemetry.SpanStatusCode.ERROR,
        message: error.message
      });
      throw error;
    } finally {
      span.end();
    }
  },

  async del(key) {
    const tracer = opentelemetry.trace.getTracer('auth-service');
    const span = tracer.startSpan('redis.del', {
      attributes: {
        'db.system': 'redis',
        'db.operation': 'del',
        'db.redis.key': key
      }
    });

    try {
      const result = await redisClient.del(key);
      return result;
    } catch (error) {
      span.recordException(error);
      span.setStatus({
        code: opentelemetry.SpanStatusCode.ERROR,
        message: error.message
      });
      throw error;
    } finally {
      span.end();
    }
  },

  async exists(key) {
    const tracer = opentelemetry.trace.getTracer('auth-service');
    const span = tracer.startSpan('redis.exists', {
      attributes: {
        'db.system': 'redis',
        'db.operation': 'exists',
        'db.redis.key': key
      }
    });

    try {
      const result = await redisClient.exists(key);
      return result;
    } catch (error) {
      span.recordException(error);
      span.setStatus({
        code: opentelemetry.SpanStatusCode.ERROR,
        message: error.message
      });
      throw error;
    } finally {
      span.end();
    }
  }
};

module.exports = { redisClient, tracedRedis };
