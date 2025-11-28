// ============================================================================
// EXAMPLE 1: VIDEO FRAME PROCESSING
// ============================================================================
// This example shows how to use the lock-free ring buffer pattern for
// processing video frames in real-time (e.g., camera → encoder pipeline)
//
// Use Case: Live streaming, video recording, computer vision
// Performance: Can handle 60+ FPS without frame drops
// ============================================================================

use rtrb::RingBuffer;
use std::thread;
use std::time::{Duration, Instant};

// ============================================================================
// VIDEO FRAME STRUCTURE
// ============================================================================

/// Represents a single video frame
#[derive(Clone, Debug)]
struct VideoFrame {
    frame_number: u64,
    timestamp: u64,        // Microseconds since start
    width: u32,
    height: u32,
    format: VideoFormat,
    // In real app, this would be actual pixel data
    // For demo, we just simulate with a small buffer
    data_size: usize,
}

#[derive(Clone, Debug)]
enum VideoFormat {
    RGB24,
    YUV420,
    H264,
}

impl VideoFrame {
    fn new(frame_number: u64, timestamp: u64) -> Self {
        VideoFrame {
            frame_number,
            timestamp,
            width: 1920,
            height: 1080,
            format: VideoFormat::RGB24,
            data_size: 1920 * 1080 * 3, // RGB24 = 3 bytes per pixel
        }
    }
}

// ============================================================================
// MAIN - VIDEO PROCESSING PIPELINE
// ============================================================================

fn main() {
    println!("🎥 VIDEO PROCESSING PIPELINE - Lock-Free Ring Buffer Example");
    println!("============================================================\n");
    
    const TOTAL_FRAMES: u64 = 1000;
    const BUFFER_SIZE: usize = 64; // Small buffer to simulate real-time constraints
    
    println!("📊 Configuration:");
    println!("   • Total Frames: {}", TOTAL_FRAMES);
    println!("   • Ring Buffer Size: {}", BUFFER_SIZE);
    println!("   • Resolution: 1920x1080");
    println!("   • Target FPS: 60\n");
    
    // Create the lock-free ring buffer
    let (mut producer, mut consumer) = RingBuffer::<VideoFrame>::new(BUFFER_SIZE);
    
    // ========================================================================
    // PRODUCER THREAD: Camera / Video Source
    // ========================================================================
    
    let producer_handle = thread::spawn(move || {
        println!("📹 [CAMERA] Starting video capture...");
        
        let start_time = Instant::now();
        let mut frames_sent = 0u64;
        let mut buffer_full_count = 0u64;
        
        for frame_num in 0..TOTAL_FRAMES {
            let timestamp = start_time.elapsed().as_micros() as u64;
            let frame = VideoFrame::new(frame_num, timestamp);
            
            // Try to push frame into ring buffer
            loop {
                match producer.push(frame.clone()) {
                    Ok(_) => {
                        frames_sent += 1;
                        break;
                    }
                    Err(_) => {
                        // Buffer full! This would cause frame drops in a mutex-based system
                        buffer_full_count += 1;
                        thread::yield_now();
                    }
                }
            }
            
            // Simulate 60 FPS capture rate (16.67ms per frame)
            thread::sleep(Duration::from_micros(16670));
        }
        
        let elapsed = start_time.elapsed();
        
        println!("📹 [CAMERA] Finished capturing {} frames", frames_sent);
        println!("📹 [CAMERA] Total time: {:.2}s", elapsed.as_secs_f64());
        println!("📹 [CAMERA] Average FPS: {:.1}", frames_sent as f64 / elapsed.as_secs_f64());
        if buffer_full_count > 0 {
            println!("📹 [CAMERA] Buffer full events: {} (handled without dropping frames!)", buffer_full_count);
        }
    });
    
    // ========================================================================
    // CONSUMER THREAD: Video Encoder / Processor
    // ========================================================================
    
    let consumer_handle = thread::spawn(move || {
        println!("🎬 [ENCODER] Starting video encoding...\n");
        
        let start_time = Instant::now();
        let mut frames_processed = 0u64;
        let mut total_data_mb = 0.0;
        
        while frames_processed < TOTAL_FRAMES {
            match consumer.pop() {
                Ok(frame) => {
                    // Simulate encoding work (compression, format conversion, etc.)
                    // In real app, this would be H.264/H.265 encoding
                    simulate_encoding(&frame);
                    
                    frames_processed += 1;
                    total_data_mb += frame.data_size as f64 / (1024.0 * 1024.0);
                    
                    // Progress update every 100 frames
                    if frames_processed % 100 == 0 {
                        println!("🎬 [ENCODER] Processed {} frames...", frames_processed);
                    }
                }
                Err(_) => {
                    // Buffer empty, wait for more frames
                    thread::yield_now();
                }
            }
        }
        
        let elapsed = start_time.elapsed();
        
        println!("\n🎬 [ENCODER] Finished encoding {} frames", frames_processed);
        println!("🎬 [ENCODER] Total time: {:.2}s", elapsed.as_secs_f64());
        println!("🎬 [ENCODER] Average FPS: {:.1}", frames_processed as f64 / elapsed.as_secs_f64());
        println!("🎬 [ENCODER] Total data processed: {:.1} MB", total_data_mb);
        
        (frames_processed, elapsed)
    });
    
    // ========================================================================
    // WAIT FOR COMPLETION
    // ========================================================================
    
    producer_handle.join().unwrap();
    let (frames_processed, elapsed) = consumer_handle.join().unwrap();
    
    // ========================================================================
    // RESULTS
    // ========================================================================
    
    println!("\n🎯 PIPELINE RESULTS");
    println!("============================================================");
    println!("✅ Successfully processed {} frames", frames_processed);
    println!("⏱️  Total time: {:.2} seconds", elapsed.as_secs_f64());
    println!("🚀 Average throughput: {:.1} FPS", frames_processed as f64 / elapsed.as_secs_f64());
    println!("⚡ Zero frame drops (lock-free design prevents blocking!)");
    println!();
    
    println!("💡 WHY THIS WORKS:");
    println!("   • Lock-free ring buffer prevents encoder from blocking camera");
    println!("   • Camera captures at consistent 60 FPS");
    println!("   • Encoder processes frames as fast as possible");
    println!("   • No mutex contention = no frame drops");
    println!();
    
    println!("🎓 REAL-WORLD APPLICATIONS:");
    println!("   • Live streaming (Twitch, YouTube)");
    println!("   • Video conferencing (Zoom, Teams)");
    println!("   • Security cameras (real-time recording)");
    println!("   • Computer vision (object detection pipelines)");
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

fn simulate_encoding(frame: &VideoFrame) {
    // Simulate encoding work (in real app, this would be actual H.264 encoding)
    // We just sleep for a tiny bit to simulate CPU work
    thread::sleep(Duration::from_micros(100));
}
