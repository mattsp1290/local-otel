const StatsD = require('node-statsd');

// Initialize StatsD client
const statsClient = new StatsD({
  host: process.env.STATSD_HOST || 'localhost',
  port: process.env.STATSD_PORT || 8125,
  prefix: 'auth_service.',
  global_tags: [`env:${process.env.NODE_ENV || 'development'}`],
});

// Handle StatsD errors gracefully
statsClient.socket.on('error', (error) => {
  console.error('StatsD error:', error);
});

// Helper functions for common metrics
const metrics = {
  // Track API endpoint timings
  trackRequestDuration: (endpoint, method, statusCode, duration) => {
    statsClient.timing('request_duration', duration, [
      `endpoint:${endpoint}`,
      `method:${method}`,
      `status:${statusCode}`
    ]);
  },

  // Track authentication events
  trackAuthEvent: (event, success = true) => {
    statsClient.increment('auth_events', 1, [
      `event:${event}`,
      `success:${success}`
    ]);
  },

  // Track OAuth provider usage
  trackOAuthProvider: (provider, event) => {
    statsClient.increment('oauth_usage', 1, [
      `provider:${provider}`,
      `event:${event}`
    ]);
  },

  // Track token operations
  trackTokenOperation: (operation, success = true) => {
    statsClient.increment('token_operations', 1, [
      `operation:${operation}`,
      `success:${success}`
    ]);
  },

  // Track cache operations
  trackCacheOperation: (operation, hit = true) => {
    statsClient.increment('cache_operations', 1, [
      `operation:${operation}`,
      `hit:${hit}`
    ]);
  },

  // Track rate limit hits
  trackRateLimit: (endpoint) => {
    statsClient.increment('rate_limit_hits', 1, [`endpoint:${endpoint}`]);
  },

  // Track active sessions gauge
  setActiveSessions: (count) => {
    statsClient.gauge('active_sessions', count);
  },

  // Track database query duration
  trackDbQuery: (query, duration) => {
    statsClient.timing('db_query_duration', duration, [`query:${query}`]);
  }
};

module.exports = { statsClient, metrics };
