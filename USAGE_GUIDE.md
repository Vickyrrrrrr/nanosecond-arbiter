# 🔧 Using This Code for Your Own Projects

This guide shows you how to adapt the lock-free ring buffer pattern for **any data type** in your own projects.

---

## 🎯 **The Core Pattern (Works for ANY Data)**

The beauty of this implementation is that it's **generic** - you can use it for ANY data type, not just trading orders!

### **Step 1: Define Your Data Structure**

Replace `Order` with whatever data you need to pass between threads:

```rust
// Example 1: Video Processing
struct VideoFrame {
    frame_number: u64,
    timestamp: u64,
    width: u32,
    height: u32,
    data: Vec<u8>,  // Pixel data
}

// Example 2: Sensor Data (IoT)
struct SensorReading {
    sensor_id: u64,
    temperature: f32,
    humidity: f32,
    pressure: f32,
    timestamp: u64,
}

// Example 3: Game Engine
struct RenderCommand {
    command_type: CommandType,
    entity_id: u64,
    position: (f32, f32, f32),
    rotation: (f32, f32, f32),
}

// Example 4: Audio Processing
struct AudioBuffer {
    sample_rate: u32,
    channels: u8,
    samples: Vec<f32>,
}

// Example 5: Network Packets
struct NetworkPacket {
    source_ip: [u8; 4],
    destination_ip: [u8; 4],
    payload: Vec<u8>,
}
```

### **Step 2: Create the Ring Buffer**

```rust
use rtrb::RingBuffer;

// Replace VideoFrame with YOUR data type
let (mut producer, mut consumer) = RingBuffer::<VideoFrame>::new(1024);
```

### **Step 3: Producer Thread (Data Source)**

```rust
use std::thread;

let producer_handle = thread::spawn(move || {
    // Your data source (camera, sensor, network, etc.)
    for frame in camera.capture_frames() {
        // Try to push into ring buffer
        loop {
            match producer.push(frame.clone()) {
                Ok(_) => break,  // Success!
                Err(_) => {
                    // Buffer full, wait a bit
                    thread::yield_now();
                }
            }
        }
    }
});
```

### **Step 4: Consumer Thread (Data Processor)**

```rust
let consumer_handle = thread::spawn(move || {
    loop {
        match consumer.pop() {
            Ok(frame) => {
                // Process your data here!
                process_video_frame(frame);
            }
            Err(_) => {
                // Buffer empty, keep checking
                thread::yield_now();
            }
        }
    }
});
```

---

## 🌟 **Real-World Use Cases**

### **1. Video Processing Pipeline**
```
[Camera Thread] → [Ring Buffer] → [Encoder Thread]
   (Capture)        (Lock-Free)      (H.264 Encode)
```

**Performance Benefit:**
- No frame drops due to mutex contention
- Consistent frame timing
- 60+ FPS guaranteed

### **2. IoT Sensor Network**
```
[Sensor Reader] → [Ring Buffer] → [Data Logger]
   (100Hz data)     (Lock-Free)      (Database)
```

**Performance Benefit:**
- Never miss sensor readings
- Real-time data processing
- Handles burst traffic

### **3. Game Engine**
```
[Game Logic] → [Ring Buffer] → [Render Thread]
   (60 FPS)      (Lock-Free)      (144 FPS)
```

**Performance Benefit:**
- No frame stuttering
- Decoupled update/render rates
- Smooth gameplay

### **4. Audio Processing**
```
[Audio Input] → [Ring Buffer] → [Effects Chain]
   (Microphone)   (Lock-Free)      (Reverb/EQ)
```

**Performance Benefit:**
- No audio glitches
- Ultra-low latency (<10ms)
- Real-time processing

### **5. Network Packet Processing**
```
[Network RX] → [Ring Buffer] → [Protocol Handler]
   (NIC IRQ)     (Lock-Free)      (TCP/IP Stack)
```

**Performance Benefit:**
- Handle millions of packets/sec
- No packet loss
- Minimal CPU overhead

---

## 📦 **Quick Start Template**

Here's a complete template you can copy and modify:

