package handlers

import (
	"context"
	"database/sql"
	"fmt"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/go-redis/redis/v8"
	"github.com/social-media/feed-service/cache"
	"github.com/social-media/feed-service/models"
	"github.com/social-media/feed-service/telemetry"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/trace"
)

// Handlers contains the handler dependencies
type Handlers struct {
	db    *sql.DB
	redis *redis.Client
}

// ErrorResponse represents an error response
type ErrorResponse struct {
	Error ErrorDetail `json:"error"`
}

// ErrorDetail contains error information
type ErrorDetail struct {
	Code    string `json:"code"`
	Message string `json:"message"`
	TraceID string `json:"trace_id,omitempty"`
}

// NewHandlers creates a new handlers instance
func NewHandlers(db *sql.DB, redis *redis.Client) *Handlers {
	return &Handlers{
		db:    db,
		redis: redis,
	}
}

// extractUserID extracts user ID from X-User-ID header
func extractUserID(c *gin.Context) (string, error) {
	userID := c.GetHeader("X-User-ID")
	if userID == "" {
		return "", fmt.Errorf("missing X-User-ID header")
	}
	return userID, nil
}

// sendError sends a structured error response
func sendError(c *gin.Context, statusCode int, code, message string) {
	span := trace.SpanFromContext(c.Request.Context())
	traceID := ""
	if span.SpanContext().IsValid() {
		traceID = span.SpanContext().TraceID().String()
	}

	c.JSON(statusCode, ErrorResponse{
		Error: ErrorDetail{
			Code:    code,
			Message: message,
			TraceID: traceID,
		},
	})
}

// HealthCheck handles health check requests
func (h *Handlers) HealthCheck(c *gin.Context) {
	tracer := telemetry.GetTracer()
	ctx, span := tracer.Start(c.Request.Context(), "handlers.HealthCheck")
	defer span.End()

	// Check database connection
	if err := h.db.PingContext(ctx); err != nil {
		span.RecordError(err)
		sendError(c, http.StatusServiceUnavailable, "DATABASE_ERROR", "Database connection failed")
		return
	}

	// Check Redis connection
	if err := h.redis.Ping(ctx).Err(); err != nil {
		span.RecordError(err)
		sendError(c, http.StatusServiceUnavailable, "CACHE_ERROR", "Cache connection failed")
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status":    "healthy",
		"service":   "feed-service",
		"timestamp": time.Now().UTC(),
	})
}

