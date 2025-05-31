const passport = require('passport');
const GoogleStrategy = require('passport-google-oauth20').Strategy;
const { userDb } = require('../db');
const { logger } = require('../utils/logger');
const { metrics } = require('../utils/metrics');
const opentelemetry = require('@opentelemetry/api');

passport.use(new GoogleStrategy({
  clientID: process.env.GOOGLE_CLIENT_ID || 'mock-google-client-id',
  clientSecret: process.env.GOOGLE_CLIENT_SECRET || 'mock-google-client-secret',
  callbackURL: '/api/auth/google/callback',
  passReqToCallback: true
},
async (req, accessToken, refreshToken, profile, done) => {
  const tracer = opentelemetry.trace.getTracer('auth-service');
  const span = tracer.startSpan('oauth.google.callback', {
    attributes: {
      'oauth.provider': 'google',
      'user.email': profile.emails?.[0]?.value
    }
  });

  try {
    logger.info('Google OAuth callback', { 
      profileId: profile.id,
      email: profile.emails?.[0]?.value 
    });

    // Extract user data from Google profile
    const userData = {
      id: profile.id,
      email: profile.emails?.[0]?.value,
      displayName: profile.displayName,
      photo: profile.photos?.[0]?.value
    };

    // Find or create user
    const user = await userDb.findOrCreateOAuthUser(userData, 'google');
    
    span.setAttribute('user.id', user.id);
    span.setAttribute('user.new', !user.existing);
    
    metrics.trackOAuthProvider('google', 'success');
    
    return done(null, user);
  } catch (error) {
    logger.error('Google OAuth error', error);
    span.recordException(error);
    span.setStatus({
      code: opentelemetry.SpanStatusCode.ERROR,
      message: error.message
    });
    metrics.trackOAuthProvider('google', 'error');
    return done(error);
  } finally {
    span.end();
  }
}));

// Serialize user for session
passport.serializeUser((user, done) => {
  done(null, user.id);
});

// Deserialize user from session
passport.deserializeUser(async (id, done) => {
  try {
    const user = await userDb.findUserById(id);
    done(null, user);
  } catch (error) {
    done(error);
  }
});
