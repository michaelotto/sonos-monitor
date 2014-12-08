sonos-monitor
=============

Automatically turns on a Yamaha Receiver (and switches it to the appropriate input) when a Sonos Connect starts playing.

What this does:

Start this as a daemon (sample init.d-script included). It connects to your Sonos Connect and your Yamaha Receiver. Whenever the Sonos Connect starts playing music, radio or whatever, it turns on the Receiver, switches to the appropriate input, sets the volume and changes to the Sound Program you want to (e.g. "5ch Stereo").

If the Receiver is already turned on, it just switches the input and leaves the rest alone.

If you set the standby time of the Receiver to 20 minutes, you'll have a decent instant-on solution for your Sonos Connect - it behaves just like one of Sonos' other players.

Optimized for minimum use of resources. I leave this running on a Raspberry Pi at my place. An A model should suffice. And it would still be bored 99% of the time.

Before installing it as a daemon, try it out first: Adapt the settings in the script below. Then just run the script. It'll auto-discover your Sonos Connect. If that fails (e.g. because you have more than one Connect in your home or for other reasons), you can use the UID of your Sonos Connect as the first and only parameter of the script. The script will output all UIDs neatly for your comfort.

Prerequisites:
- Your Yamaha Receiver has to be connected to the LAN.
- Both your Yamaha Receiver and your Sonos Connect have to use fixed IP
  addresses. You probably have to set this in your router (or whichever
  device is your DHCP).
- Your Yamaha Receiver's setting of "Network Standby" has to be "On".
  Otherwise the Receiver cannot be turned on from standby mode.

Software prerequisites:
- sudo pip install soco
