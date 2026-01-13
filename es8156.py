# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
CircuitPython driver for the ES8156 I2S DAC
"""

from adafruit_bus_device.i2c_device import I2CDevice
from adafruit_register.i2c_struct import UnaryStruct
from adafruit_register.i2c_bit import RWBit
from micropython import const

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/yourrepo/CircuitPython_ES8156.git"


# Register addresses (Page 0)
_RESET_CONTROL = const(0x00)
_MAIN_CLOCK_CONTROL = const(0x01)
_MODE_CONFIG_1 = const(0x02)
_MISC_CONTROL_1 = const(0x07)
_CLOCK_OFF = const(0x08)
_MISC_CONTROL_2 = const(0x09)
_TIME_CONTROL_1 = const(0x0A)
_TIME_CONTROL_2 = const(0x0B)
_CHIP_STATUS = const(0x0C)
_P2S_CONTROL = const(0x0D)
_SDP_INTERFACE_CONFIG_1 = const(0x11)
_MUTE_CONTROL = const(0x13)
_VOLUME_CONTROL = const(0x14)
_MISC_CONTROL_3 = const(0x18)
_ANALOG_SYSTEM_1 = const(0x20)
_ANALOG_SYSTEM_2 = const(0x21)
_ANALOG_SYSTEM_3 = const(0x22)
_ANALOG_SYSTEM_4 = const(0x23)
_ANALOG_SYSTEM_5 = const(0x24)
_ANALOG_SYSTEM_6 = const(0x25)
_PAGE_SELECT = const(0xFC)
_CHIP_ID1 = const(0xFD)
_CHIP_ID0 = const(0xFE)
_CHIP_VERSION = const(0xFF)

# Chip ID
_CHIP_ID = const(0x8155)


class ES8156:
    """
    Driver for the ES8156 I2S DAC.
    """
    
    # Page Select Register
    _page_select = RWBit(_PAGE_SELECT, 0, register_width=1)
    
    # Volume Control Register (0x14)
    volume = UnaryStruct(_VOLUME_CONTROL, "B")
    """Volume level (0-255, where 0 is mute and 255 is maximum)"""
    
    # Mute Control Register (0x13)
    left_mute = RWBit(_MUTE_CONTROL, 1, register_width=1)
    
    right_mute = RWBit(_MUTE_CONTROL, 2, register_width=1)

    _out_mute_bit = RWBit(_ANALOG_SYSTEM_3, 0, register_width=1)
    
    def __init__(self, i2c_bus, address=0x08):
        """Initialize the ES8156 DAC.
        
        :param ~busio.I2C i2c_bus: The I2C bus the device is connected to
        :param int address: The I2C device address (default: 0x08)
        """
        self.i2c_device = I2CDevice(i2c_bus, address)
        self._current_page = 0
        
        # Verify chip ID
        if self.chip_id != _CHIP_ID:
            raise RuntimeError(f"Failed to find ES8156! Chip ID: 0x{self.chip_id:04X}")
    
    def _select_page(self, page):
        if self._current_page != page:
            self._page_select = page
            self._current_page = page
    
    def _write_register(self, reg, value):
        """Write a single register."""
        with self.i2c_device as i2c:
            i2c.write(bytes([reg, value]))
    
    def _read_register(self, reg):
        """Read a single register."""
        buf = bytearray(1)
        with self.i2c_device as i2c:
            i2c.write_then_readinto(bytes([reg]), buf)
        return buf[0]

    @property
    def chip_id(self):
        """Chip ID."""
        self._select_page(0)
        buf1 = bytearray(1)
        buf0 = bytearray(1)
        with self.i2c_device as i2c:
            i2c.write_then_readinto(bytes([_CHIP_ID1]), buf1)
            i2c.write_then_readinto(bytes([_CHIP_ID0]), buf0)
        return (buf1[0] << 8) | buf0[0]
    
    @property
    def chip_version(self):
        """Chip version."""
        self._select_page(0)
        buf = bytearray(1)
        with self.i2c_device as i2c:
            i2c.write_then_readinto(bytes([_CHIP_VERSION]), buf)
        return (buf[0] >> 4) & 0x0F
    
    @property
    def mute(self):
        """Mute state for all outputs (True = muted, False = unmuted)"""
        return self.left_mute or self.right_mute or self._out_mute_bit
    
    @mute.setter
    def mute(self, value):
        self.left_mute = value
        self.right_mute = value
        self._out_mute_bit = value
    
    def configure(self, use_sclk_as_mclk=True):
        """Configure the ES8156 with default settings for I2S peripheral mode.
        
        :param bool use_sclk_as_mclk: Use SCLK as main clock source (default: True)
        
        This configures the ES8156 for:
        - I2S peripheral mode
        - 16-bit audio
        - Internal clock generation from SCLK (if use_sclk_as_mclk=True)
        - All analog outputs powered up and unmuted
        """
        self._select_page(0)
        
        # Reset: CSM_ON=0, SEQ_DIS=1
        self._write_register(0x00, 0b00000010)
        
        # Mode Config: Enable software mode, configure clock source
        if use_sclk_as_mclk:
            # MCLK_SEL=1, ISCLKLRCK_SEL=1, SOFT_MODE_SEL=1
            self._write_register(0x02, 0b11000100)
        else:
            # SOFT_MODE_SEL=1 only (use external MCLK)
            self._write_register(0x02, 0b00000100)
        
        # Main Clock Control: Configure clock multiplier/divider
        if use_sclk_as_mclk:
            # MULTP_FACTOR=3 (x8), CLK_DAC_DIV=1 (divide by 2)
            self._write_register(0x01, 0b11000001)
        else:
            # Default clock settings
            self._write_register(0x01, 0b00100000)
        
        # Misc Control 2: Configure main clock source
        if use_sclk_as_mclk:
            # MSTCLK_SRCSEL=1, DLL_ON=1
            self._write_register(0x09, 0b00100010)
        else:
            self._write_register(0x09, 0b00000000)
        
        # Misc Control 1: Clock doubler settings
        if use_sclk_as_mclk:
            self._write_register(0x07, 0b00001100)
        
        # Time control (power-up timing)
        self._write_register(0x0A, 0x01)
        self._write_register(0x0B, 0x01)
        
        # Analog system configuration
        self._write_register(0x20, 0b00101010)  # S6_SEL=2, S2_SEL=2, S3_SEL=2
        self._write_register(0x21, 0b00111100)  # VSEL=0x1C, VREF_RMPDN1=1
        self._write_register(0x22, 0b00000000)  # Unmute analog outputs
        self._write_register(0x23, 0b00000100)  # VROI=1
        self._write_register(0x24, 0b00000111)  # Low power settings
        
        # SDP Interface: I2S format, 16-bit
        self._write_register(0x11, 0b00110000)
        
        # P2S Control
        self._write_register(0x0D, 0b00010100)
        
        # Misc Control 3: Normal operation
        self._write_register(0x18, 0b00000000)
        
        # Clock configuration: All clocks enabled
        self._write_register(0x08, 0b00111111)
        
        # Enable CSM: CSM_ON=1, SEQ_DIS=1
        self._write_register(0x00, 0b00000011)
        
        # Power up analog: VMIDSEL=2
        self._write_register(0x25, 0b00100000)
        
        # Unmute all channels
        self._write_register(0x13, 0b00000000)
        
        # Set default volume
        self.volume = 180
