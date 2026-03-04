# rfsoc_rfdc

Python library for controlling **Xilinx RFSoC RF Data Converters** (RFDC) on
[PYNQ](https://www.pynq.io/)-enabled boards (e.g. ZCU216).

## Features

| Area | Description |
|------|-------------|
| **RFDC control** | DAC/ADC tile configuration, mixer, NCO, interpolation/decimation |
| **Clock management** | LMK04828 distribution IC and LMX2594 PLL programming |
| **Multi-Tile Sync** | Coherent DAC/ADC alignment across tiles (MTS) |
| **Transmit tasks** | Single-channel, multi-channel, and MIMO transmit orchestration |
| **Receive tasks** | Single-channel, multi-channel, and MIMO receive orchestration |
| **DSP** | OFDM (16/256 QAM), Zadoff-Chu detection, CFO estimation |
| **DMA drivers** | Streaming DMA controller wrappers (v1–v4) |
| **Waveforms** | Sine, cosine, square, triangle, sawtooth, Zadoff-Chu, PRBS |
| **IQ loading** | NumPy `.npy` and MATLAB `.mat` file loaders |
| **Visualization** | Time-domain, FFT, BER, and EVM plots |

## Quick Start

```python
from rfsoc_rfdc.rfsoc_overlay import RFSoCOverlay
from rfsoc_rfdc.rfdc_task import RfdcTask

overlay = RFSoCOverlay("design.bit")
rfdc = RfdcTask(overlay)
rfdc.start()
```

## Architecture

```
rfsoc_rfdc/
├── rfdc.py               # RF Data Converter controller
├── rfdc_config.py        # Hardware configuration dictionaries
├── rfdc_task.py          # RFDC + clock + MTS orchestration
├── rfsoc_overlay.py      # PYNQ overlay / bitstream management
├── overlay_task.py       # Abstract task base classes
├── clocks.py             # LMK04828 / LMX2594 clock configuration
├── mts.py                # Multi-Tile Synchronization
├── iq_loader.py          # IQ sample file loaders
├── waveform_generator.py # Waveform synthesis
├── dma_monitor.py        # DMA controller drivers
├── multi_ch_mem_layout.py# Multi-channel DMA memory layout
├── throughput_timer.py   # Performance measurement
├── cmac_task.py          # CMAC transceiver task
├── dsp/                  # Signal processing (OFDM, detection, MIMO)
├── receiver/             # ADC channel wrappers and Rx tasks
├── transmitter/          # DAC channel wrappers and Tx tasks
└── plotter/              # Matplotlib / Plotly visualization
```

## API Reference

See the **API Reference** tab for full auto-generated documentation of every
module, class, and function.
