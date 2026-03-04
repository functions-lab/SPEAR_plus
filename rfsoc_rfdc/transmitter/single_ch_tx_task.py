from rfsoc_rfdc.overlay_task import OverlayTask, TASK_STATE
from pynq.lib import AxiGPIO
from rfsoc_rfdc.transmitter.tx_channel_iq2real import TxChannelIq2Real
from rfsoc_rfdc.transmitter.tx_channel_real2real import TxChannelReal2Real
from rfsoc_rfdc.transmitter.tx_data_generator import TxDataGenerator

from rfsoc_rfdc.waveform_generator import WaveFormGenerator as wg
from rfsoc_rfdc.rfdc_config import ZCU216_CONFIG
import time


class SingleChTxTask(OverlayTask):
    """Single-Channel Tx Task"""

    def __init__(self, overlay, mode="iq2real"):
        super().__init__(overlay, name="SingleChTxTask")
        # Hardware IPs
        self.dma_ip = self.ol.dac_datapath.data_mover_ctrl
        self.fifo_count_ip = AxiGPIO(
            self.ol.ip_dict['dac_datapath/fifo_count']).channel1
        # Initialize Tx channels
        self._channel_factory(mode)
        self._layout_factory(mode)

    def _channel_factory(self, mode):
        if mode == "iq2real":
            tx_channel = TxChannelIq2Real(
                dma_ip=self.dma_ip,
                fifo_count_ip=self.fifo_count_ip,
                target_device=self.ol.PSDDR,
                debug_mode=False
            )
        elif mode == "real2real":
            tx_channel = TxChannelReal2Real(
                dma_ip=self.dma_ip,
                fifo_count_ip=self.fifo_count_ip,
                target_device=self.ol.PSDDR,
                debug_mode=False
            )
        else:
            raise RuntimeError(f"Unrecognized mode {mode}")

        self.tx_ch = tx_channel

    def _layout_factory(self, mode):
        if mode == "iq2real":
            tx_data_generator = TxDataGenerator()
            data = tx_data_generator.get_iq_samples()
            self.tx_ch.data_copy(complex_array=data)
        elif mode == "real2real":
            target_cw_freq_mhz = 100
            pts_per_period = int(ZCU216_CONFIG['DACSampleRate'] /
                                 ZCU216_CONFIG['DACInterpolationRate'] / target_cw_freq_mhz)
            data = wg.generate_sine_wave(repeat_time=10000, sample_pts=100)
            self.tx_ch.data_copy(real_array=data)
        else:
            raise RuntimeError(f"Unrecognized mode {mode}")

    def run(self):
        while self.task_state != TASK_STATE["STOP"]:
            if self.task_state == TASK_STATE["RUNNING"]:
                self.tx_ch.stream(duty_cycle=100)
                time.sleep(1)
            else:
                self.tx_ch.tx_dma.stop()
                time.sleep(1)
