# 🎨 Visualization Tools

This directory contains tools to generate animated performance charts and demo videos for the HFT Matching Engine.

## 📋 Prerequisites

1. **Python 3.7+** installed
2. **FFmpeg** installed (for video generation)
   - Windows: `winget install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org/)
   - Verify: `ffmpeg -version`

## 🚀 Quick Start

### Option 1: Complete Pipeline (Recommended)

Run everything in one command:

```bash
# Install dependencies
pip install -r requirements.txt

# Run benchmarks + generate visualizations
python run_visualization_pipeline.py
```

### Option 2: Step-by-Step

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run benchmarks
python benchmark_runner.py

# 3. Generate visualizations
python visualize.py
```

## 📹 Generated Outputs

All files are saved to the `visualizations/` directory:

### Videos (MP4)
- **`latency_distribution.mp4`** - Animated histogram showing latency distribution
- **`orderbook_depth.mp4`** - Real-time order book depth visualization

### Charts (PNG)
- **`throughput_chart.png`** - Throughput performance across iterations
- **`comparison_chart.png`** - Lock-free vs Mutex performance comparison

### Data (JSON)
- **`benchmark_data.json`** - Raw benchmark metrics for custom analysis

## 📊 What Gets Visualized

### 1. Latency Distribution
- Animated histogram of order processing latency
- Shows mean, median, min, max, and standard deviation
- Highlights ultra-low latency performance (<100ns)

### 2. Throughput Performance
- Bar chart showing orders/second across benchmark iterations
- Demonstrates consistency and peak performance
- Includes mean throughput line

### 3. Lock-Free vs Mutex Comparison
- Side-by-side comparison of latency and throughput
- Shows performance advantage of lock-free design
- Estimates mutex-based performance for comparison

### 4. Order Book Depth
- Animated visualization of bid/ask order book
- Real-time simulation of market depth
- Shows spread and volume distribution

## 🎬 Embedding in README

### For GitHub README

```markdown
# Performance Demo

![Latency Distribution](visualizations/latency_distribution.gif)

Or link to video:
[![Performance Demo](visualizations/thumbnail.png)](visualizations/latency_distribution.mp4)
```

### For Portfolio/Website

Upload the MP4 files to your hosting and embed:

```html
<video width="100%" controls>
  <source src="latency_distribution.mp4" type="video/mp4">
</video>
```

## 🔧 Customization

### Adjust Benchmark Parameters

Edit `benchmark_runner.py`:
```python
# Change number of iterations
results = runner.run_benchmark(iterations=10)
```

### Customize Visualizations

Edit `visualize.py`:
- Modify `COLORS` dictionary for different color schemes
- Adjust figure sizes in `figsize=(16, 9)`
- Change animation duration in `frames=60`

### Export Different Formats

```python
# In visualize.py, change save format:
plt.savefig(output_path, dpi=300, format='png')  # High-res PNG
plt.savefig(output_path, format='svg')           # Vector graphics
```

## 📈 Performance Tips

- **Faster generation**: Reduce animation frames (e.g., `frames=30`)
- **Smaller files**: Lower bitrate in `Writer(bitrate=1500)`
- **Higher quality**: Increase DPI in `savefig(dpi=300)`

## 🐛 Troubleshooting

### "FFmpeg not found"
Install FFmpeg:
```bash
# Windows
winget install ffmpeg

# Or download from https://ffmpeg.org/
```

### "No module named 'matplotlib'"
Install dependencies:
```bash
pip install -r requirements.txt
```

### "Benchmark data not found"
Run benchmarks first:
```bash
python benchmark_runner.py
```

### Videos won't play
- Ensure FFmpeg is installed and in PATH
- Try different video player (VLC, MPV)
- Check file isn't corrupted (re-run generation)

## 📝 Files Overview

| File | Purpose |
|------|---------|
| `requirements.txt` | Python dependencies |
| `benchmark_runner.py` | Runs Rust benchmarks, captures metrics |
| `visualize.py` | Generates charts and animations |
| `run_visualization_pipeline.py` | Complete automated pipeline |
| `VISUALIZATION_README.md` | This file |

## 🎯 Next Steps

1. ✅ Generate visualizations
2. 📤 Upload to GitHub repository
3. 📝 Embed in README.md
4. 🌐 Share on LinkedIn/portfolio
5. 🎥 Create demo video for presentations

---

**Questions?** Open an issue or check the main [README.md](../README.md)
