import concurrent.futures
from rfsoc_rfdc.overlay_task import TASK_STATE
import time
import logging
from rfsoc_rfdc.rfdc_config import ZCU216_CONFIG
from rfsoc_rfdc.receiver.multi_ch_rx_task import MultiChRxTask

from rfsoc_rfdc.receiver.rx_analyzer import Real2IqRxAnalyzer, Real2RealRxAnalyzer


class MultiChRxIndeptTask(MultiChRxTask):
    """Multi-Channel Rx Independent Task"""

    def __init__(self, overlay, mode="real2iq", channel_count=4, dp_vect_dim=1):
        super().__init__(overlay, mode, channel_count, dp_vect_dim)

    def _channel_factory(self):
        super()._channel_factory()

        if self.mode == "real2iq":
            self.rx_analyzers = [Real2IqRxAnalyzer(channel_id=id, ofdm_scheme=ZCU216_CONFIG['OFDM_SCHEME'],
                                                   detect_scheme=ZCU216_CONFIG['DETECTION_SCHEME']) for id in range(self.channel_count)]
        elif self.mode == "real2real":
            self.rx_analyzers = [Real2RealRxAnalyzer(channel_id=id)
                                 for id in range(self.channel_count)]
        else:
            raise RuntimeError(f"Unrecognized mode {self.mode}")

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

                ch = 0
                self.rx_analyzers[ch].proc_rx(mch_complex_arr[ch])

                # with concurrent.futures.ThreadPoolExecutor(max_workers=self.channel_count) as executor:
                #     futures = []
                #     for ch in range(self.channel_count):
                #         futures.append(executor.submit(
                #             self.rx_analyzers[ch].proc_rx, mch_complex_arr[ch]))
                #     # Wait for all threads to complete
                #     concurrent.futures.wait(futures)
                logging.info(f"--------------------")
            else:
                time.sleep(1)
