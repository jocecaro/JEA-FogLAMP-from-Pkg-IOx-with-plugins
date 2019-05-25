"""
For troubleshooting purposes we can call the b100modbus file directly after making
a few slight modifications to the file. This will allow us to call the code 
directly from a workstation and step through it while watching variables. Once
you have it working, you can put your code into the plugin and be reasonably
sure that it will work.
"""


from b100modbus import get_b100_readings

get_b100_readings("192.168.1.200", 502)