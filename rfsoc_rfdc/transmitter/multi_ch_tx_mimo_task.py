from rfsoc_rfdc.overlay_task import TASK_STATE

from rfsoc_rfdc.transmitter.multi_ch_tx_task import MultiChTxTask
from rfsoc_rfdc.overlay_task import TASK_STATE
import time
from rfsoc_rfdc.waveform_generator import WaveFormGenerator as wg
from scipy.io import loadmat

import numpy as np
from rfsoc_rfdc.transmitter.tx_data_generator import TxDataGenerator

from rfsoc_rfdc.iq_loader import IqLoader
from rfsoc_rfdc.rfdc import MyRFdcType
from rfsoc_rfdc.rfdc_config import ZCU216_CONFIG
import logging


class MultiChTxMIMOTask(MultiChTxTask):

    def __init__(self, overlay, mode="iq2real", channel_count=4, dp_vect_dim=1):
        super().__init__(overlay, mode, channel_count, dp_vect_dim)

    def data_preparation(self):
        if self.mode == "iq2real":
            detection_scheme = ZCU216_CONFIG["DETECTION_SCHEME"]
            try:
                packetTx = loadmat(detection_scheme.txFile)[
                    detection_scheme.txMatVarKey].T
            except:
                raise (
                    f"Failed to load Tx waveform from {detection_scheme.txFile}")
            logging.info(
                f"Tx waveform {detection_scheme.txFile} loaded successfully.")

            # OFDM symbol attenuation
            db2amp = 0.5/(10**(ZCU216_CONFIG["OFDM_ATTEN_DB"]/20))
            for ch in range(self.channel_count):
                # Scale to int16
                packetTx[ch] = packetTx[ch, :] / \
                    np.std(packetTx[ch, :]) * db2amp

            # Add preamble
            waveTx = detection_scheme.proc_tx(packetTx)

            # Convert to int16
            real_max, imag_max = np.max(
                np.abs(np.real(waveTx))), np.max(np.abs(np.imag(waveTx)))
            raw_max = max(real_max, imag_max)
            scaling = MyRFdcType.DAC_MAX_SCALE / raw_max

            for ch in range(self.channel_count):
                # Scale to int16
                waveTx[ch] = waveTx[ch, :] * scaling
        else:
            raise RuntimeError(f"Unrecognized mode {self.mode}")
        # Generate multi-channel memory layout
        mch_data = self.mch_mem_layout.gen_layout(waveTx)
        # Convert to np.int16
        mch_data = mch_data.astype(np.int16)
        # Perform data copy
        self.tx_ch.data_copy(mch_data)
        logging.info(f"Tx data preparation done.")

    def run(self):
        self.data_preparation()
        # MIMO Processing
        while self.task_state != TASK_STATE["STOP"]:
            if self.task_state == TASK_STATE["RUNNING"]:
                # Streaming IQ samples
                self.tx_ch.stream(duty_cycle=100)
                time.sleep(1)
            else:
                self.tx_ch.tx_dma.stop()
                time.sleep(1)
