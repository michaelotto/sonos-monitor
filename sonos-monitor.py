#!/usr/bin/python

# -*- coding: utf-8 -*-

# What this does:
#
# Start this as a daemon. It connects to your Sonos Connect and your Yamaha
# Receiver. Whenever the Sonos Connect starts playing music, radio or whatever,
# it turns on the Receiver, switches to the appropriate input, sets the volume
# and changes to the Sound Program you want to (e.g. "5ch Stereo").
#
# If the Receiver is already turned on, it just switches the input and leaves
# the rest alone.
#
# If you set the standby time of the Receiver to 20 minutes, you'll have a
# decent instant-on solution for your Sonos Connect - it behaves just like
# one of Sonos' other players.
#
# Optimized for minimum use of resources. I leave this running on a Raspberry
# Pi at my place.
#
# Before installing it as a daemon, try it out first: Adapt the settings in the
# script below. Then just run the script. It'll auto-discover your Sonos
# Connect. If that fails (e.g. because you have more than one Connect in your
# home or for other reasons), you can use the UID of your Sonos Connect as the
# first and only parameter of the script. The script will output all UIDs
# neatly for your comfort.
#
# Prerequisites:
# - Your Yamaha Receiver has to be connected to the LAN.
# - Both your Yamaha Receiver and your Sonos Connect have to use fixed IP
#   addresses. You probably have to set this in your router (or whichever
#   device is your DHCP).
# - Your Yamaha Receiver's setting of "Network Standby" has to be "On".
#   Otherwise the Receiver cannot be turned on from standby mode.
#
# Software prerequisites:
# - sudo pip install soco



import os
import sys
import time
import re
import urllib, urllib2
import telnetlib
import soco
import Queue
import signal
from datetime import datetime


# --- Please adapt these settings ---------------------------------------------

YAMAHA_IP       = '192.168.2.23'            # IP address of your Yamaha Receiver. Look it up in your router or set it in the Receiver menu.
YAMAHA_PORT     = 50000                     # Port your Yamaha Receiver listens to (should be 50000 unless you changed it)
YAMAHA_INPUT    = 'AV1'                     # Name of your Receiver's input the Sonos Connect is connected to. Should be one
                                            # of AV1, AV2, ..., HDMI1, HDMI2, ..., AUDIO1, AUDIO2, ..., TUNER, PHONO, V-AUX, DOCK,
                                            # iPod, Bluetooth, UAW, NET, Napster, PC, NET RADIO, USB, iPod (USB) or the like.
                                            # Don't use an input name you set yourself in the Receiver's setup menu.
YAMAHA_VOLUME   = -20.0                     # Volume the Receiver is set to when started. Set to None if you don't want to change it.
YAMAHA_SOUNDPRG = '5ch Stereo'              # DSP Sound Program to set the Receiver to when started. Set to None if you don't want to change it.
                                            # Should be one of Standard, 2ch Stereo, 5ch Stereo, 7ch Stereo, Music Video, Hall in Munich,
                                            # Hall in Vienna, Chamber, Cellar Club, The Roxy Theatre, The Bottom Line, Sports, Action Game,
                                            # Roleplaying Game, Spectacle, Sci-Fi, Adventure, Drama, Mono Movie, Surround Decoder or the like.



# basic in/out with the receiver

def _yamaha_send_receive(out):
    rec = ''

    try:
        tn = telnetlib.Telnet(YAMAHA_IP, YAMAHA_PORT, 10)
        tn.write(out + "\r\n")
        rec = tn.read_until("\r\n", 5)
        tn.close()
    except Exception as e:
        print u"Connecting to Yamaha Receiver failed: {}".format(e).encode('utf-8')

    return rec[0:-2]

def yamaha_get_value(variable):
    return _yamaha_send_receive("@{}=?".format(variable))[len(variable)+2:]

def yamaha_set_value(variable, value):
    cv = yamaha_get_value(variable)

    # set the value only when it is different from the current value
    # because otherwise the receiver won't answer and then you're
    # timeout-ing waiting for the answer ...
    if str(cv) != str(value):
        print u"Setting Yamaha {} to {} (was: {})".format(variable, value, cv).encode('utf-8')
        _yamaha_send_receive("@{}={}".format(variable, value))

def auto_flush_stdout():
    unbuffered = os.fdopen(sys.stdout.fileno(), 'w', 0)
    sys.stdout.close()
    sys.stdout = unbuffered

def handle_sigterm(*args):
    global break_loop
    print u"SIGTERM caught. Exiting gracefully.".encode('utf-8')
    break_loop = True



# --- Discover SONOS zones ----------------------------------------------------

if len(sys.argv) == 2:
    connect_uid = sys.argv[1]
else:
    connect_uid = None

print u"Discovering Sonos zones".encode('utf-8')

match_ips   = []
for zone in soco.discover():
    print u"   {} (UID: {})".format(zone.player_name, zone.uid).encode('utf-8')

    if connect_uid:
        if zone.uid.lower() == connect_uid.lower():
            match_ips.append(zone.ip_address)
    else:
        # we recognize Sonos Connect and ZP90 by their hardware revision number
        if zone.get_speaker_info().get('hardware_version')[:4] == '1.1.':
            match_ips.append(zone.ip_address)
            print u"   => possible match".encode('utf-8')
print

if len(match_ips) != 1:
    print u"The number of Sonos Connect devices found was not exactly 1.".encode('utf-8')
    print u"Please specify which Sonos Connect device should be used by".encode('utf-8')
    print u"using its UID as the first parameter.".encode('utf-8')
    sys.exit(1)

sonos_device    = soco.SoCo(match_ips[0])
sub             = sonos_device.avTransport.subscribe()

# --- Initial Yamaha status ---------------------------------------------------

print u"Yamaha Power status:  {}".format(yamaha_get_value('MAIN:PWR')).encode('utf-8')
print u"Yamaha Input select:  {}".format(yamaha_get_value('MAIN:INP')).encode('utf-8')
print u"Yamaha Volume:        {}".format(yamaha_get_value('MAIN:VOL')).encode('utf-8')
print u"Yamaha Sound Program: {}".format(yamaha_get_value('MAIN:SOUNDPRG')).encode('utf-8')
print

# --- Main loop ---------------------------------------------------------------

break_loop      = False
last_status     = None

# catch SIGTERM gracefully
signal.signal(signal.SIGTERM, handle_sigterm)
# no bufferd STDOUT so we can use it for logging
auto_flush_stdout()

while True:
    try:
        event   = sub.events.get(timeout=10)
        status  = event.variables.get('transport_state')

        if not status:
            print u"{} Invalid SONOS status: {}".format(datetime.now(), event.variables).encode('utf-8')

        if last_status != status:
            print u"{} SONOS play status: {}".format(datetime.now(), status).encode('utf-8')

        if last_status != 'PLAYING' and status == 'PLAYING':
            if not yamaha_get_value('MAIN:PWR') == 'On':
                yamaha_set_value('MAIN:PWR', 'On')
                if YAMAHA_VOLUME is not None:
                    yamaha_set_value('MAIN:VOL', float(YAMAHA_VOLUME))
                if YAMAHA_SOUNDPRG is not None:
                    yamaha_set_value('MAIN:SOUNDPRG', YAMAHA_SOUNDPRG)
            yamaha_set_value('MAIN:INP', YAMAHA_INPUT)

        last_status = status
    except Queue.Empty:
        pass
    except KeyboardInterrupt:
        handle_sigterm()

    if break_loop:
        sub.unsubscribe()
        soco.events.event_listener.stop()
        break
