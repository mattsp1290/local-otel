package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/social-media/feed-service/cache"
	"github.com/social-media/feed-service/handlers"
	"github.com/social-media/feed-service/models"
	"github.com/social-media/feed-service/telemetry"
)

func main() {
	// Initialize telemetry
	cleanup := telemetry.InitTelemetry()
	defer cleanup()

	// Initialize metrics
	telemetry.InitMetrics()

	// Initialize database
	db, err := models.InitDB()
	if err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer db.Close()

	// Run migrations
	if err := models.RunMigrations(db); err != nil {
		log.Fatalf("Failed to run migrations: %v", err)
	}

	// Initialize Redis cache
	redisClient := cache.InitRedis()
	defer redisClient.Close()

	// Create Gin router
	gin.SetMode(gin.ReleaseMode)
	router := gin.New()

	// Add middleware
	router.Use(gin.Recovery())
	router.Use(telemetry.TracingMiddleware())
	router.Use(telemetry.LoggingMiddleware())

	// Create handlers
	h := handlers.NewHandlers(db, redisClient)

	// Health check
	router.GET("/health", h.HealthCheck)

	// API routes
	api := router.Group("/api")
	{
		// Post routes
		api.POST("/posts", h.CreatePost)
		api.GET("/posts/:id", h.GetPost)
		api.DELETE("/posts/:id", h.DeletePost)

		// Timeline routes
		api.GET("/timeline/:user_id", h.GetTimeline)
		api.GET("/posts/user/:user_id", h.GetUserPosts)

		// Interaction routes
		api.POST("/posts/:id/like", h.LikePost)
		api.DELETE("/posts/:id/like", h.UnlikePost)
		api.POST("/posts/:id/comment", h.AddComment)
		api.GET("/posts/:id/comments", h.GetComments)
	}

	// Start server
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	srv := &http.Server{
		Addr:    ":" + port,
		Handler: router,
	}

	// Graceful shutdown
	go func() {
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("listen: %s\n", err)
		}
	}()

	log.Printf("Feed service started on port %s", port)
	telemetry.RecordServiceStart()

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("Shutting down server...")

	// Graceful shutdown with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		log.Fatal("Server forced to shutdown:", err)
	}

	log.Println("Server exiting")
}
