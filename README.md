# pyDPS5315
python interface to the ELV DPS 5315 power supply. It allows to
 * read the latest voltage levels and currents
 * set target/limiting voltages and currents
 * set the modes Master/Slave/Dual/Series and activate/standby the output
so pretty much everything you can do with the physical interface, except for the internal memory of the presets. But this also doesnt work with the windows control application. 
One advantage compared to the windows app is that you can use pyDPS5315 as a voltage logging tool. This even works in standby mode, so it acts as a volt meter.

How to install:
Just it somewhere and make sure you have the crcmod python package. If not you can install it via 
pip install crcmod

how to use:
If you under Linux and your are lucky you just start it with 
python dps5315.py to have a stand alone application that prints the latest status of the dps.
If this doesnt work you probably have to a adjust the serial port at
"connect(putyourserialporthere)"
