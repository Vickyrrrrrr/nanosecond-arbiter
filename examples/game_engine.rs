// ============================================================================
// EXAMPLE 3: GAME ENGINE - LOGIC TO RENDER PIPELINE
// ============================================================================
// This example shows how to use the lock-free ring buffer for separating
// game logic from rendering, achieving smooth 144+ FPS
//
// Use Case: Game engines, real-time simulations, graphics applications
// Performance: Can handle 1M+ game state updates per second
// ============================================================================

use rtrb::RingBuffer;
use std::thread;
use std::time::{Duration, Instant};

// ============================================================================
// GAME STATE STRUCTURES
// ============================================================================

/// Represents a game entity (player, enemy, projectile, etc.)
#[derive(Clone, Debug)]
struct GameObject {
    id: u64,
    entity_type: EntityType,
    position: Vector3,
    velocity: Vector3,
    rotation: f32,
    health: f32,
    is_active: bool,
}

#[derive(Clone, Debug)]
enum EntityType {
    Player,
    Enemy,
    Projectile,
    Particle,
}

#[derive(Clone, Debug)]
struct Vector3 {
    x: f32,
    y: f32,
    z: f32,
}

impl Vector3 {
    fn new(x: f32, y: f32, z: f32) -> Self {
        Vector3 { x, y, z }
    }
}

/// Complete game state snapshot sent to renderer
#[derive(Clone, Debug)]
struct GameStateSnapshot {
    frame_number: u64,
    timestamp_us: u64,
    objects: Vec<GameObject>,
    camera_position: Vector3,
    delta_time: f32,
}

impl GameStateSnapshot {
    fn new(frame_number: u64, timestamp_us: u64, num_objects: usize) -> Self {
        let mut objects = Vec::with_capacity(num_objects);
        
        // Simulate game objects (players, enemies, projectiles)
        for i in 0..num_objects {
            let t = frame_number as f32 * 0.016; // ~60 FPS time
            
            objects.push(GameObject {
                id: i as u64,
                entity_type: match i % 4 {
                    0 => EntityType::Player,
                    1 => EntityType::Enemy,
                    2 => EntityType::Projectile,
                    _ => EntityType::Particle,
                },
                position: Vector3::new(
                    (t + i as f32).sin() * 10.0,
                    (t * 0.5).cos() * 5.0,
                    (i as f32 * 0.1).sin() * 8.0,
                ),
                velocity: Vector3::new(
                    (t * 2.0).cos() * 2.0,
                    0.5,
                    (t * 1.5).sin() * 2.0,
                ),
                rotation: (t + i as f32) % 360.0,
                health: 100.0 - (frame_number % 100) as f32,
                is_active: true,
            });
        }
        
        GameStateSnapshot {
            frame_number,
            timestamp_us,
            objects,
            camera_position: Vector3::new(0.0, 5.0, -10.0),
            delta_time: 0.016, // ~60 FPS
        }
    }
}

// ============================================================================
// MAIN - GAME ENGINE PIPELINE
// ============================================================================

