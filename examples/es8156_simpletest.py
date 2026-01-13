# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
ES8156 DAC Sine Wave Example
"""

import array
import math
import time
import audiobusio
import audiocore
import board
from es8156 import ES8156

# Initialize I2C and ES8156 DAC
i2c = board.I2C()
dac = ES8156(i2c)

print("ES8156 Sine Wave Demo")
print(f"Chip ID: 0x{dac.chip_id:04X}")
print(f"Chip Version: {dac.chip_version}")

# Configure the DAC
dac.configure()
print("DAC configured!")

# Initialize I2S audio output
if hasattr(board, 'I2S_BCLK') and hasattr(board, 'I2S_WS'):
    audio = audiobusio.I2SOut(board.I2S_BCLK, board.I2S_WS, board.I2S_DIN)
else:
    audio = audiobusio.I2SOut(board.D5, board.D18, board.D19) # Yoto Mini pinout

tone_volume = 0.5
frequency = 440
sample_rate = 44100
length = sample_rate // frequency

sine_wave = array.array("h", [0] * length)
for i in range(length):
    sine_wave[i] = int((math.sin(math.pi * 2 * i / length)) * tone_volume * (2**15 - 1))

sine_wave_sample = audiocore.RawSample(sine_wave, sample_rate=sample_rate)

print(f"Playing {frequency}Hz tone")

audio.play(sine_wave_sample, loop=True)
dac.volume = 150

while True:

    dac.mute = False
    time.sleep(1)
    dac.mute = True
    time.sleep(1)