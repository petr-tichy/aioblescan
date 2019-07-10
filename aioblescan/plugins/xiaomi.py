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


import aioblescan as aiobs
from .generic import Device, DevicesDict, ReadingDescriptor, AttributeDescriptor, BaseDescriptor

XIAOMI_UUID = b"\xfe\x95"

class XiaomiDevice(Device):
    temperature = ReadingDescriptor('temperature', precision=1, signed=True, scale=-1, ttl=3)
    humidity = ReadingDescriptor('humidity', precision=0, signed=False, scale=-1)
    battery_level = ReadingDescriptor('battery_level', precision=0, signed=False, scale=0)

    mac_address = AttributeDescriptor('mac_address')
    name = AttributeDescriptor('name')

class Xiaomi(object):
    """Class defining the content of an Xiaomi advertisement.
    """

    def __init__(self):
        self.devices = DevicesDict(XiaomiDevice)

    def decode(self,packet):
        rssi=packet.retrieve("rssi")
        # if rssi:
        #     result["rssi"]=rssi[-1].val

        found = False
        for x in packet.retrieve("Advertised Data"):
            for uuid in x.retrieve("Service Data uuid"):
                if XIAOMI_UUID == uuid:
                    found = x
                    break
            if found:
                break

        if not found:
            return None

        adv_payload = found.retrieve("Adv Payload")[0]

        if not adv_payload or len(adv_payload) <= 13:
            # Packet too short
            #print('Adv Payload too short')
            return None

        val = adv_payload.val
        if not (val[0]==0x50 and val[1]==0x20 and val[2]==0xaa and val[3]==0x01):
            return None

        payload_length = val[13]
        if payload_length != len(val) - 14:
            # Data length doesn't match
            # print('Invalid payload length %s vs %s' % (payload_length, len(val) - 14))
            return None

        # result["message_number"] = val[4]

        mac_addr = aiobs.MACAddr(None)
        mac_addr.decode(val[5:11])
        mac_addr = mac_addr.val
        if mac_addr != packet.retrieve("peer")[0].val:
            # print("Packet source MAC doesn't match indicated MAC")
            return None

        state = self.devices[mac_addr]

        payload_type = val[11]
        if payload_type == 0x0d and payload_length == 4:
            # Temperature & Humidity
            state.temperature = val[14:16]
            state.humidity = val[16:18]
        elif payload_type == 0x0a and payload_length == 1:
            # Battery level
            state.battery_level = val[14:15]
        elif payload_type == 0x06 and payload_length == 2:
            # Humidity
            state.humidity = val[14:16]
        elif payload_type == 0x04 and payload_length == 2:
            # Temperature
            state.temperature = val[14:16]
        else:
            # print('Invalid packet type %s or length' % payload_type)
            # adv_payload.show()
            return None

        if state.get('changed') is not None:
            return state

        return None
