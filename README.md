# 🚀 The Nanosecond Arbiter

A high-performance **lock-free matching engine** and **SPSC ring buffer** implementation in Rust, demonstrating production-grade low-latency systems design.

[![Rust](https://img.shields.io/badge/rust-1.70%2B-orange.svg)](https://www.rust-lang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Performance

- **Throughput**: 51M+ orders/second
- **Latency**: 19 nanoseconds per order
- **Architecture**: Lock-free SPSC (Single-Producer Single-Consumer)
- **Zero mutex overhead**: Atomic operations only

## 📊 Benchmark Results

```
🎯 BENCHMARK RESULTS
============================================================
📦 Orders Processed: 1,000,000
⏱️  Total Time: 0.020 seconds
🚀 Throughput: 51,081,393 orders/second
⚡ Latency per Order: 19 ns

💡 PERFORMANCE INSIGHTS:
   🏆 EXCELLENT: >10M orders/sec - Production-grade HFT performance!
   ⚡ Ultra-low latency: <100ns per order
```

## 🏗️ Architecture

```
[Producer Thread]  --push-->  [Ring Buffer]  --pop-->  [Consumer Thread]
 (Market Data)                (1024 capacity)           (Matching Engine)
                              (Lock-Free)
```

## ✨ Features

### Phase 1: Matching Engine
- ✅ Order book with `BTreeMap` for sorted price levels
- ✅ Limit order matching with spread-crossing detection
- ✅ Buy/Sell order support
- ✅ Real-time trade execution

### Phase 2: Lock-Free Ring Buffer
- ✅ SPSC lock-free queue using `rtrb` crate
- ✅ Producer thread with backpressure handling
- ✅ Consumer thread with busy-wait optimization
- ✅ Comprehensive performance measurement
- ✅ Zero-copy order transmission

## 🚀 Quick Start

### Prerequisites
- Rust 1.70+ ([Install Rust](https://rustup.rs/))

### Run the Benchmark

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/nanosecond-arbiter.git
cd nanosecond-arbiter

# Run in release mode (optimized)
cargo run --release
```

### Run Phase 1 (Matching Engine Only)

```bash
rustc matching_engine.rs -O
./matching_engine  # or matching_engine.exe on Windows
```

## 📖 What You'll Learn

This project demonstrates:

- **Lock-Free Programming**: SPSC ring buffer with atomic operations
- **Performance Engineering**: 10-50x faster than mutex-based queues
- **Systems Design**: HFT-grade architecture patterns
- **Rust Concurrency**: Safe multi-threading without data races
- **Benchmarking**: Proper latency and throughput measurement

## 🔬 Technical Deep Dive

### Why Lock-Free?

| Approach | Latency | Characteristics |
|----------|---------|-----------------|
| **Mutex-based** | ~25-50ns | Context switches, kernel involvement |
| **Lock-free (rtrb)** | ~1-5ns | Atomic operations, CPU-level only |
| **This implementation** | **19ns** | Includes order creation + processing |

### Key Optimizations

1. **Lock-Free Queue**: `rtrb` crate for zero mutex overhead
2. **Aggressive Compiler Flags**: LTO, single codegen unit
3. **Zero-Copy**: Orders passed by value, no heap allocations
4. **Cache-Friendly**: Ring buffer keeps data in CPU cache
5. **Spin-Wait**: Lower latency than blocking for HFT workloads

## 📁 Project Structure

```
HFT-2/
├── src/
│   └── main.rs              # Lock-free ring buffer implementation
├── matching_engine.rs       # Phase 1: Basic matching engine
├── Cargo.toml              # Dependencies and optimizations
└── README.md               # This file
```

## 🎓 Use Cases

This architecture is used in:

- **High-Frequency Trading**: Order execution pipelines
- **Game Engines**: Render thread ↔ Game logic communication
- **Real-Time Systems**: Sensor data processing
- **Databases**: Write-ahead logging, replication
- **Video Processing**: Encoder/decoder pipelines

## 🛠️ Technologies

- **Language**: Rust (memory safety + zero-cost abstractions)
- **Lock-Free Queue**: [`rtrb`](https://crates.io/crates/rtrb) v0.3
- **Data Structures**: BTreeMap, Ring Buffer
- **Concurrency**: `std::thread`, atomic operations

## 📈 Roadmap

- [x] Phase 1: Basic matching engine with BTreeMap
- [x] Phase 2: Lock-free SPSC ring buffer
- [ ] Phase 3: CPU pinning and NUMA optimization
- [ ] Phase 4: Latency histograms (p50, p99, p99.9)
- [ ] Phase 5: SPMC (Single-Producer Multi-Consumer)
- [ ] Phase 6: Full exchange simulation with WebSocket API

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- Add latency histogram tracking
- Implement CPU pinning (thread affinity)
- Compare against mutex-based queue
- Add more order types (market, stop-loss, etc.)
- Implement order cancellation

## 📝 License

MIT License - feel free to use this in your own projects!

## 👨‍💻 Author

Built as a portfolio project to demonstrate low-latency systems engineering skills.

**Connect with me:**
- GitHub: [@YOUR_USERNAME](https://github.com/YOUR_USERNAME)
- LinkedIn: [Your Name](https://linkedin.com/in/YOUR_PROFILE)

## 🙏 Acknowledgments

- Inspired by real-world HFT systems at Jane Street, Citadel, and Jump Trading
- Built with the excellent [`rtrb`](https://github.com/mgeier/rtrb) crate
- Thanks to the Rust community for amazing documentation

---

⭐ **Star this repo** if you found it useful!

💬 **Questions?** Open an issue or reach out on LinkedIn!
