package models

import (
	"database/sql"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/google/uuid"
	_ "github.com/lib/pq"
)

// Post represents a social media post
type Post struct {
	ID           string    `json:"id"`
	UserID       string    `json:"user_id"`
	Content      string    `json:"content"`
	CreatedAt    time.Time `json:"created_at"`
	UpdatedAt    time.Time `json:"updated_at"`
	LikeCount    int       `json:"like_count"`
	CommentCount int       `json:"comment_count"`
}

// Like represents a like on a post
type Like struct {
	PostID    string    `json:"post_id"`
	UserID    string    `json:"user_id"`
	CreatedAt time.Time `json:"created_at"`
}

// Comment represents a comment on a post
type Comment struct {
	ID        string    `json:"id"`
	PostID    string    `json:"post_id"`
	UserID    string    `json:"user_id"`
	Content   string    `json:"content"`
	CreatedAt time.Time `json:"created_at"`
}

// UserInteraction tracks interactions between users for timeline ranking
type UserInteraction struct {
	UserID           string    `json:"user_id"`
	TargetUserID     string    `json:"target_user_id"`
	InteractionCount int       `json:"interaction_count"`
	LastInteraction  time.Time `json:"last_interaction"`
}

// InitDB initializes the database connection
func InitDB() (*sql.DB, error) {
	dbURL := os.Getenv("DATABASE_URL")
	if dbURL == "" {
		dbURL = "postgres://feeduser:feedpass@localhost:5432/feeddb?sslmode=disable"
	}

	db, err := sql.Open("postgres", dbURL)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	// Test connection
	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	// Set connection pool settings
	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(5 * time.Minute)

	log.Println("Connected to PostgreSQL database")
	return db, nil
}

// RunMigrations creates the necessary tables
func RunMigrations(db *sql.DB) error {
	migrations := []string{
		`CREATE EXTENSION IF NOT EXISTS "uuid-ossp"`,
		`CREATE TABLE IF NOT EXISTS posts (
			id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
			user_id VARCHAR(255) NOT NULL,
			content TEXT NOT NULL,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			like_count INTEGER DEFAULT 0,
			comment_count INTEGER DEFAULT 0
		)`,
		`CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id)`,
		`CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at DESC)`,
		`CREATE TABLE IF NOT EXISTS likes (
			post_id UUID NOT NULL,
			user_id VARCHAR(255) NOT NULL,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			PRIMARY KEY (post_id, user_id),
			FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
		)`,
		`CREATE TABLE IF NOT EXISTS comments (
			id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
			post_id UUID NOT NULL,
			user_id VARCHAR(255) NOT NULL,
			content TEXT NOT NULL,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
		)`,
		`CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id)`,
		`CREATE TABLE IF NOT EXISTS user_interactions (
			user_id VARCHAR(255) NOT NULL,
			target_user_id VARCHAR(255) NOT NULL,
			interaction_count INTEGER DEFAULT 1,
			last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			PRIMARY KEY (user_id, target_user_id)
		)`,
	}

	for _, migration := range migrations {
		if _, err := db.Exec(migration); err != nil {
			return fmt.Errorf("migration failed: %w", err)
		}
	}

	log.Println("Database migrations completed")
	return nil
}

// CreatePost creates a new post
func CreatePost(db *sql.DB, userID, content string) (*Post, error) {
	post := &Post{
		ID:        uuid.New().String(),
		UserID:    userID,
		Content:   content,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}

	query := `
		INSERT INTO posts (id, user_id, content, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5)
		RETURNING like_count, comment_count
	`

	err := db.QueryRow(query, post.ID, post.UserID, post.Content, post.CreatedAt, post.UpdatedAt).
		Scan(&post.LikeCount, &post.CommentCount)
	if err != nil {
		return nil, fmt.Errorf("failed to create post: %w", err)
	}

	return post, nil
}

