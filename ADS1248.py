import spidev
import time
import gpiozero

'''
ADS1248 class based off spidev objects

Documentation:
https://www.ti.com/lit/ds/symlink/ads1248.pdf?ts=1596548376865&ref_url=https%253A%252F%252Fwww.ti.com%252Fproduct%252FADS1248

'''

class ADS1248:
    #Register map (9.6.3)
    registers = {
        "MUX0"   : 0x00,
        "VBIAS"  : 0x01,
        "MUX1"   : 0x02,
        "SYS0"   : 0x03,
        "OFC0"   : 0x04,
        "OFC1"   : 0x05,
        "OFC2"   : 0x06,
        "FSC0"   : 0x07,
        "FSC1"   : 0x08,
        "FSC2"   : 0x09,
        "IDAC0"  : 0x0A,
        "IDAC1"  : 0x0B,
        "GPIOCFG": 0x0C,
        "GPIODIR": 0x0D,
        "GPIODAT": 0x0E
    }
    
    #Table 19 (9.5.3)
    commands = {
        "WAKEUP" : 0x00,
        "SLEEP"  : 0x02,
        "SYNC"   : [0x04,0x04],
        "RESET"  : 0x06,
        "NOP"    : 0xFF,
        "RDATA"  : 0x12,
        "RDATAC" : 0x14,
        "SDATAC" : 0x16,
        "RREG"   : [0x20,0x00], #Needs to be or'd with register and number nibbles 0x0r0n
        "WREG"   : [0x40,0x00], #Needs to be or'd with register and number nibbles 0x0r0n
        "SYSOCAL": 0x60,
        "SYSGCAL": 0x61,
        "SELFOCAL":0x62
    }
