# 🎨 Quick Reference: Visualization Tools

## One-Line Commands

```bash
# Complete pipeline (recommended)
python run_visualization_pipeline.py

# Just visualizations (if you have benchmark_data.json)
python visualize.py

# Just benchmarks
python benchmark_runner.py
```

## What You Get

| File | Type | Description |
|------|------|-------------|
| `latency_distribution.gif` | Animated | Latency histogram with stats |
| `orderbook_depth.gif` | Animated | Real-time order book |
| `throughput_chart.png` | Static | Performance consistency |
| `comparison_chart.png` | Static | Lock-free vs Mutex |
| `performance_summary.png` | Static | Complete dashboard |

## Embedding in README

```markdown
## Performance Demo

![Performance](visualizations/performance_summary.png)

![Latency](visualizations/latency_distribution.gif)
```

## Upgrading to MP4

```bash
# Install FFmpeg
winget install ffmpeg

# Re-run visualizations
python visualize.py
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No module named 'matplotlib'" | `pip install -r requirements.txt` |
| "FFmpeg not found" | Use GIF output (works without FFmpeg) |
| "Benchmark data not found" | Run `python benchmark_runner.py` first |

## File Locations

- **Scripts**: Root directory (`*.py`)
- **Output**: `visualizations/` directory
- **Data**: `benchmark_data.json`
- **Docs**: `VISUALIZATION_GUIDE.md`

---

**Full documentation:** [VISUALIZATION_GUIDE.md](VISUALIZATION_GUIDE.md)
