""" B100 Modbus code
This code has been modified slightly so that it can be called directly for troubleshooting.
See comments for changes.

This code specifically collects to readings from the B100 using the Modbus protocol, but 
it is intended to act as a reference implementation of a Modbus-based plugin for FogLAMP.

The b100 python module implements the functions required of a FogLAMP plugin like plugin_info,
plugin_init, plugin_poll, plugin_reconfigure, and plugin_shutdown. The function plugin_poll
is called by the FogLAMP scheduler to periodically collect new reading. The collection of the 
readings through the Modbus protocol was separated into this module to make the code easier to
maintain by encapsulating all of the Modbus code.

The b100 module's plugin_poll function calls get_b100_readings in this module. That fuction
returns the readings object containing the data.

This b100modbus module uses the PyModbus library to implement the Modbus communication.
Documentation and examples for this library are available at 
https://pymodbus.readthedocs.io/en/v1.3.2/index.html

This module uses the PyModbus synchronous methods. PyModbus also as asnyc methods available
if needed for better performance.
"""

import logging

from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from pymodbus.transaction import ModbusRtuFramer as ModbusFramer
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.exceptions import ModbusException, ModbusIOException, ParameterException

# The foglamp stuff will not be available to us when we run the code separately
# from foglamp.common import logger
# from foglamp.plugins.common import utils
# from foglamp.services.south import exceptions

# This variable will hold the pymodbus Modbus client object. It is initialized and maintained
# in get_b100_readings
modbus_client = None

# TROUBLESHOOTING
# We can't rely on the foglamp logger while running the code separately so we will just setup a basic
# logger
#_LOGGER = logger.setup(__name__, level=logging.INFO)
_LOGGER = logging.Logger(__name__, level=logging.INFO)
""" Setup the access to the logging system of FogLAMP """

def decode_and_scale_registers(registers, scaling_value):
    """ Converts unsigned int from Modbus device to a signed integer divided by the scaling_value 

    It is customary to read a 32-bit signed integer from two consecutive 16-bit Modbus registers
    and then divide that value by a power of ten to get a scaled final value. The B100 values should
    be divided by 1000.

    Word and Byte order vary by device. Experimentation with the B100 determined that the bytes are
    big endian, which is pretty normal. the word order, or order of the registers is little endian, which
    seems weird, except in the Modbus world, where it is pretty common.
    
    Use the Modbus Poll tool available at https://www.modbustools.com/modbus_poll.html for $129
    to test a device and determine byte and word orders.
    """
    decoder = BinaryPayloadDecoder.fromRegisters(registers, byteorder=Endian.Big, wordorder=Endian.Little)
    number = decoder.decode_32bit_int()
    number = number / scaling_value
    return number
    
def get_modbus_reading(reading_name, scaling_value, register_address, num_registers, unit):
    """ Poll the Modbus registers, decode, and scale the reading

        Any errors during readings will be logged to the FogLAMP log so that they may be seen in the
        FogLAMP GUI. We will also try to return reading values that help indicate the problem that 
        occurred when the reading was taken. We will try to approximate PI conventions for this
    """

    try:
        reading_registers = modbus_client.read_input_registers(register_address, num_registers,unit=unit)
        scaled_reading = decode_and_scale_registers(reading_registers.registers,scaling_value)
        return scaled_reading
    # OSIsoft would return "I/O Timeout" although the problem is not always a timeout so we will just say error instead    
    except ModbusIOException as ex:
        _LOGGER.exception('Modbus I/O exception reading {}: {}'.format(reading_name, ex))
        return('I/O error')
    # We will try to mimic the OSIsoft interface behavior which returns "configure" if a tag does not appear to be
    # configured correctly
    except ParameterException as ex:
        _LOGGER.exception('Modbus parameter exception reading {}: {}'.format(reading_name, ex))
        return('configure')
    except ModbusException as ex:
        _LOGGER.exception('Modbus exception reading {}: {}'.format(reading_name, ex))
        return ('modbus error')
    except Exception as ex:
        _LOGGER.exception('Exception reading {}: {}'.format(reading_name, ex))
        return('error')


def get_b100_readings(address, port):
    """
    The B100 FogLAMP plugin module calls this function to get the readings for the device.

    The address should be the IP address of the B100
    The Modbus TCP port should usually be 502
    """

    # This global modbus_client object should allow us to leave a continuous Modbus
    # connection open
    global modbus_client

    # This will open the Modbus connection to the B100 the first time that we call get_b100_readings. 
    # It will also reopen the connection if it has been closed 
    if modbus_client is None:
        try:                
            modbus_client = ModbusClient(address, port=port, framer=ModbusFramer)
        except ModbusIOException as ex:
            _LOGGER.exception('Modbus I/O exception opening B100 connection: {}'.format(ex))
        except ParameterException as ex:
            _LOGGER.exception('Modbus I/O exception opening B100 connection: {}'.format(ex))
        except ModbusException as ex:
             _LOGGER.exception('Modbus exception opening B100 connection: {}'.format(ex))
        except Exception as ex:
            _LOGGER.exception('Exception opening B100 connection: {}'.format(ex))

    # We are currently using the register values of the B100. If the SEL equipment acts as an intermediary then 
    # the registers and unit will need to be changed to what the SEL equipment makes available. Make sure to update the 
    # byte and word order and scaling value in decode_and_scale_registers if that changes as well.
    LTC_TANK_TEMP_REG = 216
    TOP_OIL_TEMP_REG = 268
    UNIT = 1
    SCALING_VALUE = 1000
    # In general you will always need to read two 16-bit register to get the 32-bit signed integer Modbus reading. This
    # will probably not change.
    NUM_REGISTERS_TO_READ = 2
    
    # Additional readings may be easily added here by getting additional modbus readings and adding them to the 
    # readings object below
    ltc_tank_temp = None
    top_oil_temp = None

    ltc_tank_temp = get_modbus_reading('LTC Tank Temp',SCALING_VALUE,LTC_TANK_TEMP_REG,NUM_REGISTERS_TO_READ,UNIT)
    top_oil_temp = get_modbus_reading('Top Oil Temp',SCALING_VALUE,TOP_OIL_TEMP_REG,NUM_REGISTERS_TO_READ,UNIT)
			
    # This readings object returns the values to FogLAMP where they are embedded inside a FogLAMP reading object
    # containing the asset name, a timestamp, and a GUID. We may include any arbitrary set of readings in this 
    # readings object including static meta-data, if desired.        
    readings = {
        'ltc_tank_temp': ltc_tank_temp,
        'top_oil_temp': top_oil_temp
        }

    # Return the readings object to the FogLAMP function plugin_poll function that called us.
    return readings

def close_connection():
    global modbus_client
    try:
        if modbus_client is not None:
            modbus_client.close()
            return('B100 Modbus client connection closed.')
    except:
        raise
    else:
        modbus_client = None
        return('B100 plugin shut down.')