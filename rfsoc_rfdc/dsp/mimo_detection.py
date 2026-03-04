import matplotlib.pyplot as plt
import numpy as np
import os
import shutil
from scipy.io import loadmat, savemat

from rfsoc_rfdc.dsp.ofdm import OFDM
from rfsoc_rfdc.rfdc_config import ZCU216_CONFIG
from rfsoc_rfdc.dsp.detection import Detection


class MIMODetection(Detection):

    def __init__(self, sample_rate=1e9, tx_num=2, rx_num=2, MCS=0):
        super().__init__(sample_rate=sample_rate)
        # Initialize with dimension
        self.zadoffSet = [139, 839]  # ascent
        self.sampleRate = sample_rate
        self.MCS = MCS
        # Tx/Rx MIMO dimension
        self.txNum = tx_num  # np.shape(packetTxList)[0]
        self.rxNum = rx_num
        # Tx/Rx file name
        self.txFile = f"waveTx_{self.txNum}_{self.MCS}.mat"
        self.rxFile = f"waveRx_{self.rxNum}_{self.MCS}.mat"
        # Preamble config
        self.headLen = sum(self.zadoffSet)*3
        self.padLen = None
        self.waveLen = None
        self.packetLen = None  # np.shape(packetTxList)[1]

    def proc_tx(self, packetTxList):
        # Update vars
        self.packetLen = np.shape(packetTxList)[1]
        self.padLen = round(0.2*self.packetLen)

        txNum = self.txNum
        zadoffSet = self.zadoffSet
        padLen = self.padLen

        waveTxList = []
        for txIdx in range(txNum):
            self._check_saturation(packetTxList[txIdx, :])

        headTx = np.zeros((sum(zadoffSet)*3), dtype=np.complex64)
        offset = 0
        for zadoffLen in zadoffSet:
            zadoffSingle = np.exp(1j*2*np.pi*np.random.rand(1, zadoffLen))
            zadoffDouble = np.tile(zadoffSingle, 2)
            headTx[offset: offset+2*zadoffLen] = zadoffDouble
            offset += 3 * zadoffLen

        padTx = np.zeros((padLen))

        for txIdx in range(txNum):
            packetTx = packetTxList[txIdx, :]
            waveTx = np.concatenate((padTx, headTx, packetTx, padTx), axis=0)
            waveTxList.append(waveTx)

        return np.vstack(waveTxList)

    def proc_rx(self, wave_rx):
        """Detect preamble and extract packets from multiple Rx channels"""
        capNum = 3
        noiseNum = 1000

        waveLen = 2*self.padLen + self.headLen + self.packetLen
        rxNum = self.rxNum
        packetLen = self.packetLen
        sampleRate = self.sampleRate
        zadoffSet = self.zadoffSet
        headLen = self.headLen

        waveRxList = np.zeros((rxNum, capNum*waveLen), dtype=complex)
        offsetZadoffList = np.zeros((rxNum), dtype=int)
        offsetPacketList = np.zeros((rxNum), dtype=int)

        for rxIdx in range(rxNum):
            waveTemp = wave_rx[rxIdx, :]
            waveRx = waveTemp[-capNum*waveLen:]

            # fig, ax = plt.subplots()
            # ax.plot(np.arange(capNum*waveLen), 20*np.log10(np.abs(waveRx)+1e-10))
            # ax.set_ylim(bottom=-100, top=0)
            # fig.savefig('./detection_'+str(rxIdx)+'.png')
            # plt.close(fig)

            offsetList, corrList = self._zadoff_detection(
                waveRx[: waveLen], zadoffSet[-1], zadoffSet[-1], 0.7)
            offsetListAfter, _ = self._zadoff_detection(
                waveRx[waveLen: 2*waveLen], zadoffSet[-1], zadoffSet[-1], 0.7)
            if (len(offsetList) == 0) or (len(offsetListAfter) == 0):
                break
            offsetIdx = np.argmax(np.array(corrList))
            offsetZadoff = offsetList[offsetIdx]-3*sum(zadoffSet[: -1])
            offsetPacket = offsetZadoff + headLen
            if offsetZadoff <= 0:
                break

            waveRxList[rxIdx, :] = waveRx
            offsetZadoffList[rxIdx] = offsetZadoff
            offsetPacketList[rxIdx] = offsetPacket

        packetRxList = np.zeros((rxNum, packetLen), dtype=complex)

        snrList = np.ones((rxNum)) * np.nan
        cfoList = np.ones((rxNum)) * np.nan

        for rxIdx in range(rxNum):
            waveRx = waveRxList[rxIdx, :]
            offsetZadoff = offsetZadoffList[rxIdx]
            offsetPacket = offsetPacketList[rxIdx]

            cfoSet = []
            offset = offsetZadoff
            for zadoffLen in zadoffSet:
                zadoff_1 = waveRx[offset: offset+zadoffLen]
                zadoff_2 = waveRx[offset+zadoffLen: offset+2*zadoffLen]
                cfoTemp = -sampleRate/zadoffLen * \
                    np.angle(np.sum(zadoff_1 * np.conj(zadoff_2)))/2/np.pi
                cfoSet.append(cfoTemp)
                offset += 3*zadoffLen

                waveRx[offsetZadoff: offsetZadoff+headLen] = \
                    waveRx[offsetZadoff: offsetZadoff+headLen] * \
                    np.exp(-1j*2*np.pi*np.arange(headLen)/sampleRate*cfoTemp)

            cfo = 0  # This line turn off CFO
            # cfo = sum(cfoSet)
            packetRx = waveRx[offsetPacket: offsetPacket+packetLen]
            packetRx = packetRx * \
                np.exp(-1j*2*np.pi*np.arange(packetLen)/sampleRate*cfo)

            noiseList = []
            for noiseIdx in range(noiseNum):
                startIdx = round(capNum*waveLen/noiseNum*noiseIdx)
                endIdx = round(capNum*waveLen/noiseNum*noiseIdx) + \
                    int(np.ceil(100))
                noiseSym = waveRx[startIdx: endIdx]
                noise = self._get_energy(noiseSym)
                noiseList.append(noise)
            noise = np.percentile(noiseList, 10)
            signal = self._get_energy(packetRx) - noise
            snr = 10 * np.log10(signal/noise)

            # Detection plot
            plt.ioff()
            fig, ax = plt.subplots()
            ax.plot(np.arange(capNum*waveLen), 20 *
                    np.log10(np.abs(waveRx)+1e-10))
            ax.vlines(offsetZadoff, ymin=-1e10, ymax=+1e10)
            ax.vlines(offsetPacket, ymin=-1e10, ymax=+1e10)
            ax.vlines(offsetPacket+packetLen, ymin=--1e10, ymax=+1e10)
            ax.set_ylim(bottom=0, top=100)
            ax.set_title(f"CH #{rxIdx} SNR: {snr:.2f}dB CFO: {cfo:.2f}Hz")
            fprefix = ZCU216_CONFIG['CONFIG_NAME']+f"_CH{rxIdx}_MCS{self.MCS}"
            detection_file = os.path.join(
                self.path2wave, fprefix+"_detection.png")
            fig.savefig(detection_file)
            plt.close(fig)

            # Detection log
            with open(os.path.join(self.path2wave, fprefix+"_res.log"), 'w') as f:
                f.write(f"{snr:.3f}, {cfo:.3f}")

            packetRxList[rxIdx, :] = packetRx
            snrList[rxIdx] = snr
            cfoList[rxIdx] = cfo

        return packetRxList, snrList, cfoList
