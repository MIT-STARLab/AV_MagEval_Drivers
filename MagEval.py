from MagRM3100 import MagRM3100
from ADS1248 import ADS1248
import time

class MAG_REFERENCE:
    def __init__(self, bus = 0, device = 0, start=None, reset=None, drdy=None):

mag1 = MagRM3100(0,1,23) #initialize with bus, device, and chip select
mag2 = MagRM3100(0,1,14)

mag3= ADS1248(0,0,6,13,19) #initialize with bus,device, start,reset,drdy

mag1.initiate_CMM()
mag2.initiate_CMM()

mag3.send_command("RESET")
time.sleep(0.001)
mag3.send_command("SDATAC")

mag3.config_MUX0(BCS=0b00,MUX_SP=?,MUX_SN=?)
mag3.config_