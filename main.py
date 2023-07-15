# MicroPython SH1106 OLED driver
#
# Pin Map I2C for ESP8266
#   - 3v - xxxxxx   - Vcc
#   - G  - xxxxxx   - Gnd
#   - D2 - GPIO 5   - SCK / SCL
#   - D1 - GPIO 4   - DIN / SDA
#   - D0 - GPIO 16  - Res (required, unless a Hardware reset circuit is connected)
#   - G  - GND        CS
#   - G  - GND        D/C
#
# Pin's for I2C can be set almost arbitrary
#
from machine import Pin, I2C
import sh1106       # library for OLED 
import bme280       # library for BME280 
import i2c_lib      # library for ENS160
from bh1750 import BH1750       # library for BH1750 
import time
import neopixel
import binascii

time.sleep(4)

led_onboard=16
pixel = neopixel.NeoPixel(machine.Pin(led_onboard), 1)
pixel[0] = (50,0,0)
pixel.write()

ENS160_ADDR = 0x53

oled_err = 0
ens160_err = 0
bme280_err = 0
lifebit = 0
menu_status = 0

# push button config
button = Pin(3, mode=Pin.IN)

# configure I2C settings
i2c = I2C(0, scl=Pin(9), sda=Pin(8), freq=100000)
time.sleep(3)

#print out any addresses found
devices = i2c.scan()
'''
if devices:
    for d in devices:
        print(hex(d))
        
print (len(devices))

while len(devices) < 4:
    pixel[0] = (0,50,0)
    pixel.write()
    i2c = I2C(0, scl=Pin(9), sda=Pin(8), freq=100000)
    time.sleep(3)
    devices = i2c.scan()
    print (len(devices))
'''

# oled display config
display = sh1106.SH1106_I2C(128, 64, i2c, Pin(2), 0x3c)

# light sensor config
bh1750 = BH1750(0x23, i2c)

display.init_display()
display.sleep(False)
display.fill(0)
display.contrast(100)
display.text('  Multi', 0, 0, 1)
display.text(' Sensor', 0, 10, 1)
display.text(' Station', 0, 20, 1)
display.text(' v0.2 July 2023', 0, 40, 1)
display.show()

time.sleep(2)
display.contrast(250)

# temperature, humidity, pressure sensor config
bme = bme280.BME280(i2c=i2c)          

# air quality sensor config
i2c_lib.reg_write(i2c, ENS160_ADDR, 0x10, 0x02)
time.sleep(0.5)

pixel[0] = (0,0,5)
pixel.write()

