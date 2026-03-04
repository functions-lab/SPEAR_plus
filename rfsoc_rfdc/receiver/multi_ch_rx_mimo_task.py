import concurrent.futures
from rfsoc_rfdc.overlay_task import TASK_STATE
import time
import logging
from rfsoc_rfdc.rfdc_config import ZCU216_CONFIG
from rfsoc_rfdc.receiver.multi_ch_rx_task import MultiChRxTask
import numpy as np
from rfsoc_rfdc.receiver.rx_analyzer import RxMIMOAnalyzer
from scipy.io import loadmat, savemat


class MultiChRxMIMOTask(MultiChRxTask):
    """Multi-Channel Rx MIMO Task"""

    def __init__(self, overlay, mode="real2iq", channel_count=4, dp_vect_dim=1):
        super().__init__(overlay, mode, channel_count, dp_vect_dim)
        self.rx_analyzer = RxMIMOAnalyzer(
            detection_scheme=ZCU216_CONFIG["DETECTION_SCHEME"],
            tx_ant=channel_count,
            rx_ant=channel_count)

    def run(self):
        # Rx init
        self._channel_factory()
        """Main task loop"""
        while self.task_state != TASK_STATE["STOP"]:
            if self.task_state == TASK_STATE["RUNNING"]:
                # DMA transfer
                self.rx_ch.transfer()  # Additional DMA transfer that clears out remainings in FIFO
                self.rx_ch.transfer()

                raw_mch_data = self.rx_ch.data
                mch_complex_arr = self._layout_factory(raw_mch_data)
                # Plot captured samples
                self.rx_analyzer.proc_rx(mch_complex_arr)
                # Detection
                rx_packet_list, snr_list, cfo_list = self.rx_analyzer.detect(
                    mch_complex_arr)

                if np.isnan(snr_list).any():
                    logging.warning(f"Rx detection failed.")
                    continue

                for ch in range(self.channel_count):
                    logging.info(
                        f"Rx #CH{ch} SNR: {snr_list[ch]:.3f}, CFO: {cfo_list[ch]:.3f}")
                waveFile = "./" + \
                    ZCU216_CONFIG["CONFIG_NAME"] + "_" + \
                    self.rx_analyzer.mimo_detection.rxFile
                waveKey = self.rx_analyzer.mimo_detection.rxMatVarKey
                savemat(waveFile, {waveKey: rx_packet_list.T})
            else:
                time.sleep(1)
