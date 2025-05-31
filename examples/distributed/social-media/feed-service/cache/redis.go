package cache

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/go-redis/redis/v8"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
)

var ctx = context.Background()

// InitRedis initializes Redis client
func InitRedis() *redis.Client {
	redisURL := os.Getenv("REDIS_URL")
	if redisURL == "" {
		redisURL = "redis://localhost:6379"
	}

	opt, err := redis.ParseURL(redisURL)
	if err != nil {
		log.Fatalf("Failed to parse Redis URL: %v", err)
	}

	client := redis.NewClient(opt)

	// Test connection
	_, err = client.Ping(ctx).Result()
	if err != nil {
		log.Fatalf("Failed to connect to Redis: %v", err)
	}

	log.Println("Connected to Redis")
	return client
}

// GetTimeline gets cached timeline
func GetTimeline(client *redis.Client, userID string, page int) ([]string, error) {
	tracer := otel.Tracer("feed-service")
	ctx, span := tracer.Start(ctx, "cache.GetTimeline")
	defer span.End()

	span.SetAttributes(
		attribute.String("cache.operation", "get_timeline"),
		attribute.String("user.id", userID),
		attribute.Int("page", page),
	)

	key := fmt.Sprintf("timeline:%s:%d", userID, page)
	val, err := client.Get(ctx, key).Result()

	if err == redis.Nil {
		span.SetAttributes(attribute.Bool("cache.hit", false))
		return nil, nil
	} else if err != nil {
		span.RecordError(err)
		return nil, err
	}

	span.SetAttributes(attribute.Bool("cache.hit", true))

	var postIDs []string
	err = json.Unmarshal([]byte(val), &postIDs)
	if err != nil {
		span.RecordError(err)
		return nil, err
	}

	return postIDs, nil
}

// SetTimeline caches timeline
func SetTimeline(client *redis.Client, userID string, page int, postIDs []string) error {
	tracer := otel.Tracer("feed-service")
	ctx, span := tracer.Start(ctx, "cache.SetTimeline")
	defer span.End()

	span.SetAttributes(
		attribute.String("cache.operation", "set_timeline"),
		attribute.String("user.id", userID),
		attribute.Int("page", page),
		attribute.Int("post.count", len(postIDs)),
	)

	key := fmt.Sprintf("timeline:%s:%d", userID, page)
	data, err := json.Marshal(postIDs)
	if err != nil {
		span.RecordError(err)
		return err
	}

	// Cache for 5 minutes
	err = client.Set(ctx, key, data, 5*time.Minute).Err()
	if err != nil {
		span.RecordError(err)
		return err
	}

	return nil
}

// InvalidateTimeline removes cached timeline
func InvalidateTimeline(client *redis.Client, userID string) error {
	tracer := otel.Tracer("feed-service")
	ctx, span := tracer.Start(ctx, "cache.InvalidateTimeline")
	defer span.End()

	span.SetAttributes(
		attribute.String("cache.operation", "invalidate_timeline"),
		attribute.String("user.id", userID),
	)

	// Delete all pages
	pattern := fmt.Sprintf("timeline:%s:*", userID)
	iter := client.Scan(ctx, 0, pattern, 0).Iterator()

	for iter.Next(ctx) {
		err := client.Del(ctx, iter.Val()).Err()
		if err != nil {
			span.RecordError(err)
			return err
		}
	}

	if err := iter.Err(); err != nil {
		span.RecordError(err)
		return err
	}

	return nil
}

// GetPost gets cached post
func GetPost(client *redis.Client, postID string) (map[string]interface{}, error) {
	tracer := otel.Tracer("feed-service")
	ctx, span := tracer.Start(ctx, "cache.GetPost")
	defer span.End()

	span.SetAttributes(
		attribute.String("cache.operation", "get_post"),
		attribute.String("post.id", postID),
	)

	key := fmt.Sprintf("post:%s", postID)
	val, err := client.Get(ctx, key).Result()

	if err == redis.Nil {
		span.SetAttributes(attribute.Bool("cache.hit", false))
		return nil, nil
	} else if err != nil {
		span.RecordError(err)
		return nil, err
	}

	span.SetAttributes(attribute.Bool("cache.hit", true))

	var post map[string]interface{}
	err = json.Unmarshal([]byte(val), &post)
	if err != nil {
		span.RecordError(err)
		return nil, err
	}

	return post, nil
}

// SetPost caches post
func SetPost(client *redis.Client, postID string, post map[string]interface{}) error {
	tracer := otel.Tracer("feed-service")
	ctx, span := tracer.Start(ctx, "cache.SetPost")
	defer span.End()

	span.SetAttributes(
		attribute.String("cache.operation", "set_post"),
		attribute.String("post.id", postID),
	)

	key := fmt.Sprintf("post:%s", postID)
	data, err := json.Marshal(post)
	if err != nil {
		span.RecordError(err)
		return err
	}

	// Cache for 1 hour
	err = client.Set(ctx, key, data, time.Hour).Err()
	if err != nil {
		span.RecordError(err)
		return err
	}

	return nil
}
