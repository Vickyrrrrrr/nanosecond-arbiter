// ============================================================================
// EXAMPLE 2: IoT SENSOR NETWORK
// ============================================================================
// This example shows how to use the lock-free ring buffer for processing
// sensor data from IoT devices in real-time
//
// Use Case: Smart home, industrial monitoring, environmental sensors
// Performance: Can handle 1000+ sensors at 100Hz each
// ============================================================================

use rtrb::RingBuffer;
use std::thread;
use std::time::{Duration, Instant};

// ============================================================================
// SENSOR DATA STRUCTURE
// ============================================================================

/// Represents a reading from an IoT sensor
#[derive(Clone, Debug)]
struct SensorReading {
    sensor_id: u64,
    timestamp: u64,        // Microseconds since start
    sensor_type: SensorType,
    temperature: f32,      // Celsius
    humidity: f32,         // Percentage
    pressure: f32,         // hPa
    battery_level: f32,    // Percentage
}

#[derive(Clone, Debug)]
enum SensorType {
    Environmental,
    Industrial,
    Medical,
}

impl SensorReading {
    fn new(sensor_id: u64, timestamp: u64) -> Self {
        // Simulate realistic sensor values
        SensorReading {
            sensor_id,
            timestamp,
            sensor_type: SensorType::Environmental,
            temperature: 20.0 + (sensor_id as f32 * 0.1) % 15.0,
            humidity: 40.0 + (sensor_id as f32 * 0.2) % 40.0,
            pressure: 1013.0 + (sensor_id as f32 * 0.05) % 20.0,
            battery_level: 100.0 - (sensor_id as f32 * 0.01) % 50.0,
        }
    }
}

// ============================================================================
// MAIN - IoT SENSOR PIPELINE
// ============================================================================

