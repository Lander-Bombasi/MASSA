#!/usr/bin/env python3

import time
import numpy as np
import lgpio

class HX711:
    def __init__(self, dout, pd_sck, gain=128):
        self.h = lgpio.gpiochip_open(0)  # Open the GPIO chip
        self.PD_SCK = pd_sck
        self.DOUT = dout
        
        # Setup pins
        lgpio.gpio_claim_output(self.h, self.PD_SCK)
        lgpio.gpio_claim_input(self.h, self.DOUT)
        lgpio.gpio_write(self.h, self.PD_SCK, 0)  # Initialize SCK low
        
        self.GAIN = 0
        self.REFERENCE_UNIT = 1
        self.OFFSET = 0
        self.last_val = 0
        
        self.set_gain(gain)
        time.sleep(0.1)

    def set_gain(self, gain):
        if gain == 128:
            self.GAIN = 1
        elif gain == 64:
            self.GAIN = 3
        elif gain == 32:
            self.GAIN = 2

        lgpio.gpio_write(self.h, self.PD_SCK, 0)
        self.read()
        
    def is_ready(self):
        return lgpio.gpio_read(self.h, self.DOUT) == 0

    def read(self):
        # Wait for the chip to become ready
        while not self.is_ready():
            time.sleep(0.001)
        
        data = 0
        for _ in range(24):
            lgpio.gpio_write(self.h, self.PD_SCK, 1)
            data <<= 1
            lgpio.gpio_write(self.h, self.PD_SCK, 0)
            if lgpio.gpio_read(self.h, self.DOUT):
                data |= 1
        
        # Set the channel and gain for next reading
        for _ in range(self.GAIN):
            lgpio.gpio_write(self.h, self.PD_SCK, 1)
            lgpio.gpio_write(self.h, self.PD_SCK, 0)
        
        # Convert from two's complement
        data ^= 0x800000
        
        self.last_val = data
        return data

    def read_average(self, times=3):
        values = []
        for _ in range(times):
            values.append(self.read())
            time.sleep(0.01)
        return sum(values) / len(values)

    def get_value(self, times=3):
        return self.read_average(times) - self.OFFSET

    def get_units(self, times=3):
        return self.get_value(times) / self.REFERENCE_UNIT

    def tare(self, times=15):
        self.OFFSET = self.read_average(times)

    def set_scale(self, scale):
        self.REFERENCE_UNIT = scale

    def set_reference_unit(self, reference_unit):
        self.REFERENCE_UNIT = reference_unit

    def power_down(self):
        lgpio.gpio_write(self.h, self.PD_SCK, 0)
        lgpio.gpio_write(self.h, self.PD_SCK, 1)
        time.sleep(0.001)

    def power_up(self):
        lgpio.gpio_write(self.h, self.PD_SCK, 0)
        time.sleep(0.001)
        self.set_gain(128)

    def close(self):
        lgpio.gpiochip_close(self.h)

def calibrate(hx):
    print("Taring... Remove any weights from the scale.")
    input("Press Enter to continue...")
    hx.tare()
    print("Tare done.")
    
    print("Place a known weight on the scale.")
    known_weight = float(input("Enter the weight in grams or other unit: "))
    
    print("Calibrating... Please wait...")
    readings = []
    for _ in range(20):
        val = hx.get_value()
        readings.append(val)
        time.sleep(0.1)
    
    avg_raw = np.mean(readings)
    reference_unit = avg_raw / known_weight
    
    hx.set_reference_unit(reference_unit)
    
    print(f"Calibration complete. Reference unit set to: {reference_unit}")
    print(f"Now {hx.get_units()} should be close to {known_weight}")

def main():
    hx = None
    try:
        print("Initializing HX711...")
        hx = HX711(dout=5, pd_sck=6)
        
        print("HX711 initialized")
        print("Raw value:", hx.read())
        
        calibrate(hx)
        
        print("Reading measurements (press Ctrl+C to exit):")
        while True:
            weight = hx.get_units(5)
            print(f"Weight: {weight:.2f} units", end='\r')
            time.sleep(0.2)
            
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if hx:
            hx.power_down()
            hx.close()

if __name__ == "__main__":
    main()