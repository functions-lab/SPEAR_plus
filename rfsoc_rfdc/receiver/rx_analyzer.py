from rfsoc_rfdc.plotter.signal_plotter import ComplexSignalPlotter, RealSignalPlotter
from rfsoc_rfdc.plotter.fft_plotter import FFTPlotter
from rfsoc_rfdc.rfdc_config import ZCU216_CONFIG
import numpy as np
import logging
import pickle
import socket
import time
import threading
from rfsoc_rfdc.dsp.mimo_detection import MIMODetection

from abc import ABC, abstractmethod


def save_to_file(data, filename):
    np.save(filename, data)


class BaseAnalyzer:

    def __init__(self, channel_id):
        self.channel_id = channel_id

    @abstractmethod
    def io_logging_thd(self, data):
        pass

    @abstractmethod
    def plot_thd(self, data):
        pass


class TimeDomainAnalyzer(BaseAnalyzer):
    """Visualize and save raw waveform data"""

    def __init__(self, channel_id, path2wave="../wave_files", mode="real2iq"):
        super().__init__(channel_id)
        self.path2wave = path2wave
        if mode == "real2iq":
            self.time_domain_plotter = ComplexSignalPlotter(
                title=f"TimeDomainAnalyzer (IQ) (Channel {channel_id})")
        elif mode == "real2real":
            self.time_domain_plotter = RealSignalPlotter(
                title=f"TimeDomainAnalyzer (Channel {channel_id})")
        else:
            raise RuntimeError(f"Unrecognize mode {mode}")

    def io_logging_thd(self, data):
        thd = threading.Thread(target=save_to_file, args=(
            data, f"{self.path2wave}/Rx{self.channel_id}_raw.npy"))
        return thd

    def plot_thd(self, data):
        thd = threading.Thread(
            target=self.time_domain_plotter.update_plot, args=(data, 0.1))
        return thd


class TimeDomainPacketAnalyzer(BaseAnalyzer):
    """Analyzer for time-domain packet analysis (assumed real2iq mode)"""

    def __init__(self, channel_id, path2wave="../wave_files"):
        super().__init__(channel_id)
        self.path2wave = path2wave
        self.time_pkt_plotter = ComplexSignalPlotter(
            title=f"TimeDomainPacketAnalyzer (Channel {channel_id})")

    def io_logging_thd(self, pkt_iq_data):
        thd = threading.Thread(target=save_to_file, args=(
            pkt_iq_data, f"{self.path2wave}/Rx_pkt.npy"))
        return thd

    def plot_thd(self, pkt_iq_data):
        thd = threading.Thread(
            target=self.time_pkt_plotter.update_plot, args=(pkt_iq_data, 0.5))
        return thd


class FreqDomainPacketAnalyzer(BaseAnalyzer):
    """Analyzer for frequency-domain packet analysis"""

    def __init__(self, channel_id, mode="real2iq"):
        super().__init__(channel_id)
        dac_samp_rate = ZCU216_CONFIG['DACSampleRate'] / \
            ZCU216_CONFIG['DACInterpolationRate'] * 1e6
        self.fft_pkt_plotter = FFTPlotter(
            sample_rate=dac_samp_rate,
            title=f"FreqDomainPacketAnalyzer (Channel {channel_id})")

    def io_logging_thd(self, pkt_iq_data):
        pass

    def plot_thd(self, pkt_iq_data):
        thd = threading.Thread(
            target=self.fft_pkt_plotter.update_plot, args=(pkt_iq_data,))
        return thd


class OFDMAnalyzer(BaseAnalyzer):
    """Analyzer for OFDM-specific processing (assume real2iq mode)"""

    def __init__(self, channel_id, ofdm_scheme, detect_scheme):
        super().__init__(channel_id)
        self.ofdm_scheme = ofdm_scheme
        self.detect_scheme = detect_scheme

    def io_logging_thd(self, raw_iq):
        pass

    def plot_thd(self, raw_iq):
        thd = threading.Thread(
            target=self.detect_scheme.update_plot, args=(raw_iq,))
        return thd

    def analyze_packet(self, raw_iq):
        """Perform packet detection and OFDM analysis"""
        try:
            rx_packet, snr, cfo = self.detect_scheme.proc_rx(raw_iq)
        except Exception:
            raise RuntimeError("Failed to detect Rx packet")

        config_name = ZCU216_CONFIG['CONFIG_NAME']
        evm, ber = self.ofdm_scheme.analyze(
            rx_packet,
            plot_fname=f"{self.detect_scheme.path2wave}/{config_name}_CH{self.channel_id}_const_diagram.png",
            constel_data_fname=None,
            constel_map_fname=None
        )

        with open(f"{self.detect_scheme.path2wave}/{config_name}_CH{self.channel_id}_res.log", 'w') as f:
            f.write(f"{snr:.3f}, {cfo:.3f}, {evm:.3f}, {ber:.10f}")

        return rx_packet, snr, cfo, evm, ber