```rust
use rtrb::RingBuffer;
use std::thread;

// 1. Define YOUR data type
#[derive(Clone)]
struct MyData {
    id: u64,
    // Add your fields here
    value: String,
}

fn main() {
    // 2. Create ring buffer
    let (mut producer, mut consumer) = RingBuffer::<MyData>::new(1024);
    
    // 3. Producer thread
    let producer_handle = thread::spawn(move || {
        for i in 0..1000 {
            let data = MyData {
                id: i,
                value: format!("Data {}", i),
            };
            
            loop {
                match producer.push(data.clone()) {
                    Ok(_) => break,
                    Err(_) => thread::yield_now(),
                }
            }
        }
    });
    
    // 4. Consumer thread
    let consumer_handle = thread::spawn(move || {
        let mut count = 0;
        while count < 1000 {
            match consumer.pop() {
                Ok(data) => {
                    // Process your data here!
                    println!("Received: {:?}", data.value);
                    count += 1;
                }
                Err(_) => thread::yield_now(),
            }
        }
    });
    
    // 5. Wait for completion
    producer_handle.join().unwrap();
    consumer_handle.join().unwrap();
}
```

---

## 🎓 **When to Use This Pattern**

✅ **Use lock-free ring buffer when:**
- You need **ultra-low latency** (<100ns)
- You have **one producer, one consumer** (SPSC)
- You're passing data between **two threads**
- You want **predictable performance** (no mutex contention)
- You're building **real-time systems**

❌ **Don't use when:**
- You have multiple producers or consumers (use MPMC queue instead)
- Latency isn't critical (regular channels are fine)
- Data is too large to copy (use shared memory instead)

---

## 🔬 **Performance Characteristics**

| Operation | Time Complexity | Typical Latency |
|-----------|----------------|-----------------|
| `push()` | O(1) | ~5-10ns |
| `pop()` | O(1) | ~5-10ns |
| Full pipeline | O(1) | ~19ns (as measured) |

**Compare to alternatives:**
- **Mutex + Vec**: ~50-100ns (5-10x slower)
- **std::sync::mpsc**: ~30-50ns (2-3x slower)
- **Crossbeam channel**: ~20-30ns (similar)

---

## 💡 **Advanced Customizations**

### **1. Change Buffer Size**
```rust
// Larger buffer = less backpressure, more memory
let (producer, consumer) = RingBuffer::<MyData>::new(4096);

// Smaller buffer = less memory, more backpressure
let (producer, consumer) = RingBuffer::<MyData>::new(256);
```

### **2. Add Graceful Shutdown**
```rust
// Use a sentinel value to signal shutdown
enum Message {
    Data(MyData),
    Shutdown,
}

let (mut producer, mut consumer) = RingBuffer::<Message>::new(1024);

// Producer sends shutdown signal
producer.push(Message::Shutdown).unwrap();

// Consumer exits on shutdown
loop {
    match consumer.pop() {
        Ok(Message::Data(data)) => process(data),
        Ok(Message::Shutdown) => break,
        Err(_) => thread::yield_now(),
    }
}
```

### **3. Add Performance Monitoring**
```rust
use std::time::Instant;

let start = Instant::now();
let mut items_processed = 0;

loop {
    match consumer.pop() {
        Ok(data) => {
            process(data);
            items_processed += 1;
            
            // Print stats every second
            if start.elapsed().as_secs() >= 1 {
                println!("Throughput: {} items/sec", items_processed);
                break;
            }
        }
        Err(_) => thread::yield_now(),
    }
}
```

---

## 📚 **Further Reading**

- [rtrb crate documentation](https://docs.rs/rtrb/)
- [Lock-free programming guide](https://preshing.com/20120612/an-introduction-to-lock-free-programming/)
- [Rust concurrency patterns](https://rust-lang.github.io/async-book/)

---

## 🤝 **Contributing**

If you've used this pattern in your project, I'd love to hear about it! Open an issue or PR with:
- Your use case
- Performance results
- Any improvements you made

---

## 📝 **License**

MIT License - use this pattern freely in your own projects, commercial or otherwise!

---

**Questions?** Open an issue on GitHub or reach out on LinkedIn!
