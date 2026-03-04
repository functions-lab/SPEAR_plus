# API Reference

Complete auto-generated documentation for all public modules, classes, and
functions in **rfsoc_rfdc**.

## Core Modules

| Module | Description |
|--------|-------------|
| [rfdc](rfdc.md) | RF Data Converter tiles, mixer config, amplitude helpers |
| [rfdc_config](rfdc_config.md) | ZCU216 hardware configuration dictionaries |
| [rfdc_task](rfdc_task.md) | RFDC + clock + MTS task orchestration |
| [rfsoc_overlay](rfsoc_overlay.md) | PYNQ bitstream overlay management |
| [overlay_task](overlay_task.md) | Abstract task base classes |
| [clocks](clocks.md) | LMK04828 / LMX2594 clock IC configuration |
| [mts](mts.md) | Multi-Tile Synchronization engine |
| [iq_loader](iq_loader.md) | IQ sample loaders (NumPy, MATLAB) |
| [waveform_generator](waveform_generator.md) | Waveform synthesis |
| [dma_monitor](dma_monitor.md) | Streaming DMA controller drivers |
| [multi_ch_mem_layout](multi_ch_mem_layout.md) | Multi-channel DMA memory layout |
| [throughput_timer](throughput_timer.md) | Performance measurement |
| [cmac_task](cmac_task.md) | CMAC transceiver task |

## Sub-packages

| Package | Description |
|---------|-------------|
| [dsp](dsp/index.md) | OFDM, Zadoff-Chu detection, MIMO |
| [receiver](receiver/index.md) | ADC channel wrappers and Rx tasks |
| [transmitter](transmitter/index.md) | DAC channel wrappers and Tx tasks |
| [plotter](plotter/index.md) | Time-domain, FFT, BER, EVM plots |
