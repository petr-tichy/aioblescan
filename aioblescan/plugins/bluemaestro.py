#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# This file deal with RuuviTag formated message
#
# Copyright (c) 2017 François Wautier
#
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies
# or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR
# IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

import aioblescan as aios

# Ruuvi tag stuffs

class BlueMaestro(object):
    """Class defining the content of an Ruuvi Tag advertisement.


    """

    def __init__(self):
        pass

    def decode(self,packet):
        #Look for Ruuvi tag URL and decode it
        result={}
        rssi=packet.retrieve("rssi")
        if rssi:
            result["rssi"]=rssi[-1].val
        url=packet.retrieve("Payload for mfg_specific_data")
        if url:
            val=url[0].val
            if val[0]==0x33 and val[1]==0x01 and val[2]==0x17:
                #Looks just right
                result["mac_address"]=packet.retrieve("peer")[0].val
                val=val[2:]
                result["battery_level"]=val[1]
                result["logging_interval"]=int.from_bytes(val[2:4], "big")
                result["log_count"]=int.from_bytes(val[4:6], "big")
                result["temperature"]=int.from_bytes(val[6:8], "big", signed=True)/10
                result["humidity"]=int.from_bytes(val[8:10], "big", signed=True)/10
                result["dew_point"]=int.from_bytes(val[10:12], "big", signed=True)/10
                result["mode"]=val[12]
                result["breach_count"]=val[13]
                result["name"]=str(packet.retrieve("Complete Name")[0].val, 'utf-8', 'ignore')
                return result
        else:
            return None
