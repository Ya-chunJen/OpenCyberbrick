from machine import Pin,SPI # type: ignore
from epaper4in2 import EPD, EPD_WIDTH, EPD_HEIGHT
import framebuf # type: ignore
from micropython import const # type: ignore
import ujson # type: ignore
import urequests # type: ignore
import uos # type: ignore
import ubinascii # type: ignore

# esp32
# 硬件SPI
# HSPI (id=1)  sck=14   mosi(sda) = 13  miso(无需连接)= 12
# VSPI (id=2)  sck=18   mosi=23   miso= 19
# self.hspi = SPI(1, baudrate=10000000,sck=Pin(14), mosi=Pin(13), miso=Pin(12))
# self.epaper = EPD(self.hspi, rst=Pin(37), dc=Pin(38), cs=Pin(39) , busy=Pin(40)) 

# esp8266
# 硬件SPI
# The hardware SPI is faster (up to 80Mhz), but only works on following pins: 
# MISO is GPIO12（D6）, MOSI(sda) is GPIO13(D7), and SCK is GPIO14（D5）. 
# It has the same methods as the bitbanging SPI class above, except for the pin parameters for the constructor and init (as those are fixed):
# self.hspi = SPI(1, baudrate=10000000, polarity=0, phase=0)
# rst=Pin(2)-D4, dc=Pin(4)-D2, cs=Pin(15)-D8 , busy=Pin(5)-D1
# (SPI(0) is used for FlashROM and not available to users.)

class InkDisplay():
    def __init__(self) -> None:
        self.hspi = SPI(1, baudrate=10000000,sck=Pin(14), mosi=Pin(13), miso=Pin(12))
        # self.hspi = SPI(1, baudrate=10000000, polarity=0, phase=0)
        self.hspi.init()
        self.epaper = EPD(self.hspi, rst=Pin(37), dc=Pin(38), cs=Pin(39) , busy=Pin(40))
        # self.epaper = EPD(self.hspi, rst=Pin(2), dc=Pin(4), cs=Pin(15) , busy=Pin(5)) 
        self.epaper.init()

        # Display resolution
        self.EPD_WIDTH  = const(400)
        self.EPD_HEIGHT = const(300)
        self.black      = const(0)
        self.white      = const(1)
        
        # 创建帧缓冲
        self.buf = bytearray(self.EPD_WIDTH * self.EPD_HEIGHT // 8)
        self.fb = framebuf.FrameBuffer(self.buf , self.EPD_WIDTH, self.EPD_HEIGHT, framebuf.MONO_HLSB)
    
    def show(self):
        # 显示buf中的内容
        self.epaper.display_frame(self.buf)
    
    def clear(self,color=1):
        # 清屏，默认为白色
        self.fb.fill(color)
        
    def displaychar(self,text,pos_x=50,pos_y=50):
        # 显示英文字符
        self.fb.text(text, pos_x, pos_y, self.black)

    def displaypixle(self,x,y,color=1):
        # 显示像素
        self.fb.pixel(x,y,color)

    def displayimg(self,image_array,width,height,pos_x=50,pos_y=50):
        fbimage = framebuf.FrameBuffer(image_array, width, height, framebuf.MONO_HLSB)
        self.fb.blit(fbimage, pos_x , pos_y)

    def displayimgv2(self,image_array):
        # image_array 是图片像素矩阵对应的二维数组，对应的字节数组
        screen_width = self.EPD_WIDTH  # 例子中的宽度
        screen_height = len(image_array) * 8 // screen_width  # 计算屏幕高度
        # 遍历字节数组并设置像素
        for byte_index, byte in enumerate(image_array):
            for bit in range(8):
                # 计算当前像素的x, y坐标
                x = (byte_index * 8 + bit) % screen_width
                y = (byte_index * 8 + bit) // screen_width

                # 计算像素颜色
                color = (byte >> (7 - bit)) & 1
                self.displaypixle(x,y,color)

    def display_bin_file(self, filename="byte_array.bin"):
        with open(filename, "rb") as f:
            image_array = f.read()
        self.displayimgv2(image_array)
        return True

    def display_bin_url(self, bin_url="https://pubdz.paperol.cn/bin/byte_array.bin"):
        response = urequests.get(bin_url)
        image_array = response.content
        self.displayimgv2(image_array)
        return True
    
    def display_jsondata(self, data):
        if data == None:
            data = {
            "text":"测试图片|-2|50\n测试图片2",
            "fontsize":30,
            "align":-1
            }
        try:
            # 向云函数发起请求。
            url = "https://imagepil-ebseiglznc.cn-zhangjiakou.fcapp.run"
            headers = {'User-Agent': 'MicroPython urequests','Content-Type':'application/json'}
            data = ujson.dumps(data).encode('utf-8')
            response = urequests.post(url,data=data,headers=headers)
            res_json = response.json()
            image_array_base64 = res_json["data"]
            image_array = ubinascii.a2b_base64(image_array_base64)
        except Exception as e:
            print("解析返回结果失败，错误信息：",e)
            return e
        self.displayimgv2(image_array)
        return True