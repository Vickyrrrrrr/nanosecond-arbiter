#!/usr/bin/env python3
"""
Complete Pipeline: Run benchmarks and generate visualizations
"""

import sys
from pathlib import Path

# Import our modules
from benchmark_runner import BenchmarkRunner
from visualize import VisualizationGenerator


def main():
    print("="*70)
    print("🚀 HFT MATCHING ENGINE - COMPLETE VISUALIZATION PIPELINE")
    print("="*70)
    print()
    
    # Step 1: Run benchmarks
    print("STEP 1: Running Benchmarks")
    print("-" * 70)
    runner = BenchmarkRunner()
    
    if not runner.compile_release():
        print("\n❌ Failed to compile. Exiting.")
        sys.exit(1)
    
    results = runner.run_benchmark(iterations=5)
    
    if not results:
        print("\n❌ No benchmark results. Exiting.")
        sys.exit(1)
    
    runner.print_summary()
    runner.save_results()
    
    # Step 2: Generate visualizations
    print("\n" + "="*70)
    print("STEP 2: Generating Visualizations")
    print("-" * 70)
    
    generator = VisualizationGenerator()
    generator.generate_all()
    
    print("\n" + "="*70)
    print("✅ PIPELINE COMPLETE!")
    print("="*70)
    print("\n📁 Check the 'visualizations' folder for your videos and charts!")
    print("🎬 You can now embed these in your README or portfolio.\n")


if __name__ == "__main__":
    main()