class TCPAnalyzer(BaseAnalyzer):
    """Analyzer for TCP network operations"""

    def __init__(self, channel_id, server_config=("server.local", 1234), mode="real2iq"):
        super().__init__(channel_id)
        self.server_config = server_config
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.mode = mode

    def tcp_reconnect(self):
        """Attempt to reconnect TCP socket"""
        new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        new_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            new_sock.connect(self.server_config)
        except socket.error:
            return None
        return new_sock

    def io_logging_thd(self, raw_iq):
        """Send samples over TCP connection"""
        if self.mode == "real2iq":
            samples = np.array(raw_iq, dtype=np.csingle)
        else:
            samples = np.array(raw_iq, dtype=np.float32)

        try:
            byte_data = pickle.dumps(samples)
            self.sock.sendall(byte_data)
        except socket.error:
            for _ in range(5):
                s = self.tcp_reconnect()
                if s is not None:
                    self.sock = s
                    break

    def plot_thd(self, raw_iq):
        pass

    def __del__(self):
        """Clean up network resources"""
        self.sock.close()


class RxAnalyzer:
    """Base class for common analyzer functionality"""

    def __init__(self, channel_id, server_config=("server.local", 1234)):
        self.thd_list = []
        self.channel_id = channel_id
        self.tcp_analyzer = TCPAnalyzer(
            channel_id=self.channel_id, server_config=server_config)

    def _run_thds(self):
        """Common thread processing"""
        for thd in self.thd_list:
            thd.start()
        for thd in self.thd_list:
            thd.join()
        self.thd_list.clear()

    @abstractmethod
    def proc_rx(self, data):
        pass


class Real2IqRxAnalyzer(RxAnalyzer):
    """Analyzer for Real to IQ conversion"""

    def __init__(self, ofdm_scheme, detect_scheme, channel_id, server_config=("server.local", 1234)):
        super().__init__(channel_id, server_config)
        self.waveform_analyzer = TimeDomainAnalyzer(
            channel_id, detect_scheme.path2wave, mode="real2iq")
        self.time_analyzer = TimeDomainPacketAnalyzer(
            channel_id, detect_scheme.path2wave)
        self.freq_analyzer = FreqDomainPacketAnalyzer(channel_id)
        self.ofdm_analyzer = OFDMAnalyzer(channel_id,
                                          ofdm_scheme, detect_scheme)

    def proc_rx(self, data):
        self.thd_list.append(self.waveform_analyzer.plot_thd(data))
        self.thd_list.append(self.waveform_analyzer.io_logging_thd(data))
        raw_iq = data
        self._run_thds()

        try:
            rx_packet, snr, cfo, evm, ber = self.ofdm_analyzer.analyze_packet(
                raw_iq)
        except:
            logging.warning(
                f"Rx #{self.channel_id} Failed to decode Rx packet.")
            return

        self.thd_list.append(self.time_analyzer.plot_thd(rx_packet))
        self.thd_list.append(self.time_analyzer.io_logging_thd(rx_packet))
        self.thd_list.append(self.freq_analyzer.plot_thd(rx_packet))

        logging.info(
            f"Rx #{self.channel_id} SNR: {snr:.3f}, CFO: {cfo:.3f}, EVM: {evm:.3f}, BER: {ber:.10f}")

        self._run_thds()


class RxMIMOAnalyzer(RxAnalyzer):
    """Analyzer for Rx MIMO Channel"""

    def __init__(self, detection_scheme, tx_ant, rx_ant, server_config=("server.local", 1234)):
        super().__init__(channel_id=-1, server_config=server_config)
        # TODO: Properly handle tx_ant and rx_ant
        self.channel_count = tx_ant
        self.time_analyer_list = [TimeDomainAnalyzer(channel_id=id,
                                                     path2wave="./wave_files",
                                                     mode="real2iq")
                                  for id in range(self.channel_count)]
        self.mimo_detection = detection_scheme

    def detect(self, wave_rx):
        """Perform multi-channel packet detection"""
        rx_packet_list, snr_list, cfo_list = self.mimo_detection.proc_rx(
            wave_rx)

        return rx_packet_list, snr_list, cfo_list

    def proc_rx(self, iq_data):
        """Only update plot. No DSP is performed"""
        for id in range(self.channel_count):
            self.thd_list.append(
                self.time_analyer_list[id].plot_thd(iq_data[id]))
            # self.thd_list.append(self.time_analyer_list[id].io_logging_thd(mch_data[id]))

        self._run_thds()

        logging.info(f"Rx samples captured.")


class Real2RealRxAnalyzer(RxAnalyzer):
    """Analyzer for Real to Real conversion"""

    def __init__(self, channel_id, server_config=("server.local", 1234)):
        super().__init__(channel_id, server_config)
        # Initialize real analyzer
        self.waveform_analyzer = TimeDomainAnalyzer(
            self.channel_id, mode="real2real")

    def proc_rx(self, data):
        self.thd_list.append(self.waveform_analyzer.plot_thd(data))
        self.thd_list.append(self.waveform_analyzer.io_logging_thd(data))

        self._run_thds()
