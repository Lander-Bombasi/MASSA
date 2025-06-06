# Quick hardware test script (run this directly on your Pi)
import lgpio
import time

DT_PIN = 5
SCK_PIN = 6

def read_hx711_raw(chip, dt_pin, sck_pin):
    lgpio.gpio_write(chip, sck_pin, 0)
    while lgpio.gpio_read(chip, dt_pin) == 1:
        time.sleep(0.001)
    
    data = 0
    for _ in range(24):
        lgpio.gpio_write(chip, sck_pin, 1)
        data = (data << 1) | lgpio.gpio_read(chip, dt_pin)
        lgpio.gpio_write(chip, sck_pin, 0)
    
    # Set the channel and gain factor (optional, usually needed)
    lgpio.gpio_write(chip, sck_pin, 1)
    lgpio.gpio_write(chip, sck_pin, 0)
    
    if data & 0x800000:
        data -= 0x1000000
    return data

try:
    chip = lgpio.gpiochip_open(0)
    lgpio.gpio_claim_output(chip, SCK_PIN, 0)
    lgpio.gpio_claim_input(chip, DT_PIN)
    
    print("Reading raw values (ctrl+c to stop):")
    while True:
        readings = []
        for _ in range(10):
            val = read_hx711_raw(chip, DT_PIN, SCK_PIN)
            readings.append(val)
            time.sleep(0.1)
        
        avg = sum(readings) / len(readings)
        print(f"Raw: {avg:>8} | Grams: {(avg - 91096)/104.2787:.1f}g")

except Exception as e:
    print(f"Error: {e}")
finally:
    if 'chip' in locals():
        lgpio.gpiochip_close(chip)