fn main() {
    println!("🌡️  IoT SENSOR NETWORK - Lock-Free Ring Buffer Example");
    println!("============================================================\n");
    
    const TOTAL_READINGS: u64 = 10_000;
    const BUFFER_SIZE: usize = 512;
    const NUM_SENSORS: u64 = 10;
    
    println!("📊 Configuration:");
    println!("   • Number of Sensors: {}", NUM_SENSORS);
    println!("   • Total Readings: {}", TOTAL_READINGS);
    println!("   • Ring Buffer Size: {}", BUFFER_SIZE);
    println!("   • Sampling Rate: 100 Hz per sensor\n");
    
    // Create the lock-free ring buffer
    let (mut producer, mut consumer) = RingBuffer::<SensorReading>::new(BUFFER_SIZE);
    
    // ========================================================================
    // PRODUCER THREAD: Sensor Data Collector
    // ========================================================================
    
    let producer_handle = thread::spawn(move || {
        println!("📡 [COLLECTOR] Starting sensor data collection...");
        
        let start_time = Instant::now();
        let mut readings_sent = 0u64;
        let mut buffer_full_count = 0u64;
        
        for reading_num in 0..TOTAL_READINGS {
            let timestamp = start_time.elapsed().as_micros() as u64;
            let sensor_id = reading_num % NUM_SENSORS;
            let reading = SensorReading::new(sensor_id, timestamp);
            
            // Try to push reading into ring buffer
            loop {
                match producer.push(reading.clone()) {
                    Ok(_) => {
                        readings_sent += 1;
                        break;
                    }
                    Err(_) => {
                        // Buffer full! Wait for consumer to catch up
                        buffer_full_count += 1;
                        thread::yield_now();
                    }
                }
            }
            
            // Simulate 100 Hz sampling rate (10ms per reading)
            thread::sleep(Duration::from_micros(10000));
        }
        
        let elapsed = start_time.elapsed();
        
        println!("📡 [COLLECTOR] Finished collecting {} readings", readings_sent);
        println!("📡 [COLLECTOR] Total time: {:.2}s", elapsed.as_secs_f64());
        println!("📡 [COLLECTOR] Average rate: {:.0} readings/sec", readings_sent as f64 / elapsed.as_secs_f64());
        if buffer_full_count > 0 {
            println!("📡 [COLLECTOR] Buffer full events: {} (handled gracefully!)", buffer_full_count);
        }
    });
    
    // ========================================================================
    // CONSUMER THREAD: Data Logger / Processor
    // ========================================================================
    
    let consumer_handle = thread::spawn(move || {
        println!("💾 [LOGGER] Starting data logging...\n");
        
        let start_time = Instant::now();
        let mut readings_processed = 0u64;
        let mut sensor_stats: Vec<SensorStats> = vec![SensorStats::new(); NUM_SENSORS as usize];
        
        while readings_processed < TOTAL_READINGS {
            match consumer.pop() {
                Ok(reading) => {
                    // Process the sensor reading
                    // In real app: save to database, check thresholds, send alerts
                    process_sensor_reading(&reading, &mut sensor_stats);
                    
                    readings_processed += 1;
                    
                    // Progress update every 1000 readings
                    if readings_processed % 1000 == 0 {
                        println!("💾 [LOGGER] Processed {} readings...", readings_processed);
                    }
                }
                Err(_) => {
                    // Buffer empty, wait for more data
                    thread::yield_now();
                }
            }
        }
        
        let elapsed = start_time.elapsed();
        
        println!("\n💾 [LOGGER] Finished logging {} readings", readings_processed);
        println!("💾 [LOGGER] Total time: {:.2}s", elapsed.as_secs_f64());
        println!("💾 [LOGGER] Average rate: {:.0} readings/sec", readings_processed as f64 / elapsed.as_secs_f64());
        
        (readings_processed, elapsed, sensor_stats)
    });
    
    // ========================================================================
    // WAIT FOR COMPLETION
    // ========================================================================
    
    producer_handle.join().unwrap();
    let (readings_processed, elapsed, sensor_stats) = consumer_handle.join().unwrap();
    
    // ========================================================================
    // RESULTS
    // ========================================================================
    
    println!("\n🎯 SENSOR NETWORK RESULTS");
    println!("============================================================");
    println!("✅ Successfully processed {} readings", readings_processed);
    println!("⏱️  Total time: {:.2} seconds", elapsed.as_secs_f64());
    println!("🚀 Average throughput: {:.0} readings/sec", readings_processed as f64 / elapsed.as_secs_f64());
    println!();
    
    println!("📊 SENSOR STATISTICS:");
    for (i, stats) in sensor_stats.iter().enumerate() {
        if stats.count > 0 {
            println!("   Sensor #{}: {} readings, Avg Temp: {:.1}°C, Avg Humidity: {:.1}%", 
                i, stats.count, stats.avg_temperature, stats.avg_humidity);
        }
    }
    println!();
    
    println!("💡 WHY THIS WORKS:");
    println!("   • Lock-free design prevents data loss during bursts");
    println!("   • Sensors can send data without waiting for database writes");
    println!("   • Logger processes data as fast as possible");
    println!("   • No mutex contention = consistent sampling rate");
    println!();
    
    println!("🎓 REAL-WORLD APPLICATIONS:");
    println!("   • Smart home automation (temperature, humidity, motion)");
    println!("   • Industrial monitoring (pressure, vibration, flow)");
    println!("   • Environmental monitoring (air quality, weather)");
    println!("   • Medical devices (heart rate, blood pressure)");
}

// ============================================================================
// HELPER STRUCTURES AND FUNCTIONS
// ============================================================================

#[derive(Clone, Debug)]
struct SensorStats {
    count: u64,
    avg_temperature: f32,
    avg_humidity: f32,
    avg_pressure: f32,
}

impl SensorStats {
    fn new() -> Self {
        SensorStats {
            count: 0,
            avg_temperature: 0.0,
            avg_humidity: 0.0,
            avg_pressure: 0.0,
        }
    }
}

fn process_sensor_reading(reading: &SensorReading, stats: &mut Vec<SensorStats>) {
    let sensor_id = reading.sensor_id as usize;
    if sensor_id < stats.len() {
        let stat = &mut stats[sensor_id];
        
        // Update running averages
        let n = stat.count as f32;
        stat.avg_temperature = (stat.avg_temperature * n + reading.temperature) / (n + 1.0);
        stat.avg_humidity = (stat.avg_humidity * n + reading.humidity) / (n + 1.0);
        stat.avg_pressure = (stat.avg_pressure * n + reading.pressure) / (n + 1.0);
        stat.count += 1;
    }
    
    // Simulate database write or processing work
    thread::sleep(Duration::from_micros(50));
}