// CreatePost handles post creation
func (h *Handlers) CreatePost(c *gin.Context) {
	tracer := telemetry.GetTracer()
	ctx, span := tracer.Start(c.Request.Context(), "handlers.CreatePost")
	defer span.End()

	userID, err := extractUserID(c)
	if err != nil {
		span.RecordError(err)
		sendError(c, http.StatusUnauthorized, "UNAUTHORIZED", "Authentication required")
		return
	}

	span.SetAttributes(attribute.String("user.id", userID))

	var req struct {
		Content string `json:"content" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		span.RecordError(err)
		sendError(c, http.StatusBadRequest, "INVALID_REQUEST", "Invalid request body")
		return
	}

	// Validate content length
	if len(req.Content) == 0 || len(req.Content) > 500 {
		sendError(c, http.StatusBadRequest, "INVALID_CONTENT", "Content must be between 1 and 500 characters")
		return
	}

	post, err := models.CreatePost(h.db, userID, req.Content)
	if err != nil {
		span.RecordError(err)
		sendError(c, http.StatusInternalServerError, "DATABASE_ERROR", "Failed to create post")
		return
	}

	span.SetAttributes(attribute.String("post.id", post.ID))

	// Invalidate user's timeline cache
	go func() {
		if err := cache.InvalidateTimeline(h.redis, userID); err != nil {
			span.RecordError(err)
		}
	}()

	c.JSON(http.StatusCreated, post)
}

// GetPost handles retrieving a single post
func (h *Handlers) GetPost(c *gin.Context) {
	tracer := telemetry.GetTracer()
	ctx, span := tracer.Start(c.Request.Context(), "handlers.GetPost")
	defer span.End()

	postID := c.Param("id")
	span.SetAttributes(attribute.String("post.id", postID))

	// Try cache first
	cachedPost, err := cache.GetPost(h.redis, postID)
	if err != nil {
		span.RecordError(err)
	}

	if cachedPost != nil {
		span.SetAttributes(attribute.Bool("cache.hit", true))
		c.JSON(http.StatusOK, cachedPost)
		return
	}

	span.SetAttributes(attribute.Bool("cache.hit", false))

	// Get from database
	post, err := models.GetPost(h.db, postID)
	if err != nil {
		span.RecordError(err)
		sendError(c, http.StatusInternalServerError, "DATABASE_ERROR", "Failed to retrieve post")
		return
	}

	if post == nil {
		sendError(c, http.StatusNotFound, "POST_NOT_FOUND", "The requested post does not exist")
		return
	}

	// Cache the post
	postMap := map[string]interface{}{
		"id":            post.ID,
		"user_id":       post.UserID,
		"content":       post.Content,
		"created_at":    post.CreatedAt,
		"updated_at":    post.UpdatedAt,
		"like_count":    post.LikeCount,
		"comment_count": post.CommentCount,
	}

	go func() {
		if err := cache.SetPost(h.redis, postID, postMap); err != nil {
			span.RecordError(err)
		}
	}()

	c.JSON(http.StatusOK, post)
}

// DeletePost handles post deletion
func (h *Handlers) DeletePost(c *gin.Context) {
	tracer := telemetry.GetTracer()
	ctx, span := tracer.Start(c.Request.Context(), "handlers.DeletePost")
	defer span.End()

	userID, err := extractUserID(c)
	if err != nil {
		span.RecordError(err)
		sendError(c, http.StatusUnauthorized, "UNAUTHORIZED", "Authentication required")
		return
	}

	postID := c.Param("id")
	span.SetAttributes(
		attribute.String("user.id", userID),
		attribute.String("post.id", postID),
	)

	err = models.DeletePost(h.db, postID, userID)
	if err != nil {
		span.RecordError(err)
		if err.Error() == "post not found or unauthorized" {
			sendError(c, http.StatusNotFound, "POST_NOT_FOUND", "Post not found or you don't have permission to delete it")
		} else {
			sendError(c, http.StatusInternalServerError, "DATABASE_ERROR", "Failed to delete post")
		}
		return
	}

	// Invalidate caches
	go func() {
		// Delete from post cache
		key := fmt.Sprintf("post:%s", postID)
		h.redis.Del(context.Background(), key)

		// Invalidate user timeline
		if err := cache.InvalidateTimeline(h.redis, userID); err != nil {
			span.RecordError(err)
		}
	}()

	c.JSON(http.StatusNoContent, nil)
}

// GetTimeline handles timeline generation
func (h *Handlers) GetTimeline(c *gin.Context) {
	tracer := telemetry.GetTracer()
	ctx, span := tracer.Start(c.Request.Context(), "handlers.GetTimeline")
	defer span.End()

	userID := c.Param("user_id")
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	if page < 1 {
		page = 1
	}

	span.SetAttributes(
		attribute.String("user.id", userID),
		attribute.Int("page", page),
	)

	limit := 20
	offset := (page - 1) * limit

	// Try cache first
	cachedPostIDs, err := cache.GetTimeline(h.redis, userID, page)
	if err != nil {
		span.RecordError(err)
	}

	if cachedPostIDs != nil {
		span.SetAttributes(attribute.Bool("cache.hit", true))
		// TODO: Fetch full post details from cache/DB
		c.JSON(http.StatusOK, gin.H{
			"posts": cachedPostIDs,
			"page":  page,
		})
		return
	}

	span.SetAttributes(attribute.Bool("cache.hit", false))

	// Fetch followed users from User Profile Service
	followedUsers, err := h.getFollowedUsers(ctx, userID)
	if err != nil {
		span.RecordError(err)
		sendError(c, http.StatusInternalServerError, "SERVICE_ERROR", "Failed to fetch user relationships")
		return
	}

	// Get timeline posts
	posts, err := models.GetTimelinePosts(h.db, userID, followedUsers, limit, offset)
	if err != nil {
		span.RecordError(err)
		sendError(c, http.StatusInternalServerError, "DATABASE_ERROR", "Failed to generate timeline")
		return
	}

	// Cache post IDs
	if len(posts) > 0 {
		postIDs := make([]string, len(posts))
		for i, post := range posts {
			postIDs[i] = post.ID
		}
		go func() {
			if err := cache.SetTimeline(h.redis, userID, page, postIDs); err != nil {
				span.RecordError(err)
			}
		}()
	}

	c.JSON(http.StatusOK, gin.H{
		"posts": posts,
		"page":  page,
		"count": len(posts),
	})
}

// GetUserPosts handles fetching posts by a specific user
func (h *Handlers) GetUserPosts(c *gin.Context) {
	tracer := telemetry.GetTracer()
	ctx, span := tracer.Start(c.Request.Context(), "handlers.GetUserPosts")
	defer span.End()

	userID := c.Param("user_id")
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	if page < 1 {
		page = 1
	}

	span.SetAttributes(
		attribute.String("user.id", userID),
		attribute.Int("page", page),
	)

	limit := 20
	offset := (page - 1) * limit

	posts, err := models.GetUserPosts(h.db, userID, limit, offset)
	if err != nil {
		span.RecordError(err)
		sendError(c, http.StatusInternalServerError, "DATABASE_ERROR", "Failed to retrieve user posts")
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"posts": posts,
		"page":  page,
		"count": len(posts),
	})
}

// LikePost handles liking a post
func (h *Handlers) LikePost(c *gin.Context) {
	tracer := telemetry.GetTracer()
	ctx, span := tracer.Start(c.Request.Context(), "handlers.LikePost")
	defer span.End()

	userID, err := extractUserID(c)
	if err != nil {
		span.RecordError(err)
		sendError(c, http.StatusUnauthorized, "UNAUTHORIZED", "Authentication required")
		return
	}

	postID := c.Param("id")
	span.SetAttributes(
		attribute.String("user.id", userID),
		attribute.String("post.id", postID),
	)

	err = models.LikePost(h.db, postID, userID)
	if err != nil {
		span.RecordError(err)
		sendError(c, http.StatusInternalServerError, "DATABASE_ERROR", "Failed to like post")
		return
	}

	// Invalidate post cache
	go func() {
		key := fmt.Sprintf("post:%s", postID)
		h.redis.Del(context.Background(), key)
	}()

	c.JSON(http.StatusOK, gin.H{
		"message": "Post liked successfully",
	})
}

// UnlikePost handles unliking a post
func (h *Handlers) UnlikePost(c *gin.Context) {
	tracer := telemetry.GetTracer()
	ctx, span := tracer.Start(c.Request.Context(), "handlers.UnlikePost")
	defer span.End()

	userID, err := extractUserID(c)
	if err != nil {
		span.RecordError(err)
		sendError(c, http.StatusUnauthorized, "UNAUTHORIZED", "Authentication required")
		return
	}

	postID := c.Param("id")
	span.SetAttributes(
		attribute.String("user.id", userID),
		attribute.String("post.id", postID),
	)

	err = models.UnlikePost(h.db, postID, userID)
	if err != nil {
		span.RecordError(err)
		sendError(c, http.StatusInternalServerError, "DATABASE_ERROR", "Failed to unlike post")
		return
	}

	// Invalidate post cache
	go func() {
		key := fmt.Sprintf("post:%s", postID)
		h.redis.Del(context.Background(), key)
	}()

	c.JSON(http.StatusOK, gin.H{
		"message": "Post unliked successfully",
	})
}

// AddComment handles adding a comment to a post
func (h *Handlers) AddComment(c *gin.Context) {
	tracer := telemetry.GetTracer()
	ctx, span := tracer.Start(c.Request.Context(), "handlers.AddComment")
	defer span.End()

	userID, err := extractUserID(c)
	if err != nil {
		span.RecordError(err)
		sendError(c, http.StatusUnauthorized, "UNAUTHORIZED", "Authentication required")
		return
	}

	postID := c.Param("id")
	span.SetAttributes(
		attribute.String("user.id", userID),
		attribute.String("post.id", postID),
	)

	var req struct {
		Content string `json:"content" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		span.RecordError(err)
		sendError(c, http.StatusBadRequest, "INVALID_REQUEST", "Invalid request body")
		return
	}

	// Validate comment length
	if len(req.Content) == 0 || len(req.Content) > 200 {
		sendError(c, http.StatusBadRequest, "INVALID_CONTENT", "Comment must be between 1 and 200 characters")
		return
	}

	comment, err := models.CreateComment(h.db, postID, userID, req.Content)
	if err != nil {
		span.RecordError(err)
		sendError(c, http.StatusInternalServerError, "DATABASE_ERROR", "Failed to add comment")
		return
	}

	// Invalidate post cache
	go func() {
		key := fmt.Sprintf("post:%s", postID)
		h.redis.Del(context.Background(), key)
	}()

	c.JSON(http.StatusCreated, comment)
}

