import spidev
import time
import gpiozero


'''
MagRM3100 class based off spidev objects

Documentation:
https://www.pnicorp.com/wp-content/uploads/RM3100-Testing-Boards-User-Manual-r04-1.pdf

'''

class MagRM3100:

    #Initiates continuous measurement mode
    RM_CMM = 0x01

    #Cycle Count Registers
    RM_CCX = 0x04
    RM_CCY = 0x06
    RM_CCZ = 0x08

    #Sets continuous measurement mode data rate
    RM_TMRC = 0x0B

    #Measurement results
    RM_MX = 0x24
    RM_MY = 0x27
    RM_MZ = 0x2A

    #Write and Read constants
    WRITE = 0
    READ = 0x80


    #basic initialization
    def __init__(self, bus = 0, device = 1, cs=None):
        
        #creating SPI device
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)

        #set parameters for SpiDev object
        self.spi.max_speed_hz = 1*1000000
        self.spi.mode = 0
        self.spi.bits_per_word = 8
        
        
        self.cs=cs
        if not cs==None:
            self.cspin=gpiozero.DigitalOutputDevice(cs,active_high=False,initial_value=False)
        

    def close(self):
        self.spi.close() #disconnects from the SPI device
        self.cspin.close()

    def __del__(self):
        self.close() #calls object's own close method
        
    #Function to manually toggle gpio pins as chip select    
    def transfer2(self, data):
        if not self.cs==None:
            self.cspin.on()
            time.sleep(0.01)
            
        mydat = self.spi.xfer2(data)
        
        if not self.cs==None:
            self.cspin.off()
            time.sleep(0.01)
            
        return mydat


    def set_CycleCount(self, x_cycle = 200, y_cycle = 200, z_cycle = 200): #sets cycle counts (5.1)
        #default values set all cycles to 200 (DECIMAL)

        #convert all cycle values to MSB and LSB hex
        xMSB = x_cycle // 256
        xLSB = x_cycle % 256
        yMSB = y_cycle // 256
        yLSB = y_cycle % 256
        zMSB = z_cycle // 256
        zLSB = z_cycle % 256

        #inputs to transfer
        address = self.WRITE | self.RM_CCX
        data = [xMSB, xLSB, yMSB, yLSB, zMSB, zLSB]

        to_send = [address] + data

        self.transfer2(to_send)


    def initiate_CMM(self): #initiates continuous measurement mode (5.2)
        
        #inputs to transfer
        address = self.WRITE | self.RM_CMM #write to // adds to 7bit CMM
        data = 0b01110001

        
        self.transfer2([address, data])


    def set_TMRC(self, TMRC_Val): #sets the CMM update rate with TMRC (5.2.1)

        #valid range of TMRC_Val is 0x92 to 0x9F
        if not 0x92 <= TMRC_Val <= 0x9F:
            raise ValueError

        #inputs to transfer
        address = self.WRITE | self.RM_TMRC
        data = TMRC_Val

        self.transfer2([address, data])


    def measure(self): #returns measurement values in microTesla (uT)

        #inputs to transfer
        address = self.READ | self.RM_MX
        data = [0]*9 #sending 9 filler bytes

        to_send = [address] + data

        measurements = self.transfer2(to_send)

        #yielded results variables
        status, x2, x1, x0, y2, y1, y0, z2, z1, z0 = measurements #separate into variables

        x = (256**2)*x2 + (256)*x1 + x0
        y = (256**2)*y2 + (256)*y1 + y0
        z = (256**2)*z2 + (256)*z1 + z0

        #handle 2's complement/signed encoding
        x = x if x<2**23 else x-2**24
        y = y if y<2**23 else y-2**24
        z = z if z<2**23 else z-2**24

        return (y/75, x/75, -z/75, status >= 128)


if __name__ == "__main__":

    Magboi = MagRM3100()

    Magboi.initiate_CMM()

    Magboi.set_TMRC(0x96)

    for n in range(1000):
        x, y, z, status = Magboi.measure()
        print(str(x) + "\t" + str(y) + "\t" + str(z) + "\t" + str(status))

        time.sleep(0.1)