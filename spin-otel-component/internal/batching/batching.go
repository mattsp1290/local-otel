package batching

import (
	"sync"
	"time"
)

// Batcher handles batching of telemetry data
type Batcher[T any] struct {
	items      []T
	maxSize    int
	timeout    time.Duration
	exportFunc func([]T) error
	mu         sync.Mutex
	timer      *time.Timer
	stopped    bool
}

// NewBatcher creates a new batcher
func NewBatcher[T any](maxSize int, timeout time.Duration, exportFunc func([]T) error) *Batcher[T] {
	b := &Batcher[T]{
		items:      make([]T, 0, maxSize),
		maxSize:    maxSize,
		timeout:    timeout,
		exportFunc: exportFunc,
		stopped:    false,
	}

	// Start the timeout timer
	b.resetTimer()

	return b
}

// Add adds an item to the batch
func (b *Batcher[T]) Add(item T) error {
	b.mu.Lock()
	defer b.mu.Unlock()

	if b.stopped {
		return nil
	}

	b.items = append(b.items, item)

	// If batch is full, export immediately
	if len(b.items) >= b.maxSize {
		return b.exportLocked()
	}

	return nil
}

// Flush forces export of all pending items
func (b *Batcher[T]) Flush() error {
	b.mu.Lock()
	defer b.mu.Unlock()

	if b.stopped {
		return nil
	}

	return b.exportLocked()
}

// Stop stops the batcher
func (b *Batcher[T]) Stop() {
	b.mu.Lock()
	defer b.mu.Unlock()

	b.stopped = true
	if b.timer != nil {
		b.timer.Stop()
	}
}

// exportLocked exports items (must be called with lock held)
func (b *Batcher[T]) exportLocked() error {
	if len(b.items) == 0 {
		return nil
	}

	// Make a copy of items to export
	itemsToExport := make([]T, len(b.items))
	copy(itemsToExport, b.items)

	// Clear the batch
	b.items = b.items[:0]

	// Reset timer
	b.resetTimer()

	// Export without holding the lock
	b.mu.Unlock()
	err := b.exportFunc(itemsToExport)
	b.mu.Lock()

	return err
}

// resetTimer resets the timeout timer
func (b *Batcher[T]) resetTimer() {
	if b.timer != nil {
		b.timer.Stop()
	}

	b.timer = time.AfterFunc(b.timeout, func() {
		b.mu.Lock()
		defer b.mu.Unlock()

		if !b.stopped {
			_ = b.exportLocked()
		}
	})
}
