#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'GPIO处理'
__author__ = 'kakake'

import threading
import time
import RPi.GPIO
from httphandle import httphandle

class GPIO(threading.Thread):
    DISABLED=0
    ENABLED=1
    ALT=2
        
    IN = RPi.GPIO.IN
    OUT = RPi.GPIO.OUT
    
    LOW = RPi.GPIO.LOW
    HIGH = RPi.GPIO.HIGH

    GPIO_PINS = []
    GPIO_AVAILABLE = [0, 1, 4,5,6, 7, 8, 9, 10, 11,12,13, 14, 15,16, 17, 18,19,20, 21, 22, 23, 24, 25,26,27]
    ALT = {
        "I2C": {"enabled": False, "pins": [0, 1]},
        "SPI": {"enabled": False, "pins": [7, 8, 9, 10, 11]},
        "UART": {"enabled": False, "pins": [14, 15]}
    }
    
    def __init__(self,http):
        threading.Thread.__init__(self)
        self.setupdata={}
        self.loopdata=[]
        self.replydata=[]
        self.http=http
        #self.thread_stop = False

        RPi.GPIO.setmode(RPi.GPIO.BCM)

        for i in range(self.GPIO_AVAILABLE[len(self.GPIO_AVAILABLE)-1]+1):
            self.GPIO_PINS.append({"mode": 0, "direction": None, "value": None})

        self.setALT("I2C", False)
        self.setALT("SPI", False)
        self.setALT("UART", True)

        for pin in self.GPIO_AVAILABLE:
            if self.GPIO_PINS[pin]["mode"] != GPIO.ALT:
                self.GPIO_PINS[pin]["mode"] = GPIO.ENABLED
                self.setDirection(pin, GPIO.IN)

    def isAvailable(self, gpio):
        return gpio in self.GPIO_AVAILABLE
    
    def isEnabled(self, gpio):
        return self.GPIO_PINS[gpio]["mode"] == GPIO.ENABLED
    
    def setValue(self, pin, value):
        RPi.GPIO.output(pin, value)
        self.GPIO_PINS[pin]["value"] = value
    
    def getValue(self, pin):
        if (self.GPIO_PINS[pin]["direction"] == GPIO.IN):
            self.GPIO_PINS[pin]["value"] = RPi.GPIO.input(pin)
        if (self.GPIO_PINS[pin]["value"] == GPIO.HIGH):
            return 1
        else:
            return 0
        
    def setDirection(self, pin, direction):
        if self.GPIO_PINS[pin]["direction"] != direction:
            RPi.GPIO.setup(pin, direction)
            self.GPIO_PINS[pin]["direction"] = direction
            if (direction == GPIO.OUT):
                self.setValue(pin, False)
                
    def getDirection(self, pin):
        if self.GPIO_PINS[pin]["direction"] == GPIO.IN:
            return "in"
        else:
            return "out"
            
    def setALT(self, alt, enable):
        for pin in self.ALT[alt]["pins"]:
            p = self.GPIO_PINS[pin];
            if True:
                p["mode"] = GPIO.ALT
            else:
                p["mode"] = GPIO.ENABLED
                self.setDirection(pin, GPIO.OUT)
                self.setValue(pin, False)
        self.ALT[alt]["enabled"] = enable
                
    def writeJSON(self):
        jsondata={
	        "I2C":False,
	        "SPI":False,
	        "UART":False,
	        "GPIO":{}
        }
        for (alt, value) in self.ALT.items():
            jsondata[alt]=value["enabled"]
			
        for pin in self.GPIO_AVAILABLE:
            mode = "ENABLED"
            direction = "out"
            value = 0

            if (self.GPIO_PINS[pin]["mode"] == GPIO.ALT):
                mode = "ALT"
            else:
                direction = self.getDirection(pin)
                value = self.getValue(pin)

                jsondata['GPIO']['%d' % pin]={
                    "mode":mode,
                    "direction":direction,
                    "value":value
                }
        return jsondata
		
    def checkGPIO(self, gpio):
        try:
            i = int(gpio)
            if not self.isAvailable(i):
                print "GPIO " + str(gpio) + " Not Available"
                return False
            if not self.isEnabled(i):
                print "GPIO " + str(gpio) + " Disabled"
                return False
            return True
        except ValueError:
            print 'no int'
            return False
		
    def run(self): #Overwrite run() method
        #self.thread_stop = False
        #self.setup(self.setupdata)
        while True:
            self.loop(self.loopdata)
            time.sleep(0.1)
    def stop(self):  
        self.thread_stop = True		

    def setup(self,sdata):#先设置GPIO的输入输出
        if len(sdata)>0:
            for (pin, value) in sdata.items():
                if not self.checkGPIO(pin):
                    continue
                try:
                    i = int(pin)
                    if value == "in":
                        self.setDirection(i, GPIO.IN)
                    elif value == "out":
                        self.setDirection(i, GPIO.OUT)
                    else:
                        print "Bad Direction"
                except ValueError:
                    print 'no int'

    def loop(self,ldata):#循环解析并执行命令
		if len(ldata)>0:
			for cmd_loop in ldata:
				cmd_name=cmd_loop.items()[0][0]
				val=cmd_loop.items()[0][1]
				if cmd_name=='pinval' and len(val)==2:
					if not self.checkGPIO(val[0]):
						continue
					try:
					    pin=int(val[0])
					    value=int(val[1])
					    if (value == 0):
						    self.setValue(pin, False)
					    elif (value == 1):
						    self.setValue(pin , True)
					    else:
						    print "Bad Value"
					except ValueError:
					    print 'no int'
	
				elif cmd_name=='sleep':
					try:
					    invt=float(val)
					    time.sleep(invt)
					except ValueError:
					    print 'no float'
			self.reply(self.replydata)
				
    def reply(self,rdata):#应答post提交回web
		if len(rdata)>0:
			pins=rdata
			data={}
			for pin in pins:#循环获取Pin的数据
				if not self.checkGPIO(pin):
					continue
				i = int(pin)
				mode = "ENABLED"
				direction = "out"
				value = 0
				if (self.GPIO_PINS[pin]["mode"] == GPIO.ALT):
					mode = "ALT"
				else:
					direction = self.getDirection(pin)
					value = self.getValue(pin)
				data['%d' % i]={
					"mode":mode,
					"direction":direction,
					"value":value
				}
			#提交数据
			self.http.posthttpdata('gpio',data)
			
    def setdata(self,sdata,ldata,rdata):
        self.loopdata=[]#clear
        self.setupdata=[]#clear
        self.replydata=[]#clear
        self.setup(sdata)
        self.setupdata=sdata
        self.loopdata=ldata
        self.replydata=rdata

