const express = require('express');
const jwt = require('jsonwebtoken');
const { tracedRedis } = require('../cache/redis');
const { userDb } = require('../db');
const { logger } = require('../utils/logger');
const { metrics } = require('../utils/metrics');

const router = express.Router();
const JWT_SECRET = process.env.JWT_SECRET || 'default-secret-change-in-production';

// Validate token endpoint (for other services to verify tokens)
router.post('/token', async (req, res) => {
  const span = req.span;
  const { token } = req.body;
  
  if (!token) {
    return res.status(400).json({ valid: false, error: 'Token required' });
  }

  try {
    span.setAttributes({
      'auth.action': 'validate_token'
    });

    // Try to decode the token
    const decoded = jwt.verify(token, JWT_SECRET);
    
    // Check if session exists in Redis
    const sessionData = await tracedRedis.get(`session:${token}`);
    
    if (sessionData) {
      const user = JSON.parse(sessionData);
      metrics.trackTokenOperation('validate', true);
      metrics.trackCacheOperation('session_validate', true);
      
      span.setAttribute('user.id', user.id);
      span.setAttribute('cache.hit', true);
      
      return res.json({
        valid: true,
        user: {
          id: user.id,
          email: user.email,
          username: user.username
        }
      });
    }
    
    // If not in cache, check database
    const user = await userDb.findUserById(decoded.id);
    
    if (user) {
      // Update cache
      await tracedRedis.set(
        `session:${token}`,
        JSON.stringify(user),
        { EX: 86400 }
      );
      
      metrics.trackTokenOperation('validate', true);
      metrics.trackCacheOperation('session_validate', false);
      
      span.setAttribute('user.id', user.id);
      span.setAttribute('cache.hit', false);
      
      return res.json({
        valid: true,
        user: {
          id: user.id,
          email: user.email,
          username: user.username
        }
      });
    }
    
    // Token decoded but user not found
    metrics.trackTokenOperation('validate', false);
    res.status(401).json({ valid: false, error: 'User not found' });
    
  } catch (error) {
    if (error.name === 'TokenExpiredError') {
      span.setAttribute('token.expired', true);
      metrics.trackTokenOperation('validate_expired', false);
      return res.status(401).json({ valid: false, error: 'Token expired' });
    }
    
    if (error.name === 'JsonWebTokenError') {
      span.setAttribute('token.invalid', true);
      metrics.trackTokenOperation('validate_invalid', false);
      return res.status(401).json({ valid: false, error: 'Invalid token' });
    }
    
    logger.error('Token validation error', error);
    res.status(500).json({ valid: false, error: 'Validation failed' });
  }
});

// Get user info from token (internal service endpoint)
router.get('/user', async (req, res) => {
  const span = req.span;
  const authHeader = req.headers.authorization;
  
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'No token provided' });
  }
  
  const token = authHeader.substring(7);
  
  try {
    span.setAttributes({
      'auth.action': 'get_user_info'
    });

    // Decode token
    const decoded = jwt.verify(token, JWT_SECRET);
    
    // Check cache first
    const sessionData = await tracedRedis.get(`session:${token}`);
    
    if (sessionData) {
      const user = JSON.parse(sessionData);
      metrics.trackCacheOperation('user_info', true);
      
      return res.json({
        id: user.id,
        email: user.email,
        username: user.username,
        provider: user.provider || 'local'
      });
    }
    
    // Fallback to database
    const user = await userDb.findUserById(decoded.id);
    
    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }
    
    metrics.trackCacheOperation('user_info', false);
    
    // Update cache
    await tracedRedis.set(
      `session:${token}`,
      JSON.stringify(user),
      { EX: 86400 }
    );
    
    res.json({
      id: user.id,
      email: user.email,
      username: user.username,
      provider: user.provider || 'local'
    });
    
  } catch (error) {
    logger.error('Get user info error', error);
    res.status(401).json({ error: 'Invalid token' });
  }
});

// Batch validation endpoint (for validating multiple tokens)
router.post('/batch', async (req, res) => {
  const span = req.span;
  const { tokens } = req.body;
  
  if (!Array.isArray(tokens)) {
    return res.status(400).json({ error: 'Tokens array required' });
  }
  
  span.setAttributes({
    'auth.action': 'batch_validate',
    'batch.size': tokens.length
  });

  const results = await Promise.all(
    tokens.map(async (token) => {
      try {
        const decoded = jwt.verify(token, JWT_SECRET);
        const sessionData = await tracedRedis.get(`session:${token}`);
        
        if (sessionData) {
          const user = JSON.parse(sessionData);
          return { token, valid: true, userId: user.id };
        }
        
        return { token, valid: false, reason: 'Session not found' };
      } catch (error) {
        return { token, valid: false, reason: error.message };
      }
    })
  );
  
  const validCount = results.filter(r => r.valid).length;
  span.setAttribute('batch.valid_count', validCount);
  metrics.gauge('batch_validation_size', tokens.length);
  metrics.gauge('batch_validation_valid', validCount);
  
  res.json({ results });
});

module.exports = router;
