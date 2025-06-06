import lgpio
import time

class HX711:
    def __init__(self, dout, pd_sck):
        self.dout = dout
        self.pd_sck = pd_sck
        self.handle = lgpio.gpiochip_open(0)

        lgpio.gpio_claim_input(self.handle, self.dout)
        lgpio.gpio_claim_output(self.handle, self.pd_sck)

    def is_ready(self):
        return lgpio.gpio_read(self.handle, self.dout) == 0

    def read_raw(self):
        while not self.is_ready():
            time.sleep(0.01)

        count = 0
        for _ in range(24):
            lgpio.gpio_write(self.handle, self.pd_sck, 1)
            count = count << 1 | lgpio.gpio_read(self.handle, self.dout)
            lgpio.gpio_write(self.handle, self.pd_sck, 0)

        # Set gain/channel
        lgpio.gpio_write(self.handle, self.pd_sck, 1)
        lgpio.gpio_write(self.handle, self.pd_sck, 0)

        # Convert from 24-bit signed
        if count & 0x800000:
            count -= 0x1000000
        return count

    def get_weight(self, readings=5):
        return sum(self.read_raw() for _ in range(readings)) / readings

    def power_down(self):
        lgpio.gpio_write(self.handle, self.pd_sck, 0)
        lgpio.gpio_write(self.handle, self.pd_sck, 1)
        time.sleep(0.1)

    def power_up(self):
        lgpio.gpio_write(self.handle, self.pd_sck, 0)
        time.sleep(0.1)

    def close(self):
        lgpio.gpiochip_close(self.handle)
