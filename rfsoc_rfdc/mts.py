import time
import logging


class MyMTS:

    def __init__(self, rfdc_ip, overlay, debug=False):
        self.rfdc = rfdc_ip
        self.mts_monitor = overlay.MTS_block.MTS_clk_wiz
        self.debug = debug
        self.CLOCKWIZARD_LOCK_ADDRESS = 0x0004
        self.CLOCKWIZARD_RESET_ADDRESS = 0x0000
        self.CLOCKWIZARD_RESET_TOKEN = 0x000A
        self.ACTIVE_DAC_TILES = 0b1111
        self.ACTIVE_ADC_TILES = 0b1111
        # MTS related
        self.mts_latency_min = 16
        self.mts_latency_margin = 16

    def debug_info(self):
        """Print debug information"""
        mts_attr = ['RefTile', 'Tiles', 'Target_Latency',
                    'Offset', 'Latency', 'Marker_Delay', 'SysRef_Enable']

        for attr in mts_attr:
            val = getattr(self.rfdc.mts_dac_config, attr, None)
            if attr == "Offset" or attr == "Latency":
                for i in range(4):
                    logging.info(
                        f"DAC MTS {attr} Tile[{i}] : {val[i]}")
            else:
                logging.info(
                    f"DAC MTS {attr} : {val}")

        for attr in mts_attr:
            val = getattr(self.rfdc.mts_adc_config, attr, None)
            if attr == "Offset" or attr == "Latency":
                for i in range(4):
                    logging.info(
                        f"ADC MTS {attr} Tile[{i}] : {val[i]}")
            else:
                logging.info(
                    f"ADC MTS {attr} : {val}")

    def init(self):
        """Initialize MTS"""
        try:
            self.init_tile_sync()
        except ValueError as e:
            logging.warning(f"{e}")

        if self.debug:
            self.debug_info()
        # Verify PL_CLK and PL_SYSREF are synced
        self.verify_clock_tree()
        # Actually sync tiles with measured latency
        latency = self.mts_latency_margin + 144  # from experiment
        self.sync_tiles()
        # TODO: Figure out how to set target latency for DACs and ADCs
        # self.sync_tiles(dac_target_latency=latency, adc_target_latency=latency)

    def sync_tiles(self, dac_target_latency=-1, adc_target_latency=-1):
        """ Configures RFSoC MTS alignment"""
        latency_min = self.mts_latency_min
        if dac_target_latency < latency_min and dac_target_latency != -1:
            raise RuntimeError(
                f"DAC target latency {dac_target_latency} shall be >= than {latency_min}.")
        if adc_target_latency < latency_min and adc_target_latency != -1:
            raise RuntimeError(
                f"ADC target latency {dac_target_latency} shall be >= than {latency_min}.")

        # Set which RF tiles use MTS and turn MTS off
        if self.ACTIVE_DAC_TILES > 0:
            self.rfdc.mts_dac_config.Tiles = self.ACTIVE_DAC_TILES
            self.rfdc.mts_dac_config.SysRef_Enable = 1
            self.rfdc.mts_dac_config.Target_Latency = dac_target_latency
            self.rfdc.mts_dac()
        else:
            self.rfdc.mts_dac_config.Tiles = 0x0
            self.rfdc.mts_dac_config.SysRef_Enable = 0

        if self.ACTIVE_ADC_TILES > 0:
            self.rfdc.mts_adc_config.Tiles = self.ACTIVE_ADC_TILES
            self.rfdc.mts_adc_config.SysRef_Enable = 1
            self.rfdc.mts_adc_config.Target_Latency = adc_target_latency
            self.rfdc.mts_adc()
        else:
            self.rfdc.mts_adc_config.Tiles = 0x0
            self.rfdc.mts_adc_config.SysRef_Enable = 0

    def init_tile_sync(self):
        """Resets the MTS alignment engine"""
        # Turn only one tile on first sync
        self.rfdc.mts_dac_config.Tiles = 0b0001
        self.rfdc.mts_adc_config.Tiles = 0b0001
        self.rfdc.mts_dac_config.SysRef_Enable = 1
        self.rfdc.mts_adc_config.SysRef_Enable = 1
        self.rfdc.mts_dac_config.Target_Latency = -1
        self.rfdc.mts_adc_config.Target_Latency = -1
        self.rfdc.mts_dac()
        self.rfdc.mts_adc()
        time.sleep(0.1)

        # Reset MTS ClockWizard MMCM - refer to PG065
        self.mts_monitor.mmio.write_reg(
            self.CLOCKWIZARD_RESET_ADDRESS, self.CLOCKWIZARD_RESET_TOKEN)
        time.sleep(0.1)
        # Reset only user selected DAC tiles
        bitvector = self.ACTIVE_DAC_TILES
        for n in range(4):
            if (bitvector & 0x1):
                self.rfdc.dac_tiles[n].Reset()
            bitvector = bitvector >> 1
        # Reset ADC FIFO of only user selected tiles - restarts MTS engine
        for toggleValue in range(0, 1):
            bitvector = self.ACTIVE_ADC_TILES
            for n in range(4):
                if (bitvector & 0x1):
                    self.rfdc.adc_tiles[n].SetupFIFOBoth(toggleValue)
                bitvector = bitvector >> 1

    def verify_clock_tree(self):
        """ Verify the PL and PL_SYSREF clocks are active by verifying an MMCM is in the LOCKED state"""
        lock_status = self.mts_monitor.mmio.read(
            self.CLOCKWIZARD_LOCK_ADDRESS)  # reads the LOCK register
        # the ClockWizard AXILite registers are NOT fully mapped: refer to PG065
        if (lock_status != 1):
            raise Exception(
                "The MTS clock has failed to LOCK. Please verify MTS configuration")
        else:
            logging.info(f"The MTS clock is LOCK on successfully")
