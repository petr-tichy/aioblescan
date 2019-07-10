#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# This application is an example on how to use aioblescan
#
# Copyright (c) 2017 François Wautier
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
import sys
import asyncio
import functools
import argparse
import re
import aioblescan as aiobs
from aioblescan.plugins import EddyStone
from aioblescan.plugins import RuuviWeather
from aioblescan.plugins import BlueMaestro
from aioblescan.plugins import Xiaomi
from hbmqtt.client import MQTTClient


def check_mac(val):
    try:
        if re.match("[0-9a-f]{2}([-:])[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", val.lower()):
            return val.lower()
    except:
        pass
    raise argparse.ArgumentTypeError("%s is not a MAC address" % val)

parser = argparse.ArgumentParser(description="Track BLE advertised packets")
parser.add_argument("-e", "--eddy", action='store_true', default=False,
                    help="Look specificaly for Eddystone messages.")
parser.add_argument("-m", "--mac", type=check_mac, action='append',
                    help="Look for these MAC addresses.")
parser.add_argument("-r","--ruuvi", action='store_true', default=False,
                    help="Look only for Ruuvi tag Weather station messages")
parser.add_argument("-b","--bluemaestro", action='store_true', default=False,
                    help="Look only for BlueMaestro messages")
parser.add_argument("-x","--xiaomi", action='store_true', default=False,
                    help="Look only for Xioomi messages")
parser.add_argument("-R","--raw", action='store_true', default=False,
                    help="Also show the raw data.")
parser.add_argument("-a","--advertise", type= int, default=0,
                    help="Broadcast like an EddyStone Beacon. Set the interval between packet in millisec")
parser.add_argument("-D","--device", type=int, default=0,
                    help="Select the hciX device to use (default 0, i.e. hci0).")
try:
    opts = parser.parse_args()
except Exception as e:
    parser.error("Error: " + str(e))
    sys.exit()

opts.plugins = []

def init_plugins():
    global opts
    if opts.bluemaestro:
        opts.plugins.append(BlueMaestro())

    if opts.xiaomi:
        opts.plugins.append(Xiaomi())

init_plugins()

def my_BLEScanRequesterFactory(queue):
    
    class my_BLEScanRequester(aiobs.BLEScanRequester):
        def __init__(self, queue=queue):
            self.queue = queue
            super()

        def data_received(self, data):
            global opts

            ev=aiobs.HCI_Event()
            xx=ev.decode(data)
            if opts.mac:
                goon = False
                mac= ev.retrieve("peer")
                for x in mac:
                    if x.val in opts.mac:
                        goon=True
                        break
                if not goon:
                    return

            if opts.raw:
                print("Raw data: {}".format(ev.raw_data))
            if opts.eddy:
                xx=EddyStone().decode(ev)
                if xx:
                    print("Google Beacon {}".format(xx))
            if opts.ruuvi:
                xx=RuuviWeather().decode(ev)
                if xx:
                    print("Weather info {}".format(xx))

            info = None
            for plugin in opts.plugins:
                x = plugin.decode(ev)
                if x:
                    info = x
                    break

            if info:
                self.queue.put_nowait(info)
                #print('Queue size: %s' % self.queue.qsize())
                #print('Enqued: %s' % info)

    return my_BLEScanRequester

try:
    mydev=int(sys.argv[1])
except:
    mydev=0


async def consumer(queue, mqtt_client):
    #running_tasks = []
    await mqtt_client.connect(uri='mqtt://192.168.8.10/')

    while True:
        message = await queue.get()
        #print('Queue len: %s' % queue.qsize())
        mac = message.get('mac_address')
        if mac:
            #user = await api_call()
            #print('Mac: %s' % mac)
            for t in ['temperature', 'humidity', 'dew_point', 'battery_level']:
                value = message.get(t)
                if not value:
                    continue
                topic = '/'.join(['state', 'sensors', mac, t])
                #print('Pub to %s, value %s' % (topic, value))
                mqtt_message = str(value).encode(encoding='utf-8')
                asyncio.ensure_future(mqtt_client.publish(topic, mqtt_message), loop=asyncio.get_event_loop())
                #print('task scheduled')
                #running_tasks.append(task)
                #print(running_tasks)
            #if running_tasks:
                #print('before await')
                #await asyncio.gather(running_tasks)
        else:
            print(message, file=sys.stderr)
        queue.task_done()


loop = asyncio.get_event_loop()
loop.set_debug(True)

queue = asyncio.Queue(maxsize = 5)

mqtt_config = dict()
mqtt_config['will'] = dict()
mqtt_config['will']['topic'] = 'will'
mqtt_config['will']['message'] = b'died'
mqtt_config['will']['retain'] = False
mqtt_config['will']['qos'] = 0
mqtt_client = MQTTClient(config=mqtt_config, loop=loop)

consumer_task = loop.create_task(consumer(queue, mqtt_client))

#First create and configure a raw socket
mysocket = aiobs.create_bt_socket(mydev)

#create a connection with the raw socket
#This used to work but now requires a STREAM socket.
#protocol_factory =loop.create_connection(aiobs.BLEScanRequester,sock=mysocket)
#Thanks to martensjacobs for this fix
protocol_factory = loop._create_connection_transport(mysocket,my_BLEScanRequesterFactory(queue=queue),None,None)
#Start it
transport, btctrl = loop.run_until_complete(protocol_factory)
#Attach your processing
#btctrl.process = functools.partial(my_process, queue=queue)

# if opts.advertise:
#     command = aiobs.HCI_Cmd_LE_Advertise(enable=False)
#     btctrl.send_command(command)
#     command = aiobs.HCI_Cmd_LE_Set_Advertised_Params(interval_min=opts.advertise,interval_max=opts.advertise)
#     btctrl.send_command(command)
#     command = aiobs.HCI_Cmd_LE_Set_Advertised_Msg(msg=EddyStone())
#     btctrl.send_command(command)
#     command = aiobs.HCI_Cmd_LE_Advertise(enable=True)
#     btctrl.send_command(command)

#Probe
async def queue_stat(queue):
    while True:
        #print(asyncio.Task.all_tasks())
        print(queue.qsize())
        await asyncio.sleep(1)
        
#loop.create_task(queue_stat(queue))
btctrl.send_scan_request()

try:
    loop.run_forever()
except KeyboardInterrupt:
    print('keyboard interrupt')
finally:
    print('closing event loop')
    btctrl.stop_scan_request()
    # command = aiobs.HCI_Cmd_LE_Advertise(enable=False)
    # btctrl.send_command(command)
    transport.close()
    consumer_task.cancel()
    loop.run_until_complete(asyncio.gather(consumer_task, mqtt_client.disconnect(), return_exceptions=True))
    #loop.stop()
    loop.close()
