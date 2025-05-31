const express = require('express');
const passport = require('passport');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcrypt');
const { userDb } = require('../db');
const { tracedRedis } = require('../cache/redis');
const { logger } = require('../utils/logger');
const { metrics } = require('../utils/metrics');
const opentelemetry = require('@opentelemetry/api');

const router = express.Router();
const JWT_SECRET = process.env.JWT_SECRET || 'default-secret-change-in-production';

// Helper to generate JWT
function generateToken(user) {
  return jwt.sign(
    { 
      id: user.id, 
      email: user.email,
      username: user.username 
    },
    JWT_SECRET,
    { expiresIn: '24h' }
  );
}

// Local registration
router.post('/register', async (req, res) => {
  const startTime = Date.now();
  const span = req.span;
  
  try {
    const { email, username, password } = req.body;
    
    span.setAttributes({
      'auth.action': 'register',
      'user.email': email
    });

    // Check if user exists
    const existingUser = await userDb.findUserByEmail(email);
    if (existingUser) {
      metrics.trackAuthEvent('register', false);
      return res.status(400).json({ error: 'User already exists' });
    }

    // Hash password
    const passwordHash = await bcrypt.hash(password, 10);
    
    // Create user
    const result = await userDb.createUser(email, username, passwordHash);
    const user = result.rows[0];

    // Generate token
    const token = generateToken(user);
    
    // Store session in Redis
    await tracedRedis.set(
      `session:${token}`,
      JSON.stringify(user),
      { EX: 86400 } // 24 hours
    );

    span.setAttribute('user.id', user.id);
    metrics.trackAuthEvent('register', true);
    metrics.trackRequestDuration('/register', 'POST', 201, Date.now() - startTime);

    logger.info('User registered successfully', { userId: user.id });

    res.status(201).json({
      message: 'Registration successful',
      token,
      user: {
        id: user.id,
        email: user.email,
        username: user.username
      }
    });
  } catch (error) {
    logger.error('Registration error', error);
    metrics.trackAuthEvent('register', false);
    metrics.trackRequestDuration('/register', 'POST', 500, Date.now() - startTime);
    res.status(500).json({ error: 'Registration failed' });
  }
});

// Local login
router.post('/login', async (req, res) => {
  const startTime = Date.now();
  const span = req.span;
  
  try {
    const { email, password } = req.body;
    
    span.setAttributes({
      'auth.action': 'login',
      'user.email': email
    });

    // Find user
    const user = await userDb.findUserByEmail(email);
    if (!user) {
      metrics.trackAuthEvent('login', false);
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    // Verify password
    const validPassword = await bcrypt.compare(password, user.password_hash);
    if (!validPassword) {
      metrics.trackAuthEvent('login', false);
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    // Generate token
    const token = generateToken(user);
    
    // Store session in Redis
    await tracedRedis.set(
      `session:${token}`,
      JSON.stringify(user),
      { EX: 86400 } // 24 hours
    );

    span.setAttribute('user.id', user.id);
    metrics.trackAuthEvent('login', true);
    metrics.trackRequestDuration('/login', 'POST', 200, Date.now() - startTime);

    logger.info('User logged in successfully', { userId: user.id });

    res.json({
      message: 'Login successful',
      token,
      user: {
        id: user.id,
        email: user.email,
        username: user.username
      }
    });
  } catch (error) {
    logger.error('Login error', error);
    metrics.trackAuthEvent('login', false);
    metrics.trackRequestDuration('/login', 'POST', 500, Date.now() - startTime);
    res.status(500).json({ error: 'Login failed' });
  }
});

// OAuth routes
router.get('/google', 
  passport.authenticate('google', { scope: ['profile', 'email'] })
);

router.get('/google/callback',
  passport.authenticate('google', { session: false }),
  async (req, res) => {
    const span = req.span;
    span.setAttributes({
      'auth.action': 'oauth_callback',
      'oauth.provider': 'google'
    });

    try {
      const user = req.user;
      const token = generateToken(user);
      
      // Store session
      await tracedRedis.set(
        `session:${token}`,
        JSON.stringify(user),
        { EX: 86400 }
      );

      metrics.trackOAuthProvider('google', 'login_complete');
      
      // Redirect to frontend with token
      res.redirect(`${process.env.FRONTEND_URL || 'http://localhost:3000'}/auth/callback?token=${token}`);
    } catch (error) {
      logger.error('OAuth callback error', error);
      res.redirect(`${process.env.FRONTEND_URL || 'http://localhost:3000'}/auth/error`);
    }
  }
);

router.get('/github',
  passport.authenticate('github', { scope: ['user:email'] })
);

router.get('/github/callback',
  passport.authenticate('github', { session: false }),
  async (req, res) => {
    const span = req.span;
    span.setAttributes({
      'auth.action': 'oauth_callback',
      'oauth.provider': 'github'
    });

    try {
      const user = req.user;
      const token = generateToken(user);
      
      // Store session
      await tracedRedis.set(
        `session:${token}`,
        JSON.stringify(user),
        { EX: 86400 }
      );

      metrics.trackOAuthProvider('github', 'login_complete');
      
      // Redirect to frontend with token
      res.redirect(`${process.env.FRONTEND_URL || 'http://localhost:3000'}/auth/callback?token=${token}`);
    } catch (error) {
      logger.error('OAuth callback error', error);
      res.redirect(`${process.env.FRONTEND_URL || 'http://localhost:3000'}/auth/error`);
    }
  }
);

// Logout
router.post('/logout', async (req, res) => {
  const span = req.span;
  const token = req.headers.authorization?.replace('Bearer ', '');
  
  if (token) {
    span.setAttribute('auth.action', 'logout');
    await tracedRedis.del(`session:${token}`);
    metrics.trackAuthEvent('logout', true);
  }
  
  res.json({ message: 'Logged out successfully' });
});

// Refresh token
router.post('/refresh', async (req, res) => {
  const span = req.span;
  const oldToken = req.headers.authorization?.replace('Bearer ', '');
  
  try {
    span.setAttribute('auth.action', 'refresh');
    
    // Verify old token
    const decoded = jwt.verify(oldToken, JWT_SECRET);
    
    // Get user from cache or database
    let userData = await tracedRedis.get(`session:${oldToken}`);
    let user;
    
    if (userData) {
      user = JSON.parse(userData);
      metrics.trackCacheOperation('session_get', true);
    } else {
      user = await userDb.findUserById(decoded.id);
      metrics.trackCacheOperation('session_get', false);
    }
    
    if (!user) {
      return res.status(401).json({ error: 'User not found' });
    }
    
    // Generate new token
    const newToken = generateToken(user);
    
    // Store new session and remove old one
    await tracedRedis.set(
      `session:${newToken}`,
      JSON.stringify(user),
      { EX: 86400 }
    );
    await tracedRedis.del(`session:${oldToken}`);
    
    metrics.trackTokenOperation('refresh', true);
    
    res.json({
      message: 'Token refreshed',
      token: newToken
    });
  } catch (error) {
    logger.error('Token refresh error', error);
    metrics.trackTokenOperation('refresh', false);
    res.status(401).json({ error: 'Invalid token' });
  }
});

module.exports = router;
