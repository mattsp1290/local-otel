const { Pool } = require('pg');
const { logger } = require('./utils/logger');
const opentelemetry = require('@opentelemetry/api');

// Create PostgreSQL connection pool
const pool = new Pool({
  connectionString: process.env.DATABASE_URL || 'postgresql://user:password@localhost:5432/auth',
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

// Pool event handlers
pool.on('error', (err) => {
  logger.error('Unexpected database error', err);
});

pool.on('connect', () => {
  logger.info('New database connection established');
});

// Connect to database
async function connectDB() {
  try {
    const client = await pool.connect();
    await client.query('SELECT NOW()');
    client.release();
    logger.info('Database connection test successful');
  } catch (error) {
    logger.error('Database connection failed', error);
    throw error;
  }
}

// Traced database query
async function query(text, params, spanName = 'db.query') {
  const tracer = opentelemetry.trace.getTracer('auth-service');
  const span = tracer.startSpan(spanName, {
    attributes: {
      'db.system': 'postgresql',
      'db.name': 'auth',
      'db.statement': text,
      'db.operation': text.split(' ')[0].toUpperCase()
    }
  });

  const start = Date.now();
  
  try {
    const result = await pool.query(text, params);
    const duration = Date.now() - start;
    
    span.setAttributes({
      'db.rows_affected': result.rowCount,
      'db.duration': duration
    });
    
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

// User-related database operations
const userDb = {
  async createUser(email, username, passwordHash, provider = 'local') {
    const text = `
      INSERT INTO users (email, username, password_hash, provider, created_at)
      VALUES ($1, $2, $3, $4, NOW())
      RETURNING id, email, username, created_at
    `;
    const values = [email, username, passwordHash, provider];
    return query(text, values, 'db.createUser');
  },

  async findUserByEmail(email) {
    const text = 'SELECT * FROM users WHERE email = $1';
    const result = await query(text, [email], 'db.findUserByEmail');
    return result.rows[0];
  },

  async findUserById(id) {
    const text = 'SELECT * FROM users WHERE id = $1';
    const result = await query(text, [id], 'db.findUserById');
    return result.rows[0];
  },

  async findOrCreateOAuthUser(profile, provider) {
    const span = opentelemetry.trace.getActiveSpan();
    span?.setAttribute('oauth.provider', provider);

    const client = await pool.connect();
    try {
      await client.query('BEGIN');

      // Check if user exists
      const checkResult = await client.query(
        'SELECT * FROM users WHERE email = $1',
        [profile.email]
      );

      if (checkResult.rows.length > 0) {
        await client.query('COMMIT');
        return checkResult.rows[0];
      }

      // Create new user
      const insertResult = await client.query(
        `INSERT INTO users (email, username, provider, oauth_id, created_at)
         VALUES ($1, $2, $3, $4, NOW())
         RETURNING *`,
        [profile.email, profile.displayName, provider, profile.id]
      );

      await client.query('COMMIT');
      return insertResult.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }
};

module.exports = { pool, connectDB, query, userDb };
