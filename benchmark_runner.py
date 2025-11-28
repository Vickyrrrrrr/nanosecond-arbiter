#!/usr/bin/env python3
"""
Benchmark Runner for HFT Matching Engine
Compiles and runs Rust benchmarks, capturing performance metrics
"""

import subprocess
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple


class BenchmarkRunner:
    def __init__(self, project_dir: str = "."):
        self.project_dir = Path(project_dir)
        self.results = {}
    
    def compile_release(self) -> bool:
        """Compile Rust code with release optimizations"""
        print("🔨 Compiling Rust code with release optimizations...")
        try:
            result = subprocess.run(
                ["cargo", "build", "--release"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                print("✅ Compilation successful!")
                return True
            else:
                print(f"❌ Compilation failed:\n{result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Error during compilation: {e}")
            return False
    
    def run_benchmark(self, iterations: int = 5) -> Dict:
        """Run the main benchmark multiple times and collect metrics"""
        print(f"\n🚀 Running benchmark ({iterations} iterations)...")
        
        all_results = []
        
        for i in range(iterations):
            print(f"   Iteration {i+1}/{iterations}...", end=" ", flush=True)
            
            try:
                result = subprocess.run(
                    ["cargo", "run", "--release", "--bin", "hft_ringbuffer"],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    metrics = self._parse_output(result.stdout)
                    all_results.append(metrics)
                    print(f"✅ {metrics['latency_ns']}ns")
                else:
                    print(f"❌ Failed")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
        
        # Aggregate results
        if all_results:
            aggregated = self._aggregate_results(all_results)
            self.results = aggregated
            return aggregated
        else:
            return {}
    
    def _parse_output(self, output: str) -> Dict:
        """Parse benchmark output to extract metrics"""
        metrics = {
            'orders_processed': 0,
            'total_time_secs': 0.0,
            'throughput': 0.0,
            'latency_ns': 0,
        }
        
        # Extract orders processed
        match = re.search(r'Orders Processed:\s*([\d,]+)', output)
        if match:
            metrics['orders_processed'] = int(match.group(1).replace(',', ''))
        
        # Extract total time
        match = re.search(r'Total Time:\s*([\d.]+)\s*seconds', output)
        if match:
            metrics['total_time_secs'] = float(match.group(1))
        
        # Extract throughput
        match = re.search(r'Throughput:\s*([\d,]+)\s*orders/second', output)
        if match:
            metrics['throughput'] = float(match.group(1).replace(',', ''))
        
        # Extract latency
        match = re.search(r'Latency per Order:\s*(\d+)\s*ns', output)
        if match:
            metrics['latency_ns'] = int(match.group(1))
        
        return metrics
    
    def _aggregate_results(self, results: List[Dict]) -> Dict:
        """Aggregate multiple benchmark runs"""
        import numpy as np
        
        latencies = [r['latency_ns'] for r in results if r['latency_ns'] > 0]
        throughputs = [r['throughput'] for r in results if r['throughput'] > 0]
        
        aggregated = {
            'iterations': len(results),
            'latency_ns': {
                'mean': int(np.mean(latencies)) if latencies else 0,
                'median': int(np.median(latencies)) if latencies else 0,
                'min': int(np.min(latencies)) if latencies else 0,
                'max': int(np.max(latencies)) if latencies else 0,
                'std': int(np.std(latencies)) if latencies else 0,
                'all_values': latencies,
            },
            'throughput': {
                'mean': np.mean(throughputs) if throughputs else 0,
                'median': np.median(throughputs) if throughputs else 0,
                'min': np.min(throughputs) if throughputs else 0,
                'max': np.max(throughputs) if throughputs else 0,
                'std': np.std(throughputs) if throughputs else 0,
                'all_values': throughputs,
            },
            'orders_processed': results[0]['orders_processed'] if results else 0,
        }
        
        return aggregated
    
    def save_results(self, filename: str = "benchmark_data.json"):
        """Save results to JSON file"""
        output_path = self.project_dir / filename
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 Results saved to {output_path}")
    
    def print_summary(self):
        """Print a summary of benchmark results"""
        if not self.results:
            print("❌ No results to display")
            return
        
        print("\n" + "="*60)
        print("📊 BENCHMARK SUMMARY")
        print("="*60)
        
        lat = self.results['latency_ns']
        thr = self.results['throughput']
        
        print(f"\n⚡ Latency (nanoseconds per order):")
        print(f"   Mean:   {lat['mean']:,} ns")
        print(f"   Median: {lat['median']:,} ns")
        print(f"   Min:    {lat['min']:,} ns")
        print(f"   Max:    {lat['max']:,} ns")
        print(f"   StdDev: {lat['std']:,} ns")
        
        print(f"\n🚀 Throughput (orders per second):")
        print(f"   Mean:   {thr['mean']:,.0f} orders/sec")
        print(f"   Median: {thr['median']:,.0f} orders/sec")
        print(f"   Min:    {thr['min']:,.0f} orders/sec")
        print(f"   Max:    {thr['max']:,.0f} orders/sec")
        
        print(f"\n📦 Total Orders: {self.results['orders_processed']:,}")
        print(f"🔄 Iterations: {self.results['iterations']}")
        print("="*60)


def main():
    """Main entry point"""
    runner = BenchmarkRunner()
    
    # Compile
    if not runner.compile_release():
        print("❌ Compilation failed. Exiting.")
        return
    
    # Run benchmarks
    results = runner.run_benchmark(iterations=5)
    
    if results:
        runner.print_summary()
        runner.save_results()
    else:
        print("❌ No benchmark results collected")


if __name__ == "__main__":
    main()
