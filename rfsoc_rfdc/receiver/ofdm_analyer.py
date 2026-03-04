from rfsoc_rfdc.plotter.signal_plotter import ComplexSignalPlotter
from rfsoc_rfdc.plotter.fft_plotter import FFTPlotter
from rfsoc_rfdc.rfdc_config import ZCU216_CONFIG
import numpy as np
import logging
import pickle
import socket
import time
import threading


class OFDMAnalyzer:

    def __init__(self, ofdm_scheme, detect_scheme, server_config=("server.local", 1234)):
        """Initialize RxAnalyzer with processing schemes and network configuration"""
        # Processing schemes
        self.ofdm_scheme = ofdm_scheme
        self.detect_scheme = detect_scheme

        self.time_wv_plotter = ComplexSignalPlotter(
            title="Waveform Plotter (Time)")

        # Initialize plotters
        self.time_pkt_plotter = ComplexSignalPlotter(
            title="Packet Plotter (Time)")
        dac_samp_rate = ZCU216_CONFIG['DACSampleRate'] / \
            ZCU216_CONFIG['DACInterpolationRate'] * 1e6
        self.fft_pkt_plotter = FFTPlotter(sample_rate=dac_samp_rate)

        # TCP socket setup
        self.server_config = server_config
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def __del__(self):
        """Clean up network resources"""
        self.sock.close()

    def data_logging_handler(self, iq_data, file_name):
        """Save IQ data to file"""
        np.save(file_name, iq_data)

    def tcp_reconnect(self, net_config):
        """Attempt to reconnect TCP socket"""
        new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        new_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            new_sock.connect(net_config)
        except socket.error:
            return None
        return new_sock

    def tcp_pkt_handler(self, samples):
        """Send samples over TCP connection"""
        samples = np.array(samples, dtype=np.csingle)
        try:
            byte_data = pickle.dumps(samples)
            self.sock.sendall(byte_data)
        except socket.error:
            for _ in range(5):
                s = self.tcp_reconnect(self.server_config)
                if s is not None:
                    self.sock = s
                    break

    def process_packet(self, pkt_iq_data):
        """Process and visualize packet data"""
        start_t = time.time_ns()

        thd_list = []
        # Time plot thread
        thd_list.append(threading.Thread(
            target=self.time_pkt_plotter.update_plot,
            args=(pkt_iq_data, 0.5)))
        # FFT plot thread
        thd_list.append(threading.Thread(
            target=self.fft_pkt_plotter.update_plot,
            args=(pkt_iq_data,)))
        # Save captured packet thread
        thd_list.append(threading.Thread(
            target=self.data_logging_handler,
            args=(pkt_iq_data, self.detect_scheme.rx_file)))
        # TCP samples thread (commented out by default)
        # thd_list.append(threading.Thread(
        #     target=self.tcp_pkt_handler,
        #     args=(pkt_iq_data,)))

        for thd in thd_list:
            thd.start()
        for thd in thd_list:
            thd.join()

        elapse = time.time_ns() - start_t
        # logging.info(f"packet handler takes {elapse / 1e9} to complete")

    def process_waveform(self, wave_iq_data):
        """Process and visualize waveform data"""
        start_t = time.time_ns()

        thd_list = []
        # Time plot thread
        thd_list.append(threading.Thread(
            target=self.time_wv_plotter.update_plot,
            args=(wave_iq_data, 0.1)))
        # Save captured waveform thread
        thd_list.append(threading.Thread(
            target=self.data_logging_handler,
            args=(wave_iq_data, self.detect_scheme.path2wave + "/Rx_raw.npy")))

        for thd in thd_list:
            thd.start()
        for thd in thd_list:
            thd.join()

        elapse = time.time_ns() - start_t
        # logging.info(f"wave rx handler takes {elapse / 1e9} to complete")

    def analyze_packet(self, wave_rx):
        """Perform packet detection and analysis"""

        try:
            packet_rx, snr, cfo = self.detect_scheme.proc_rx(wave_rx)
        except Exception:
            logging.error("Failed to detect Rx packet")
            return None

        config_name = ZCU216_CONFIG['CONFIG_NAME']
        evm, ber = self.ofdm_scheme.analyze(
            packet_rx,
            plot_fname=f"{self.detect_scheme.path2wave}/{config_name}_const_diagram.png",
            constel_data_fname=None,
            constel_map_fname=None
        )

        # Log results
        logging.info(
            f"SNR: {snr:.3f}, CFO: {cfo:.3f}, EVM: {evm:.3f}, BER: {ber:.10f}")

        # Write results to file
        with open(f"{self.detect_scheme.path2wave}/{config_name}_res.log", 'w') as f:
            f.write(f"{snr:.3f}, {cfo:.3f}, {evm:.3f}, {ber:.10f}")

        return packet_rx, snr, cfo, evm, ber
