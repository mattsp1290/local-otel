const passport = require('passport');
const GitHubStrategy = require('passport-github2').Strategy;
const { userDb } = require('../db');
const { logger } = require('../utils/logger');
const { metrics } = require('../utils/metrics');
const opentelemetry = require('@opentelemetry/api');

passport.use(new GitHubStrategy({
  clientID: process.env.GITHUB_CLIENT_ID || 'mock-github-client-id',
  clientSecret: process.env.GITHUB_CLIENT_SECRET || 'mock-github-client-secret',
  callbackURL: '/api/auth/github/callback',
  passReqToCallback: true
},
async (req, accessToken, refreshToken, profile, done) => {
  const tracer = opentelemetry.trace.getTracer('auth-service');
  const span = tracer.startSpan('oauth.github.callback', {
    attributes: {
      'oauth.provider': 'github',
      'user.email': profile.emails?.[0]?.value
    }
  });

  try {
    logger.info('GitHub OAuth callback', { 
      profileId: profile.id,
      username: profile.username 
    });

    // Extract user data from GitHub profile
    const userData = {
      id: profile.id,
      email: profile.emails?.[0]?.value || `${profile.username}@github.local`,
      displayName: profile.displayName || profile.username,
      photo: profile.photos?.[0]?.value
    };

    // Find or create user
    const user = await userDb.findOrCreateOAuthUser(userData, 'github');
    
    span.setAttribute('user.id', user.id);
    span.setAttribute('user.new', !user.existing);
    
    metrics.trackOAuthProvider('github', 'success');
    
    return done(null, user);
  } catch (error) {
    logger.error('GitHub OAuth error', error);
    span.recordException(error);
    span.setStatus({
      code: opentelemetry.SpanStatusCode.ERROR,
      message: error.message
    });
    metrics.trackOAuthProvider('github', 'error');
    return done(error);
  } finally {
    span.end();
  }
}));