// GetComments handles retrieving comments for a post
func (h *Handlers) GetComments(c *gin.Context) {
	tracer := telemetry.GetTracer()
	ctx, span := tracer.Start(c.Request.Context(), "handlers.GetComments")
	defer span.End()

	postID := c.Param("id")
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	if page < 1 {
		page = 1
	}

	span.SetAttributes(
		attribute.String("post.id", postID),
		attribute.Int("page", page),
	)

	limit := 20
	offset := (page - 1) * limit

	comments, err := models.GetComments(h.db, postID, limit, offset)
	if err != nil {
		span.RecordError(err)
		sendError(c, http.StatusInternalServerError, "DATABASE_ERROR", "Failed to retrieve comments")
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"comments": comments,
		"page":     page,
		"count":    len(comments),
	})
}

// getFollowedUsers fetches the list of users that the given user follows
func (h *Handlers) getFollowedUsers(ctx context.Context, userID string) ([]string, error) {
	tracer := telemetry.GetTracer()
	ctx, span := tracer.Start(ctx, "handlers.getFollowedUsers")
	defer span.End()

	// For simplicity, return a mock list
	// In production, this would call the User Profile Service
	// TODO: Implement actual HTTP call to User Profile Service

	// Mock implementation
	mockFollowed := []string{
		"user123",
		"user456",
		"user789",
	}

	span.SetAttributes(
		attribute.String("user.id", userID),
		attribute.Int("followed.count", len(mockFollowed)),
	)

	return mockFollowed, nil
}
