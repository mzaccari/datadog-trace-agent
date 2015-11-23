package main

import (
	"time"

	log "github.com/cihub/seelog"

	"github.com/DataDog/raclette/config"
	"github.com/DataDog/raclette/model"
)

// Flusher periodically triggers a synchronized flush from the workers
type Flusher struct {
	spans chan model.Span // Incoming chan of all spans, we put a span marker to trigger worker flushes

	conf *config.AgentConfig

	Worker
}

// NewFlusher creates a new Flusher
func NewFlusher(spans chan model.Span, conf *config.AgentConfig) *Flusher {
	f := &Flusher{
		spans: spans,
		conf:  conf,
	}
	f.Init()
	return f
}

// Start runs the Flusher
func (f *Flusher) Start() {
	f.wg.Add(1)

	ticker := time.NewTicker(f.conf.BucketInterval)
	go func() {
		for {
			select {
			case <-ticker.C:
				log.Debug("Flusher triggers a flush")
				f.spans <- model.NewFlushMarker()
			case <-f.exit:
				log.Info("Flusher exiting")
				ticker.Stop()
				f.wg.Done()
				return
			}
		}
	}()

	log.Info("Flusher started")
}
