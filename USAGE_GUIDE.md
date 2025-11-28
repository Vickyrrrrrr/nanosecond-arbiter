# Integration Guide

This document outlines patterns for integrating the lock-free ring buffer into various application domains. The implementation is generic and type-agnostic, supporting any `Send` + `Sync` data structure.

## Core Pattern

The fundamental pattern involves defining a data transfer object (DTO) and initializing the ring buffer with a specific capacity.

### 1. Define Data Structure

Define the payload struct that will be passed between threads.

```rust
// Example: Video Frame Payload
#[derive(Clone)]
struct VideoFrame {
    frame_id: u64,
    timestamp: u64,
    data: Vec<u8>,
}
```

### 2. Initialize Pipeline

```rust
use rtrb::RingBuffer;

// Initialize SPSC ring buffer with capacity 1024
let (mut producer, mut consumer) = RingBuffer::<VideoFrame>::new(1024);
```

### 3. Producer Implementation

The producer thread pushes data into the buffer. A spin-wait strategy is recommended for low-latency applications when the buffer is full.

```rust
let producer_handle = std::thread::spawn(move || {
    loop {
        let frame = capture_frame();
        
        // Spin-wait until space is available
        while let Err(_) = producer.push(frame.clone()) {
            std::hint::spin_loop(); // CPU-efficient spin
        }
    }
});
```

### 4. Consumer Implementation

The consumer thread pops data from the buffer.

```rust
let consumer_handle = std::thread::spawn(move || {
    loop {
        match consumer.pop() {
            Ok(frame) => process_frame(frame),
            Err(_) => std::hint::spin_loop(), // Buffer empty
        }
    }
});
```

## Domain-Specific Adaptations

### Video Processing Pipeline

*   **Producer**: Camera capture interface (e.g., V4L2, OpenCV).
*   **Consumer**: H.264/H.265 encoder or computer vision inference engine.
*   **Benefit**: Decouples capture rate from processing rate, preventing frame drops due to jitter.

### IoT Sensor Aggregation

*   **Producer**: High-frequency sensor polling loop (SPI/I2C).
*   **Consumer**: Data serialization and network transmission or disk I/O.
*   **Benefit**: Ensures deterministic sampling intervals even if I/O blocks.

### Network Packet Processing

*   **Producer**: Network interface card (NIC) polling or interrupt handler.
*   **Consumer**: Protocol stack parsing (TCP/IP, UDP).
*   **Benefit**: Handles micro-bursts of traffic without packet loss.

## Performance Considerations

### Buffer Sizing

*   **Small Buffer (256-1024)**: Lower memory footprint, higher cache locality, but less tolerant to bursty producer/consumer variance.
*   **Large Buffer (4096+)**: Higher memory usage, potentially more cache misses, but better absorption of processing jitter.

### Shutdown Signaling

For controlled shutdown, wrap the payload in an enum:

```rust
enum Message<T> {
    Payload(T),
    Shutdown,
}

// Producer
producer.push(Message::Shutdown).unwrap();

// Consumer
if let Ok(Message::Shutdown) = consumer.pop() {
    break;
}
```

### Memory Management

For large payloads (e.g., 4K video frames), avoid copying large `Vec<u8>` buffers. Instead, pass fixed-size arrays or pre-allocated buffers if possible, or use a pool of reusable buffers to minimize allocation overhead.