display.fill(0)
while True:
    pixel[0] = (0,0,5)
    pixel.write()
    
    # select measurement to show
    if button.value():
        time.sleep(0.1)
        if menu_status==1:
            menu_status = 0
        elif menu_status==0:
            menu_status=1
            
    #print(f" menu_status: {menu_status}")
    #print(button.value())
    time.sleep(0.1)
    
    if menu_status == 1:
        display.fill(0)
        time.sleep(0.1)
        delimiter = '.'
        lux_value = str(bh1750.measurement).split(delimiter, 1)[0]
        
        text1 = f"Light: {lux_value} lx"
        
        display.text(text1, 0, 0, 1)
        display.show()
        time.sleep(0.3)
        #print(text1)
        
    elif menu_status == 0:
    
        # BME280 sensor
        try:
            #print (bme.values)
            bme280_data = str(bme.values)
            
            # temperature from BME280
            temp_start = bme280_data.find('Temp:')
            temp_stop = bme280_data.find('C')
            temperature = bme280_data[temp_start+5:temp_stop]
            # rescaling temperature
            temperature = round(1.1277 * float(temperature) - 8.571, 1)
            
            # pressure from BME280
            press_start = bme280_data.find('Press:')
            press_stop = bme280_data.find('hPa')
            pressure = bme280_data[press_start+6:press_stop]
            pressure = round(float(pressure))
            
            # humidity from BME280
            humid_start = bme280_data.find('Humid:')
            humid_stop = bme280_data.find('%')
            humidity = bme280_data[humid_start+6:humid_stop]

        except Exception as e:
            print ("BME280 Error: {}".format(str(e)))
            bme280_err+=1
            time.sleep(0.3)
        
        
        # ENS160 sensor
        try:
            ens160_OPMODE = i2c_lib.reg_read(i2c, ENS160_ADDR, 0x10, 1)
            ens160_OPMODE = binascii.hexlify(ens160_OPMODE).decode()
            #print(f" OPMODE: {ens160_OPMODE}")

            ens160_DATA_STS = i2c_lib.reg_read(i2c, ENS160_ADDR, 0x20, 1)
            ens160_DATA_STS = binascii.hexlify(ens160_DATA_STS).decode()
            #print(f" DATA_STS: {ens160_DATA_STS}")

            ens160_DATA_TVOC = i2c_lib.reg_read(i2c, ENS160_ADDR, 0x22, 1)
            ens160_DATA_TVOC = binascii.hexlify(ens160_DATA_TVOC).decode()
            ens160_DATA_TVOC_LSB = int(ens160_DATA_TVOC, 16)
            #print(f" TVOC LSB: {ens160_DATA_TVOC_LSB}")
            
            ens160_DATA_TVOC = i2c_lib.reg_read(i2c, ENS160_ADDR, 0x23, 1)
            ens160_DATA_TVOC = binascii.hexlify(ens160_DATA_TVOC).decode()
            ens160_DATA_TVOC_MSB = int(ens160_DATA_TVOC, 16)
            #print(f" TVOC MSB: {ens160_DATA_TVOC_MSB}")
        
            TVOC_total = (ens160_DATA_TVOC_MSB * 256) + ens160_DATA_TVOC_LSB
            #print(f" TVOC: {TVOC_total}")
            
            if TVOC_total <= 300:
                TVOC_Rating = "Best"
            elif TVOC_total > 300 and TVOC_total <= 1000 :
                TVOC_Rating = "Good"
            elif TVOC_total > 1000 and TVOC_total <= 3000:
                TVOC_Rating = "Fair"
            elif TVOC_total > 3000 and TVOC_total <= 10000:
                TVOC_Rating = "Poor"
            elif TVOC_total > 10000:
                TVOC_Rating = "Bad"
            
            ens160_DATA_ECO2 = i2c_lib.reg_read(i2c, ENS160_ADDR, 0x24, 1)
            ens160_DATA_ECO2 = binascii.hexlify(ens160_DATA_ECO2).decode()
            ens160_DATA_ECO2_LSB = int(ens160_DATA_ECO2, 16)
            #print(f" ECO2 LSB: {ens160_DATA_ECO2_LSB}")
            
            ens160_DATA_ECO2 = i2c_lib.reg_read(i2c, ENS160_ADDR, 0x25, 1)
            ens160_DATA_ECO2 = binascii.hexlify(ens160_DATA_ECO2).decode()
            ens160_DATA_ECO2_MSB = int(ens160_DATA_ECO2, 16)
            #print(f" ECO2 MSB: {ens160_DATA_ECO2_MSB}")
            
            ECO2_total = (ens160_DATA_ECO2_MSB * 256) + ens160_DATA_ECO2_LSB
            #print(f" ECO2: {ECO2_total}")
            
            ens160_DATA_AQI = i2c_lib.reg_read(i2c, ENS160_ADDR, 0x21, 1)
            ens160_DATA_AQI = binascii.hexlify(ens160_DATA_AQI).decode()
            ens160_DATA_AQI = int(ens160_DATA_AQI, 16)
            #print(f" AQI: {ens160_DATA_AQI} \n\n")
            
            if ens160_DATA_AQI == 1:
                AQI_Rating = "Best"
            elif ens160_DATA_AQI == 2:
                AQI_Rating = "Good"
            elif ens160_DATA_AQI == 3:
                AQI_Rating = "Fair"
            elif ens160_DATA_AQI == 4:
                AQI_Rating = "Poor"
            elif ens160_DATA_AQI == 5:
                AQI_Rating = "Bad"
        
            time.sleep(1)
            
            ens160_DATA_T = i2c_lib.reg_read(i2c, ENS160_ADDR, 0x30, 1)
            ens160_DATA_T = binascii.hexlify(ens160_DATA_T).decode()
            ens160_DATA_T_LSB = int(ens160_DATA_T, 16)
            #print(f" DATA_T LSB: {ens160_DATA_T_LSB}")

            ens160_DATA_T = i2c_lib.reg_read(i2c, ENS160_ADDR, 0x31, 1)
            ens160_DATA_T = binascii.hexlify(ens160_DATA_T).decode()
            ens160_DATA_T_MSB = int(ens160_DATA_T, 16)
            #print(f" DATA_T MSB: {ens160_DATA_T_MSB}")
            
        except Exception as e:
            #print ("ENS160 Error: {}".format(str(e)))
            time.sleep(0.3)
            ens160_err+=1
            i2c_lib.reg_write(i2c, ENS160_ADDR, 0x10, 0x02)


        time.sleep(0.7)
        
        pixel[0] = (0,0,0)
        pixel.write()
        
        try:
            display.fill(0)
            text1 = f"AQI:  {ens160_DATA_AQI}    {AQI_Rating}"
            display.text(text1, 0, 0, 1)
            
            text2 = f"TVOC: {TVOC_total} ppb "
            display.text(text2, 0, 10, 1)
            
            text3 = f"eCO2: {ECO2_total} ppm"
            display.text(text3, 0, 20, 1)
            
            text4 = f"Temp: {temperature} C"
            display.text(text4, 0, 30, 1)
            
            text5 = f"Press: {pressure} hPa"
            display.text(text5, 0, 40, 1)
            
            text6 = f"Humid: {humidity} %"
            display.text(text6, 0, 50, 1)
            display.show()
            time.sleep(0.1)
        
        except Exception as e:
            #print ("OLED Error: {}".format(str(e)))
            time.sleep(0.3)
            oled_err+=1
            #i2c_lib.reg_write(i2c, ENS160_ADDR, 0x10, 0x02)
        
        #print(f" oled_err: {oled_err} | ens160_err: {ens160_err} | bme280_err: {bme280_err}")
        
        lifebit = not lifebit
        

        
      













