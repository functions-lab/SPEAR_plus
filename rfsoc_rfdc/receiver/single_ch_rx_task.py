from rfsoc_rfdc.overlay_task import OverlayTask, TASK_STATE

from rfsoc_rfdc.receiver.rx_channel_real2iq import RxChannelReal2Iq
from rfsoc_rfdc.receiver.rx_channel_real2real import RxChannelReal2Real
from rfsoc_rfdc.receiver.rx_analyzer import Real2IqRxAnalyzer, Real2RealRxAnalyzer
from rfsoc_rfdc.rfdc_config import ZCU216_CONFIG
from pynq.lib import AxiGPIO
import time


class SingleChRxTask(OverlayTask):
    """Single-Channel ADC Task"""

    def __init__(self, overlay, mode="real2iq", buff_size=2**18):
        """Initialize SingleChRxTask"""
        super().__init__(overlay, name="SingleChRxTask")
        self.mode = mode
        # Receiver datapath parameters
        self.buff_size = buff_size
        # Hardware IPs
        self.dma_ip = self.ol.adc_datapath.data_mover_ctrl
        self.fifo_count_ip = AxiGPIO(
            self.ol.ip_dict['adc_datapath/fifo_count']).channel1
        # Initialize Rx channel
        self._receiver_factory(mode)

    def _receiver_factory(self, mode):
        """Create appropriate channel object based on mode"""
        if mode == "real2iq":
            rx_channel = RxChannelReal2Iq(
                dma_ip=self.dma_ip,
                fifo_count_ip=self.fifo_count_ip,
                target_device=self.ol.ddr4_rx,
                buff_size=self.buff_size,
                debug_mode=True
            )
            rx_analyzer = Real2IqRxAnalyzer(
                ofdm_scheme=ZCU216_CONFIG['OFDM_SCHEME'], detect_scheme=ZCU216_CONFIG['DETECTION_SCHEME'])
        elif mode == "real2real":
            rx_channel = RxChannelReal2Real(
                dma_ip=self.dma_ip,
                fifo_count_ip=self.fifo_count_ip,
                target_device=self.ol.ddr4_rx,
                buff_size=self.buff_size,
                debug_mode=False
            )
            rx_analyzer = Real2RealRxAnalyzer()
        else:
            raise RuntimeError(
                f"Unrecognized mode: {mode}")

        self.rx_ch = rx_channel
        self.rx_analyzer = rx_analyzer

    def run(self):
        """Main task loop"""
        while self.task_state != TASK_STATE["STOP"]:
            if self.task_state == TASK_STATE["RUNNING"]:
                time.sleep(1)
                # DMA transfer
                self.rx_ch.transfer()
                wave_rx = self.rx_ch.data
                self.rx_analyzer.proc_rx(wave_rx)
            else:
                time.sleep(1)
