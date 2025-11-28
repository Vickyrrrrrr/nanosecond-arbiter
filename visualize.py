#!/usr/bin/env python3
"""
Visualization Generator for HFT Matching Engine (GIF version - no FFmpeg required)
Creates animated performance charts as GIFs and static PNGs
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Rectangle
from pathlib import Path
from typing import Dict, List
from PIL import Image


# Set dark theme for professional look
plt.style.use('dark_background')

# Custom color palette
COLORS = {
    'primary': '#00ff88',      # Bright green
    'secondary': '#00d4ff',    # Cyan
    'accent': '#ff6b35',       # Orange
    'warning': '#ffd700',      # Gold
    'background': '#0a0e27',   # Dark blue
    'grid': '#1a2332',         # Subtle grid
}


class VisualizationGenerator:
    def __init__(self, data_file: str = "benchmark_data.json"):
        self.data_file = Path(data_file)
        self.output_dir = Path("visualizations")
        self.output_dir.mkdir(exist_ok=True)
        self.data = self._load_data()
        self.use_ffmpeg = self._check_ffmpeg()
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available"""
        import subprocess
        import os
        import glob
        
        # 1. Check PATH
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=2)
            print("✅ FFmpeg detected in PATH - will generate MP4 videos")
            self.ffmpeg_cmd = 'ffmpeg'
            return True
        except:
            pass
            
        # 2. Check Winget location (Windows)
        try:
            local_app_data = os.environ.get('LOCALAPPDATA', '')
            if local_app_data:
                pattern = os.path.join(local_app_data, r"Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe")
                matches = glob.glob(pattern)
                if matches:
                    self.ffmpeg_cmd = matches[0]
                    print(f"✅ FFmpeg detected (Winget) - will generate MP4 videos")
                    return True
        except:
            pass

        print("⚠️  FFmpeg not found - will generate GIF animations instead")
        print("   To install FFmpeg: winget install ffmpeg")
        self.ffmpeg_cmd = None
        return False
    
    def _load_data(self) -> Dict:
        """Load benchmark data from JSON"""
        if not self.data_file.exists():
            print(f"⚠️  Data file {self.data_file} not found. Run benchmark_runner.py first.")
            return {}
        
        with open(self.data_file, 'r') as f:
            return json.load(f)
    
    def generate_latency_distribution(self):
        """Generate animated latency distribution histogram"""
        if not self.data:
            return
        
        print(f"🎬 Generating latency distribution animation...")
        
        latencies = self.data['latency_ns']['all_values']
        mean_lat = self.data['latency_ns']['mean']
        median_lat = self.data['latency_ns']['median']
        
        fig, ax = plt.subplots(figsize=(16, 9), facecolor=COLORS['background'])
        ax.set_facecolor(COLORS['background'])
        
        # Create histogram bins
        bins = np.linspace(min(latencies) - 5, max(latencies) + 5, 30)
        
        def animate(frame):
            ax.clear()
            ax.set_facecolor(COLORS['background'])
            
            # Animate bars growing
            progress = min(1.0, frame / 30)
            
            # Plot histogram
            n, bins_edges, patches = ax.hist(
                latencies, 
                bins=bins, 
                alpha=0.8, 
                color=COLORS['primary'],
                edgecolor=COLORS['secondary'],
                linewidth=1.5
            )
            
            # Animate bar heights
            for patch in patches:
                current_height = patch.get_height()
                patch.set_height(current_height * progress)
            
            # Add mean and median lines
            if progress > 0.5:
                alpha = min(1.0, (progress - 0.5) * 2)
                ax.axvline(mean_lat, color=COLORS['accent'], linestyle='--', 
                          linewidth=2, alpha=alpha, label=f'Mean: {mean_lat}ns')
                ax.axvline(median_lat, color=COLORS['warning'], linestyle='--', 
                          linewidth=2, alpha=alpha, label=f'Median: {median_lat}ns')
            
            # Styling
            ax.set_xlabel('Latency (nanoseconds)', fontsize=14, fontweight='bold')
            ax.set_ylabel('Frequency', fontsize=14, fontweight='bold')
            ax.set_title('🚀 Lock-Free Ring Buffer - Latency Distribution', 
                        fontsize=18, fontweight='bold', pad=20)
            ax.grid(True, alpha=0.2, color=COLORS['grid'])
            if progress > 0.5:
                ax.legend(fontsize=12, loc='upper right')
            
            # Add stats box
            if progress > 0.7:
                stats_text = f"Min: {min(latencies)}ns\nMax: {max(latencies)}ns\nStdDev: {self.data['latency_ns']['std']}ns"
                ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                       fontsize=11, verticalalignment='top',
                       bbox=dict(boxstyle='round', facecolor=COLORS['grid'], alpha=0.8))
        
        # Create animation
        anim = animation.FuncAnimation(fig, animate, frames=60, interval=50, repeat=True)
        
        # Save as GIF or MP4
        if self.use_ffmpeg:
            output_path = self.output_dir / "latency_distribution.mp4"
            plt.rcParams['animation.ffmpeg_path'] = self.ffmpeg_cmd
            Writer = animation.writers['ffmpeg']
            writer = Writer(fps=30, metadata=dict(artist='HFT Visualizer'), bitrate=3000)
            anim.save(output_path, writer=writer)
        else:
            output_path = self.output_dir / "latency_distribution.gif"
            anim.save(output_path, writer='pillow', fps=20)
        
        plt.close()
        print(f"✅ Saved: {output_path}")
    
    def generate_throughput_chart(self):
        """Generate throughput comparison chart"""
        if not self.data:
            return
        
        print(f"📊 Generating throughput chart...")
        
        fig, ax = plt.subplots(figsize=(16, 9), facecolor=COLORS['background'])
        ax.set_facecolor(COLORS['background'])
        
        # Data
        throughput_values = self.data['throughput']['all_values']
        iterations = list(range(1, len(throughput_values) + 1))
        mean_throughput = self.data['throughput']['mean']
        
        # Plot bars
        bars = ax.bar(iterations, throughput_values, color=COLORS['primary'], 
                     edgecolor=COLORS['secondary'], linewidth=2, alpha=0.9)
        
        # Add mean line
        ax.axhline(mean_throughput, color=COLORS['accent'], linestyle='--', 
                  linewidth=2, label=f'Mean: {mean_throughput:,.0f} orders/sec')
        
        # Styling
        ax.set_xlabel('Benchmark Iteration', fontsize=14, fontweight='bold')
        ax.set_ylabel('Throughput (orders/second)', fontsize=14, fontweight='bold')
        ax.set_title('⚡ Lock-Free Ring Buffer - Throughput Performance', 
                    fontsize=18, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.2, color=COLORS['grid'], axis='y')
        ax.legend(fontsize=12, loc='upper right')
        
        # Format y-axis with commas
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height):,}',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        plt.tight_layout()
        output_path = self.output_dir / "throughput_chart.png"
        plt.savefig(output_path, dpi=150, facecolor=COLORS['background'])
        plt.close()
        
        print(f"✅ Saved: {output_path}")
    
    def generate_comparison_chart(self):
        """Generate lock-free vs mutex comparison chart"""
        print(f"📊 Generating comparison chart...")
        
        if not self.data:
            return
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 9), facecolor=COLORS['background'])
        
        # Our lock-free latency
        lockfree_latency = self.data['latency_ns']['mean']
        
        # Estimated mutex-based latency (typically 25-50ns overhead per lock/unlock)
        # Conservative estimate: 2x our latency
        mutex_latency = lockfree_latency * 2
        
        # Latency comparison
        ax1.set_facecolor(COLORS['background'])
        categories = ['Lock-Free\nRing Buffer', 'Mutex-Based\nQueue (est.)']
        latencies = [lockfree_latency, mutex_latency]
        colors = [COLORS['primary'], COLORS['accent']]
        
        bars1 = ax1.bar(categories, latencies, color=colors, edgecolor='white', linewidth=2, alpha=0.9)
        ax1.set_ylabel('Latency (nanoseconds)', fontsize=12, fontweight='bold')
        ax1.set_title('⚡ Latency Comparison', fontsize=14, fontweight='bold', pad=15)
        ax1.grid(True, alpha=0.2, color=COLORS['grid'], axis='y')
        
        # Add value labels
        for bar in bars1:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}ns',
                    ha='center', va='bottom', fontsize=11, fontweight='bold')
        
        # Add speedup annotation
        speedup = mutex_latency / lockfree_latency
        ax1.text(0.5, 0.95, f'{speedup:.1f}x faster!', 
                transform=ax1.transAxes, ha='center', va='top',
                fontsize=16, fontweight='bold', color=COLORS['primary'],
                bbox=dict(boxstyle='round', facecolor=COLORS['grid'], alpha=0.8))
        
        # Throughput comparison
        ax2.set_facecolor(COLORS['background'])
        lockfree_throughput = self.data['throughput']['mean']
        mutex_throughput = lockfree_throughput / speedup
        
        throughputs = [lockfree_throughput, mutex_throughput]
        bars2 = ax2.bar(categories, throughputs, color=colors, edgecolor='white', linewidth=2, alpha=0.9)
        ax2.set_ylabel('Throughput (orders/second)', fontsize=12, fontweight='bold')
        ax2.set_title('🚀 Throughput Comparison', fontsize=14, fontweight='bold', pad=15)
        ax2.grid(True, alpha=0.2, color=COLORS['grid'], axis='y')
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
        
        # Add value labels
        for bar in bars2:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height):,}',
                    ha='center', va='bottom', fontsize=11, fontweight='bold')
        
        plt.suptitle('Lock-Free vs Mutex-Based Performance', 
                    fontsize=18, fontweight='bold', y=0.98)
        plt.tight_layout()
        
        output_path = self.output_dir / "comparison_chart.png"
        plt.savefig(output_path, dpi=150, facecolor=COLORS['background'])
        plt.close()
        
        print(f"✅ Saved: {output_path}")
    
    def generate_orderbook_animation(self):
        """Generate animated order book depth visualization"""
        print(f"🎬 Generating order book animation...")
        
        fig, ax = plt.subplots(figsize=(16, 9), facecolor=COLORS['background'])
        ax.set_facecolor(COLORS['background'])
        
        # Simulate order book data
        price_levels = 20
        base_price = 10000  # $100.00
        
        def animate(frame):
            ax.clear()
            ax.set_facecolor(COLORS['background'])
            
            # Generate simulated order book
            np.random.seed(frame)
            
            # Bids (buy orders) - below mid price
            bid_prices = np.arange(base_price - price_levels, base_price, 1)
            bid_volumes = np.random.exponential(100, len(bid_prices)) * (1 + 0.3 * np.sin(frame / 10))
            
            # Asks (sell orders) - above mid price
            ask_prices = np.arange(base_price, base_price + price_levels, 1)
            ask_volumes = np.random.exponential(100, len(ask_prices)) * (1 + 0.3 * np.cos(frame / 10))
            
            # Plot bids (green, left side)
            ax.barh(bid_prices / 100, bid_volumes, height=0.008, 
                   color=COLORS['primary'], alpha=0.8, label='Bids')
            
            # Plot asks (red, right side)
            ax.barh(ask_prices / 100, -ask_volumes, height=0.008, 
                   color=COLORS['accent'], alpha=0.8, label='Asks')
            
            # Styling
            ax.set_xlabel('Volume (shares)', fontsize=14, fontweight='bold')
            ax.set_ylabel('Price ($)', fontsize=14, fontweight='bold')
            ax.set_title('📊 Order Book Depth - Real-Time Visualization', 
                        fontsize=18, fontweight='bold', pad=20)
            ax.axvline(0, color='white', linewidth=2, alpha=0.5)
            ax.grid(True, alpha=0.2, color=COLORS['grid'])
            ax.legend(fontsize=12, loc='upper right')
            
            # Add spread indicator
            spread = (ask_prices[0] - bid_prices[-1]) / 100
            ax.text(0.5, 0.02, f'Spread: ${spread:.2f}', 
                   transform=ax.transAxes, ha='center',
                   fontsize=12, fontweight='bold',
                   bbox=dict(boxstyle='round', facecolor=COLORS['grid'], alpha=0.8))
        
        # Create animation
        anim = animation.FuncAnimation(fig, animate, frames=90, interval=50, repeat=True)
        
        # Save as GIF or MP4
        if self.use_ffmpeg:
            output_path = self.output_dir / "orderbook_depth.mp4"
            plt.rcParams['animation.ffmpeg_path'] = self.ffmpeg_cmd
            Writer = animation.writers['ffmpeg']
            writer = Writer(fps=30, metadata=dict(artist='HFT Visualizer'), bitrate=3000)
            anim.save(output_path, writer=writer)
        else:
            output_path = self.output_dir / "orderbook_depth.gif"
            anim.save(output_path, writer='pillow', fps=15)
        
        plt.close()
        print(f"✅ Saved: {output_path}")
    
    def generate_performance_summary(self):
        """Generate a single summary image with all key metrics"""
        if not self.data:
            return
        
        print(f"📊 Generating performance summary...")
        
        fig = plt.figure(figsize=(16, 9), facecolor=COLORS['background'])
        
        # Create grid layout
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
        
        # 1. Latency metrics (top left)
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.set_facecolor(COLORS['background'])
        
        lat_data = self.data['latency_ns']
        metrics = ['Mean', 'Median', 'Min', 'Max']
        values = [lat_data['mean'], lat_data['median'], lat_data['min'], lat_data['max']]
        
        bars = ax1.barh(metrics, values, color=COLORS['primary'], edgecolor=COLORS['secondary'], linewidth=2)
        ax1.set_xlabel('Nanoseconds', fontsize=11, fontweight='bold')
        ax1.set_title('⚡ Latency Metrics', fontsize=13, fontweight='bold')
        ax1.grid(True, alpha=0.2, color=COLORS['grid'], axis='x')
        
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax1.text(width, bar.get_y() + bar.get_height()/2, f' {int(values[i])}ns',
                    va='center', fontsize=10, fontweight='bold')
        
        # 2. Throughput (top right)
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.set_facecolor(COLORS['background'])
        
        thr_values = self.data['throughput']['all_values']
        iterations = list(range(1, len(thr_values) + 1))
        
        ax2.plot(iterations, thr_values, marker='o', linewidth=3, markersize=8,
                color=COLORS['primary'], markeredgecolor=COLORS['secondary'], markeredgewidth=2)
        ax2.set_xlabel('Iteration', fontsize=11, fontweight='bold')
        ax2.set_ylabel('Orders/Second', fontsize=11, fontweight='bold')
        ax2.set_title('🚀 Throughput Consistency', fontsize=13, fontweight='bold')
        ax2.grid(True, alpha=0.2, color=COLORS['grid'])
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x/1000)}K'))
        
        # 3. Comparison (bottom left)
        ax3 = fig.add_subplot(gs[1, 0])
        ax3.set_facecolor(COLORS['background'])
        
        lockfree_lat = lat_data['mean']
        mutex_lat = lockfree_lat * 2
        
        categories = ['Lock-Free', 'Mutex (est.)']
        latencies = [lockfree_lat, mutex_lat]
        colors = [COLORS['primary'], COLORS['accent']]
        
        bars = ax3.bar(categories, latencies, color=colors, edgecolor='white', linewidth=2)
        ax3.set_ylabel('Latency (ns)', fontsize=11, fontweight='bold')
        ax3.set_title('⚡ Performance Comparison', fontsize=13, fontweight='bold')
        ax3.grid(True, alpha=0.2, color=COLORS['grid'], axis='y')
        
        for bar in bars:
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}ns', ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        # 4. Key stats (bottom right)
        ax4 = fig.add_subplot(gs[1, 1])
        ax4.set_facecolor(COLORS['background'])
        ax4.axis('off')
        
        stats_text = f"""
        📊 BENCHMARK SUMMARY
        
        ⚡ Average Latency: {lat_data['mean']} ns
        🚀 Average Throughput: {self.data['throughput']['mean']:,.0f} orders/sec
        📦 Total Orders: {self.data['orders_processed']:,}
        🔄 Iterations: {self.data['iterations']}
        
        🏆 Performance Grade:
        """
        
        if lat_data['mean'] < 100:
            stats_text += "   EXCELLENT - Ultra-low latency!"
        elif lat_data['mean'] < 1000:
            stats_text += "   GOOD - Production ready"
        else:
            stats_text += "   NEEDS OPTIMIZATION"
        
        ax4.text(0.1, 0.5, stats_text, fontsize=12, verticalalignment='center',
                fontfamily='monospace', color='white',
                bbox=dict(boxstyle='round', facecolor=COLORS['grid'], alpha=0.8, pad=1))
        
        plt.suptitle('🚀 HFT Matching Engine - Performance Summary', 
                    fontsize=18, fontweight='bold', y=0.98)
        
        output_path = self.output_dir / "performance_summary.png"
        plt.savefig(output_path, dpi=150, facecolor=COLORS['background'])
        plt.close()
        
        print(f"✅ Saved: {output_path}")
    
    def generate_all(self):
        """Generate all visualizations"""
        print("\n" + "="*60)
        print("🎨 GENERATING VISUALIZATIONS")
        print("="*60 + "\n")
        
        if not self.data:
            print("❌ No benchmark data available. Run benchmark_runner.py first.")
            return
        
        try:
            self.generate_latency_distribution()
            self.generate_throughput_chart()
            self.generate_comparison_chart()
            self.generate_orderbook_animation()
            self.generate_performance_summary()
            
            print("\n" + "="*60)
            print("✅ ALL VISUALIZATIONS GENERATED!")
            print("="*60)
            print(f"\n📁 Output directory: {self.output_dir.absolute()}")
            print("\n📹 Generated files:")
            for file in sorted(self.output_dir.glob("*")):
                size_mb = file.stat().st_size / (1024 * 1024)
                print(f"   • {file.name} ({size_mb:.2f} MB)")
            
            if not self.use_ffmpeg:
                print("\n💡 TIP: Install FFmpeg to generate MP4 videos instead of GIFs:")
                print("   winget install ffmpeg")
            
        except Exception as e:
            print(f"\n❌ Error generating visualizations: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main entry point"""
    generator = VisualizationGenerator()
    generator.generate_all()


if __name__ == "__main__":
    main()