#     
#     #Table 29 (9.6.3)
#     #Format [register name, 1's in relevant ]
#     def fieldDef(reg,first,bits):
#         return {"reg":reg,"first":first,"bits":bits}
#     
#     register_field_bits = {
#         "BCS"     : fieldDef("MUX0",6,2),
#         "MUX_SP"  : fieldDef("MUX0",3,3),
#         "MUX_SN"  : fieldDef("MUX0",0,3),
#         "VBIAS"   : fieldDef("VBIAS",0,8),
#         "MUX1"    : fieldDef("CLKSTAT",0b11111111),
#         }
    #basic initialization
    def __init__(self, bus = 0, device = 0, start=None, reset=None, drdy=None):
        
        #Store pins
        self.startp=start
        self.resetp=reset
        self.drdyp=drdy
        
        if not self.startp==None:
            self.startp=gpiozero.DigitalOutputDevice(start,active_high=True,initial_value=False)
            
        if not self.resetp==None:
            self.resetp=gpiozero.DigitalOutputDevice(reset,active_high=False,initial_value=False)
            
        if not self.drdyp==None:
            self.startp=gpiozero.DigitalInputDevice(start,pull_up=False)
            self.startp.active_state=False
        
        
        #creating SPI device
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)

        #set parameters for SpiDev object
        self.spi.max_speed_hz = 1*1000000
        self.spi.mode = 1
        self.spi.bits_per_word = 8

    #Close instance of ADC
    def close(self):
        self.spi.close() #disconnects from the SPI device
        if not self.startp==None:
            self.startp.close()
        if not self.resetp==None:
            self.resetp.close()
        if not self.drdyp==None:
            self.drdyp.close()
            
            
    def __del__(self):
        self.close() #calls object's own close method

    def twos_comp(val,bits):
        if(val & (1<<(bits-1))) != 0:
           val = val - (1<<bits)
        return val
    
    #Toggles the reset pin 
    def pin_reset(self): #Resets device (9.4.2)
        self.resetp.blink(on_time=0.001, off_time=0.001, n=1, background=False)
        self.resetp.off()
        
    #Puts the device to sleep with the start pin 
    def pin_sleep(self): #Put device to powerdown mode (9.4.3)
        self.startp.off()
    
    def start_conversion(self): #Start single conversion (9.4.4)
        #do i need a when_activated on drdy?
        self.startp.blink(on_time=0.001, off_time=0.001, n=1, background=False)
        self.startp.off()
        
    def start_continuous(self): #Start the device operating continuously (9.4.4)
        self.startp.on()
    
    #The following two functions are associated with the read data continuous mode (9.5.3.6)
    def get_results(self):
        return [self.x,self.y,self.z]
    
    def read_continuous(self):
        to_send=[commands["NOP"]]*3
        self.x,self.y,self.z = self.spi.xfer2(to_send)
    
    #Send operational command (except those which read/write registrs)
    def send_command(self,command,r=None,n=None): #
        if command="WREG" or command="RREG":
            raise NameError("Use standalone functions to write or read registers")
            
        else if command="RDATA":
            to_send=commands[command]+[commands["NOP"]]*3
            return self.spi.xfer2(to_send)[1:]
            
        else if command="RDATAC":
            #Must wait for drdybar to go low
            self.drdyp.wait_for_active(0.1)
            
            self.drdyp.activated=read_continuous
            self.spi.xfer2([commands[command]])
            return
            
        else:
            self.spi.xfer2([commands[command]])
            return

    #Write to a configuration register
    def write_register(self,r,data,n=1):
        if not len(data)==n:
            raise ValueError
        if n<1 or n>15:
            raise ValueError
        
        if type(r) is str:
            r=registers[r]
        
        to_send=[commands["WREG"][0]|r,commands["WREG"][1]|(n-1)]+data
        self.spi.xfer2(to_send)
    
    #read a configuration register
    def read_register(self,r,n=1):
        if n<1 or n>15:
            raise ValueError
        if type(r) is str:
            r=registers[r]

        to_send=[commands["RREG"][0]|r,commands["RREG"][1]|(n-1)]+[commands["NOP"]]*n
        result = self.spi.xfer2(to_send)
        return result[2:]
    
    #Config associated with MUX0 (9.6.4.1)
    def config_MUX0(self,BCS=None,MUX_S=None,MUX_SN=None): #9.6.4.1
        to_send=self.read_register("MUX0")
        
        if not BCS is None:
            if BCS<0 or BCS>3:
                raise ValueError
            to_send=(to_send & 0b00111111)|BCS<<6
            
        if not MUX_SP is None:
            if MUX_SP<0 or MUX_SP>7:
                raise ValueError
            to_send=(to_send & 0b00111000)|MUX_SP<<3
            
        if not MUX_SN is None:
            if MUX_SN<0 or MUX_SP>7:
                raise ValueError
            to_send=(to_send & 0b00000111)|MUX_SN<<0
            
        self.write_register("MUX0",to_send,1)
            
    def set_inputs(self,p,n):
        self.config_MUX0(MUX_SP=p,MUX_SN=n)
    
    def set_bcs(self,bcs):
        self.config_MUX0(BCS=bcs)
    
    #Config associated with VBIAS (9.6.4.2)
    def config_VBIAS(self, VBIAS=None):
        if not VBIAS is None:
            if VBIAS<0 or VBIAS>0xFF:
                raise ValueError
            self.write_register("VBIAS",VBIAS)
    
    def VBIAS_on(self,pin):
        if pin<0 or pin>7:
            raise ValueError
        
        to_send=self.read_register("VBIAS")
        to_send=to_send|(0b1<<pin)
        self.write_register("VBIAS",to_send)
        
    def VBIAS_off(self,pin):
        if pin<0 or pin>7:
            raise ValueError
        
        to_send=self.read_register("VBIAS")
        to_send=to_send& ~(0b1<<pin)
        self.write_register("VBIAS",to_send)
    
    #Config associated with MUX1 (9.6.4.3)
    def config_MUX1(self,VREFCON=None,REFSELT=None,MUXCAL=None):
        to_send=self.read_register("MUX1")
        
        if not VREFCON is None:
            if VREFCON<0 or VREFCON>3:
                raise ValueError
            to_send=(to_send & 0b10011111)|VREFCON<<5
            
        if not REFSELT is None:
            if REFSELT<0 or REFSELT>3:
                raise ValueError
            to_send=(to_send & 0b11100111)|REFSELT<<3
        
        if not MUXCAL is None:
            if MUXCAL<0 or MUXCAL>0b111:
                raise ValueError
            to_send=(to_send & 0b11111000)|MUXCAL<<0
            
        self.write_register("MUX1",to_send)
        
    def get_clock_status(self): #0 for internal, 1 for external
        return self.read_register("MUX1")>>7
    
    def set_vrefcon(self, vrefcon):
        self.config_MUX1(VREFCON=vrefcon)
    
    def set_refselt(self, refselt):
        self.config_MUX1(REFSELT=refselt)
        
    def set_muxcal(self, muxcal):
        self.config_MUX1(MUXCAL=muxcal)
        
    #Config associated with SYS0 (9.6.4.4):
    def config_SYS0(self,PGA=None,DR=None)
        to_send=self.read_register("SYS0")&0b01111111 #bit 7 must always be 0
        
        if not PGA is None:
            if PGA<0 or PGA>3:
                raise ValueError
            to_send=(to_send & 0b10001111)|PGA<<4
            
        if not DR is None:
            if DR<0 or DR>0b1001:
                raise ValueError
            to_send=(to_send & 0b11110000)|DR<<0
            
        self.write_register("SYS0",to_send)
    
    def set_pga(self,pga):
        self.config_SYS0(PGA=pga)
    
    def set_dr(self, dr):
        self.config_SYS0(DR=dr)
        
    #Config associated with OFC(9.6.4.5)
    def get_offset(self):
        res = self.read_register("OFC0") | \
               self.read_register("OFC1")<<8 | self.read_register("OFC2")<<16
        return self.twos_comp(res,24)
    
    def set_offset(self,offset):
        if offset<-0x8FFFFF or offset>0x8FFFFF:
            raise ValueError
        #Perform twos complement
        to_send=offset^(2**24-1)+1
        self.write_register("OFC0",to_send&0xFF)
        self.write_register("OFC1",to_send&0xFF00)
        self.write_register("OFC2",to_send&0xFF0000)
        
    #Config associated with FSC(9.6.4.6)
    def get_fsc(self):
        res = self.read_register("FSC0") | \
               self.read_register("FSC1")<<8 | self.read_register("FSC2")<<16
        fsc = self.twos_comp(res,24)
        return fsc/0x400000
    
    def set_fsc(self,fsc):
        if type(fsc) is float:
            fsc=int(fsc*0x400000)
        if fsc<-0x8FFFFF or fsc>0x8FFFFF:
            raise ValueError
        #Perform twos complement
        to_send=fsc^(2**24-1)+1
        self.write_register("FSC0",to_send&0xFF)
        self.write_register("FSC1",to_send&0xFF00)
        self.write_register("FSC2",to_send&0xFF0000)
    
    #Config associated with IDAC0 (9.6.4.7)
    def config_IDAC0(self,DRDYMODE=None,IMAG=None):
        to_send=self.read_register("IDAC0")
        
        if not DRDYMODE is None:
            if DRDYMODE<0 or DRDYMODE>1:
                raise ValueError
            to_send=(to_send & 0b11110111)|DRDYMODE<<3
            
        if not IMAG is None:
            if IMAG<0 or IMAG>0b111:
                raise ValueError
            to_send=(to_send & 0b11111000)|IMAG<<0
            
        self.write_register("IDAC0",to_send)
        
    def get_revisionID(self):
        return self.read_register("IDAC0")>>4
    
    def set_drdymode(self,drdymode):
        self.config_IDAC0(DRDYMODE=drdymode)
        
    def set_imag(self,imag):
        self.config_IDAC0(IMAG=imag)
        
    #Config associated with IDAC1
    def config_IDAC1(self,I1DIR=None,I2DIR=None):
        to_send=self.read_register("IDAC1")
        
        if not I1DIR is None:
            if I1DIR<0 or I1DIR>0b1111:
                raise ValueError
            to_send=(to_send & 0b11110000)|I1DIR<<4
            
        if not I2DIR is None:
            if I2DIR<0 or I2DIR>0b1111:
                raise ValueError
            to_send=(to_send & 0b00001111)|I2DIR

            
        self.write_register("IDAC1",to_send)
        
    #Config associated with GPIOCFG (9.6.4.9)
    def config_GPIOCFG(self, IOCFG3=None,IOCFG2=None,IOCFG1=None,IOCFG0=None)
        to_send=self.read_register("GPIOCFG")&0x0F #First nibble must always be 0
        
        if IOCFG3==1:
            to_send=to_send|(1<<3)
        else if IOCFG3==0:
            to_send=to_send&~(1<<3)
        if IOCFG2==1:
            to_send=to_send|(1<<2)
        else if IOCFG2==0:
            to_send=to_send&~(1<<2)
        if IOCFG1==1:
            to_send=to_send|(1<<1)
        else if IOCFG1==0:
            to_send=to_send&~(1<<1)
        if IOCFG0==1:
            to_send=to_send|(1)
        else if IOCFG0==0:
            to_send=to_send&~(1)

    #Possible TODO: Keep adding functions for GPIO configuration, but not needed if
    #Not using the GPIO functionality