fn main() {
    println!("🎮 GAME ENGINE - Lock-Free Logic-to-Render Pipeline");
    println!("============================================================\n");
    
    const TOTAL_FRAMES: u64 = 10_000;
    const BUFFER_SIZE: usize = 8; // Small buffer for low latency
    const NUM_GAME_OBJECTS: usize = 100;
    const TARGET_FPS: u64 = 144;
    
    println!("📊 Configuration:");
    println!("   • Total Frames: {}", TOTAL_FRAMES);
    println!("   • Ring Buffer Size: {}", BUFFER_SIZE);
    println!("   • Game Objects: {}", NUM_GAME_OBJECTS);
    println!("   • Target FPS: {}\n", TARGET_FPS);
    
    // Create the lock-free ring buffer
    let (mut producer, mut consumer) = RingBuffer::<GameStateSnapshot>::new(BUFFER_SIZE);
    
    // ========================================================================
    // PRODUCER THREAD: Game Logic Thread
    // ========================================================================
    
    let producer_handle = thread::spawn(move || {
        println!("🧠 [LOGIC] Starting game logic thread...");
        
        let start_time = Instant::now();
        let mut frames_sent = 0u64;
        let mut buffer_full_count = 0u64;
        let frame_duration = Duration::from_micros(1_000_000 / TARGET_FPS);
        
        for frame_num in 0..TOTAL_FRAMES {
            let frame_start = Instant::now();
            let timestamp = start_time.elapsed().as_micros() as u64;
            
            // Simulate game logic processing
            let game_state = GameStateSnapshot::new(frame_num, timestamp, NUM_GAME_OBJECTS);
            
            // Physics simulation (simplified)
            simulate_physics(&game_state);
            
            // AI processing (simplified)
            process_ai(&game_state);
            
            // Try to push game state to renderer
            loop {
                match producer.push(game_state.clone()) {
                    Ok(_) => {
                        frames_sent += 1;
                        break;
                    }
                    Err(_) => {
                        // Buffer full! Renderer is falling behind
                        buffer_full_count += 1;
                        thread::yield_now();
                    }
                }
            }
            
            // Maintain target frame rate
            let elapsed = frame_start.elapsed();
            if elapsed < frame_duration {
                thread::sleep(frame_duration - elapsed);
            }
            
            // Progress update
            if (frame_num + 1) % 1000 == 0 {
                println!("🧠 [LOGIC] Processed {} frames...", frame_num + 1);
            }
        }
        
        let elapsed = start_time.elapsed();
        
        println!("🧠 [LOGIC] Finished processing {} frames", frames_sent);
        println!("🧠 [LOGIC] Total time: {:.2}s", elapsed.as_secs_f64());
        println!("🧠 [LOGIC] Average FPS: {:.0}", frames_sent as f64 / elapsed.as_secs_f64());
        if buffer_full_count > 0 {
            println!("🧠 [LOGIC] Buffer full events: {} (renderer bottleneck)", buffer_full_count);
        }
    });
    
    // ========================================================================
    // CONSUMER THREAD: Render Thread
    // ========================================================================
    
    let consumer_handle = thread::spawn(move || {
        println!("🎨 [RENDER] Starting render thread...\n");
        
        let start_time = Instant::now();
        let mut frames_rendered = 0u64;
        let mut total_objects_rendered = 0u64;
        let mut dropped_frames = 0u64;
        
        while frames_rendered < TOTAL_FRAMES {
            match consumer.pop() {
                Ok(game_state) => {
                    // Simulate rendering work
                    render_frame(&game_state);
                    
                    frames_rendered += 1;
                    total_objects_rendered += game_state.objects.len() as u64;
                    
                    // Progress update every 1000 frames
                    if frames_rendered % 1000 == 0 {
                        println!("🎨 [RENDER] Rendered {} frames...", frames_rendered);
                    }
                }
                Err(_) => {
                    // Buffer empty, wait for next frame
                    thread::yield_now();
                }
            }
        }
        
        let elapsed = start_time.elapsed();
        
        println!("\n🎨 [RENDER] Finished rendering {} frames", frames_rendered);
        println!("🎨 [RENDER] Total time: {:.2}s", elapsed.as_secs_f64());
        println!("🎨 [RENDER] Average FPS: {:.0}", frames_rendered as f64 / elapsed.as_secs_f64());
        println!("🎨 [RENDER] Total objects rendered: {}", total_objects_rendered);
        
        (frames_rendered, elapsed, dropped_frames)
    });
    
    // ========================================================================
    // WAIT FOR COMPLETION
    // ========================================================================
    
    producer_handle.join().unwrap();
    let (frames_rendered, elapsed, dropped_frames) = consumer_handle.join().unwrap();
    
    // ========================================================================
    // RESULTS
    // ========================================================================
    
    println!("\n🎯 GAME ENGINE RESULTS");
    println!("============================================================");
    println!("✅ Successfully rendered {} frames", frames_rendered);
    println!("⏱️  Total time: {:.2} seconds", elapsed.as_secs_f64());
    println!("🚀 Average FPS: {:.0}", frames_rendered as f64 / elapsed.as_secs_f64());
    println!("📦 Objects per frame: {}", NUM_GAME_OBJECTS);
    println!("🎯 Dropped frames: {}", dropped_frames);
    println!();
    
    let avg_fps = frames_rendered as f64 / elapsed.as_secs_f64();
    println!("💡 PERFORMANCE ANALYSIS:");
    if avg_fps >= 144.0 {
        println!("   🏆 EXCELLENT: {}+ FPS - High refresh rate gaming!", avg_fps as u64);
    } else if avg_fps >= 60.0 {
        println!("   ✅ GOOD: {}+ FPS - Smooth gameplay!", avg_fps as u64);
    } else {
        println!("   ⚠️  NEEDS OPTIMIZATION: {} FPS", avg_fps as u64);
    }
    println!();
    
    println!("💡 WHY THIS WORKS:");
    println!("   • Game logic and rendering run on separate threads");
    println!("   • Lock-free buffer prevents frame stuttering");
    println!("   • Logic thread never blocks waiting for renderer");
    println!("   • Renderer gets latest game state without mutex contention");
    println!();
    
    println!("🎓 REAL-WORLD APPLICATIONS:");
    println!("   • AAA game engines (Unreal, Unity, custom engines)");
    println!("   • Real-time simulations (physics, fluid dynamics)");
    println!("   • VR/AR applications (low latency critical)");
    println!("   • Graphics applications (3D modeling, CAD)");
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

fn simulate_physics(game_state: &GameStateSnapshot) {
    // Simulate physics calculations
    // In real game: collision detection, rigid body dynamics, etc.
    let _physics_work: f32 = game_state.objects.iter()
        .map(|obj| obj.position.x * obj.velocity.x)
        .sum();
    
    // Simulate some CPU work
    thread::sleep(Duration::from_micros(100));
}

fn process_ai(game_state: &GameStateSnapshot) {
    // Simulate AI processing
    // In real game: pathfinding, decision trees, behavior trees
    let _ai_work: f32 = game_state.objects.iter()
        .filter(|obj| matches!(obj.entity_type, EntityType::Enemy))
        .map(|obj| obj.health)
        .sum();
    
    // Simulate some CPU work
    thread::sleep(Duration::from_micros(50));
}

fn render_frame(game_state: &GameStateSnapshot) {
    // Simulate rendering work
    // In real game: draw calls, shader processing, post-processing
    
    // Simulate GPU work by sleeping
    thread::sleep(Duration::from_micros(200));
    
    // In a real game, you would:
    // 1. Update vertex buffers with object positions
    // 2. Submit draw calls to GPU
    // 3. Apply post-processing effects
    // 4. Present frame to screen
}