// GetPost retrieves a post by ID
func GetPost(db *sql.DB, postID string) (*Post, error) {
	post := &Post{}
	query := `
		SELECT id, user_id, content, created_at, updated_at, like_count, comment_count
		FROM posts
		WHERE id = $1
	`

	err := db.QueryRow(query, postID).Scan(
		&post.ID, &post.UserID, &post.Content,
		&post.CreatedAt, &post.UpdatedAt,
		&post.LikeCount, &post.CommentCount,
	)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("failed to get post: %w", err)
	}

	return post, nil
}

// DeletePost deletes a post
func DeletePost(db *sql.DB, postID, userID string) error {
	query := `DELETE FROM posts WHERE id = $1 AND user_id = $2`
	result, err := db.Exec(query, postID, userID)
	if err != nil {
		return fmt.Errorf("failed to delete post: %w", err)
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("failed to get rows affected: %w", err)
	}

	if rowsAffected == 0 {
		return fmt.Errorf("post not found or unauthorized")
	}

	return nil
}

// GetUserPosts retrieves posts by a specific user
func GetUserPosts(db *sql.DB, userID string, limit, offset int) ([]*Post, error) {
	query := `
		SELECT id, user_id, content, created_at, updated_at, like_count, comment_count
		FROM posts
		WHERE user_id = $1
		ORDER BY created_at DESC
		LIMIT $2 OFFSET $3
	`

	rows, err := db.Query(query, userID, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("failed to get user posts: %w", err)
	}
	defer rows.Close()

	var posts []*Post
	for rows.Next() {
		post := &Post{}
		err := rows.Scan(
			&post.ID, &post.UserID, &post.Content,
			&post.CreatedAt, &post.UpdatedAt,
			&post.LikeCount, &post.CommentCount,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan post: %w", err)
		}
		posts = append(posts, post)
	}

	return posts, nil
}

// GetTimelinePosts retrieves posts for a user's timeline with interaction weighting
func GetTimelinePosts(db *sql.DB, userID string, followedUsers []string, limit, offset int) ([]*Post, error) {
	if len(followedUsers) == 0 {
		return []*Post{}, nil
	}

	// Build the query with interaction weighting
	query := `
		WITH interaction_weights AS (
			SELECT target_user_id, interaction_count
			FROM user_interactions
			WHERE user_id = $1
		)
		SELECT 
			p.id, p.user_id, p.content, p.created_at, p.updated_at, 
			p.like_count, p.comment_count,
			EXTRACT(EPOCH FROM (NOW() - p.created_at))/3600 as hours_ago,
			COALESCE(iw.interaction_count, 0) as interaction_weight
		FROM posts p
		LEFT JOIN interaction_weights iw ON p.user_id = iw.target_user_id
		WHERE p.user_id = ANY($2)
		ORDER BY 
			(1.0 / (EXTRACT(EPOCH FROM (NOW() - p.created_at))/3600 + 1)) * 
			(1 + COALESCE(iw.interaction_count, 0) * 0.1) DESC,
			p.created_at DESC
		LIMIT $3 OFFSET $4
	`

	rows, err := db.Query(query, userID, followedUsers, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("failed to get timeline posts: %w", err)
	}
	defer rows.Close()

	var posts []*Post
	for rows.Next() {
		post := &Post{}
		var hoursAgo float64
		var interactionWeight int
		err := rows.Scan(
			&post.ID, &post.UserID, &post.Content,
			&post.CreatedAt, &post.UpdatedAt,
			&post.LikeCount, &post.CommentCount,
			&hoursAgo, &interactionWeight,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan timeline post: %w", err)
		}
		posts = append(posts, post)
	}

	return posts, nil
}

