# Performance Visualization Suite

This repository includes a Python-based visualization suite for analyzing the performance characteristics of the ring buffer implementation. It generates latency histograms, throughput timelines, and order book depth visualizations.

## Overview

The visualization pipeline (`run_visualization_pipeline.py`) automates the following:
1.  Compiles the Rust project with `release` optimizations.
2.  Executes the benchmark harness (`benchmark_runner.py`) to collect raw metrics.
3.  Parses the output and generates visualizations (`visualize.py`).

## Requirements

*   Python 3.8+
*   Dependencies: `matplotlib`, `numpy`, `pillow`
*   **Optional**: `ffmpeg` (for MP4 video generation; falls back to GIF if absent)

```bash
pip install -r requirements.txt
```

## Usage

### Automated Pipeline

Run the full benchmark and visualization suite:

```bash
python run_visualization_pipeline.py
```

### Manual Execution

To generate visualizations from existing benchmark data (`benchmark_data.json`):

```bash
python visualize.py
```

To run benchmarks without generating visualizations:

```bash
python benchmark_runner.py
```

## Output Artifacts

Artifacts are generated in the `visualizations/` directory:

| File | Type | Description |
|:-----|:-----|:------------|
| `latency_distribution.gif` | Animation | Histogram of inter-thread latency distribution. |
| `throughput_chart.png` | Chart | Orders processed per second over time. |
| `orderbook_depth.gif` | Animation | Simulated order book depth dynamics. |
| `comparison_chart.png` | Chart | Performance comparison vs. mutex-based queues. |
| `performance_summary.png` | Dashboard | Aggregated key performance indicators (KPIs). |

## Configuration

### Benchmark Parameters

Modify `benchmark_runner.py` to adjust the number of iterations or test duration:

```python
# benchmark_runner.py
results = runner.run_benchmark(iterations=10)
```

### Visualization Settings

Modify `visualize.py` to customize chart aesthetics or output formats:

```python
# visualize.py
COLORS = {
    'primary': '#00ff88',
    'background': '#0a0e27',
    # ...
}
```

## FFmpeg Support

The tool automatically detects `ffmpeg`. If available, animations are rendered as high-quality MP4 files. If not found, it falls back to generating GIFs using `Pillow`.

To enable MP4 support on Windows:
```powershell
winget install ffmpeg
```