// LikePost adds a like to a post
func LikePost(db *sql.DB, postID, userID string) error {
	tx, err := db.Begin()
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %w", err)
	}
	defer tx.Rollback()

	// Insert like
	_, err = tx.Exec(`
		INSERT INTO likes (post_id, user_id) 
		VALUES ($1, $2) 
		ON CONFLICT DO NOTHING
	`, postID, userID)
	if err != nil {
		return fmt.Errorf("failed to insert like: %w", err)
	}

	// Update like count
	_, err = tx.Exec(`
		UPDATE posts 
		SET like_count = (SELECT COUNT(*) FROM likes WHERE post_id = $1)
		WHERE id = $1
	`, postID)
	if err != nil {
		return fmt.Errorf("failed to update like count: %w", err)
	}

	// Update user interaction
	_, err = tx.Exec(`
		INSERT INTO user_interactions (user_id, target_user_id, interaction_count, last_interaction)
		SELECT $1, p.user_id, 1, NOW()
		FROM posts p
		WHERE p.id = $2
		ON CONFLICT (user_id, target_user_id) 
		DO UPDATE SET 
			interaction_count = user_interactions.interaction_count + 1,
			last_interaction = NOW()
	`, userID, postID)
	if err != nil {
		return fmt.Errorf("failed to update user interaction: %w", err)
	}

	return tx.Commit()
}

// UnlikePost removes a like from a post
func UnlikePost(db *sql.DB, postID, userID string) error {
	tx, err := db.Begin()
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %w", err)
	}
	defer tx.Rollback()

	// Delete like
	_, err = tx.Exec(`DELETE FROM likes WHERE post_id = $1 AND user_id = $2`, postID, userID)
	if err != nil {
		return fmt.Errorf("failed to delete like: %w", err)
	}

	// Update like count
	_, err = tx.Exec(`
		UPDATE posts 
		SET like_count = (SELECT COUNT(*) FROM likes WHERE post_id = $1)
		WHERE id = $1
	`, postID)
	if err != nil {
		return fmt.Errorf("failed to update like count: %w", err)
	}

	return tx.Commit()
}

// CreateComment adds a comment to a post
func CreateComment(db *sql.DB, postID, userID, content string) (*Comment, error) {
	tx, err := db.Begin()
	if err != nil {
		return nil, fmt.Errorf("failed to begin transaction: %w", err)
	}
	defer tx.Rollback()

	comment := &Comment{
		ID:        uuid.New().String(),
		PostID:    postID,
		UserID:    userID,
		Content:   content,
		CreatedAt: time.Now(),
	}

	// Insert comment
	_, err = tx.Exec(`
		INSERT INTO comments (id, post_id, user_id, content, created_at)
		VALUES ($1, $2, $3, $4, $5)
	`, comment.ID, comment.PostID, comment.UserID, comment.Content, comment.CreatedAt)
	if err != nil {
		return nil, fmt.Errorf("failed to insert comment: %w", err)
	}

	// Update comment count
	_, err = tx.Exec(`
		UPDATE posts 
		SET comment_count = (SELECT COUNT(*) FROM comments WHERE post_id = $1)
		WHERE id = $1
	`, postID)
	if err != nil {
		return nil, fmt.Errorf("failed to update comment count: %w", err)
	}

	// Update user interaction
	_, err = tx.Exec(`
		INSERT INTO user_interactions (user_id, target_user_id, interaction_count, last_interaction)
		SELECT $1, p.user_id, 1, NOW()
		FROM posts p
		WHERE p.id = $2
		ON CONFLICT (user_id, target_user_id) 
		DO UPDATE SET 
			interaction_count = user_interactions.interaction_count + 1,
			last_interaction = NOW()
	`, userID, postID)
	if err != nil {
		return nil, fmt.Errorf("failed to update user interaction: %w", err)
	}

	if err := tx.Commit(); err != nil {
		return nil, fmt.Errorf("failed to commit transaction: %w", err)
	}

	return comment, nil
}

// GetComments retrieves comments for a post
func GetComments(db *sql.DB, postID string, limit, offset int) ([]*Comment, error) {
	query := `
		SELECT id, post_id, user_id, content, created_at
		FROM comments
		WHERE post_id = $1
		ORDER BY created_at DESC
		LIMIT $2 OFFSET $3
	`

	rows, err := db.Query(query, postID, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("failed to get comments: %w", err)
	}
	defer rows.Close()

	var comments []*Comment
	for rows.Next() {
		comment := &Comment{}
		err := rows.Scan(
			&comment.ID, &comment.PostID, &comment.UserID,
			&comment.Content, &comment.CreatedAt,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan comment: %w", err)
		}
		comments = append(comments, comment)
	}

	return comments, nil
}
