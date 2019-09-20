""" SELTac Modbus code

This code specifically collects to readings from the SEL-RTac using the Modbus protocol, but 
it is intended to act as a reference implementation of a Modbus-based plugin for FogLAMP.

The SELRtac python module implements the functions required of a FogLAMP plugin like plugin_info,
plugin_init, plugin_poll, plugin_reconfigure, and plugin_shutdown. The function plugin_poll
is called by the FogLAMP scheduler to periodically collect new reading. The collection of the 
readings through the Modbus protocol was separated into this module to make the code easier to
maintain by encapsulating all of the Modbus code.

The selrtac module's plugin_poll function calls get_sel_readings in this module. That fuction
returns the readings object containing the data.

This selmodbus module uses the PyModbus library to implement the Modbus communication.
Documentation and examples for this library are available at 
https://pymodbus.readthedocs.io/en/v1.3.2/index.html

This module uses the PyModbus synchronous methods. PyModbus also as asnyc methods available
if needed for better performance.
"""

import logging

from enum import Enum
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
#from pymodbus.transaction import ModbusRtuFramer as ModbusFramer
from pymodbus.transaction import ModbusSocketFramer as ModbusFramer
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.exceptions import ModbusException, ModbusIOException, ParameterException

from foglamp.common import logger
from foglamp.plugins.common import utils
from foglamp.services.south import exceptions

# This variable will hold the pymodbus Modbus client object. It is initialized and maintained
# in get_sel_readings
modbus_client = None

# This class is used as an enum to define the size of the value in the
#  register (16 bit or 32 bit value)
class data_size_enum(Enum):
     _16bit = 1
     _32bit = 2

_LOGGER = logger.setup(__name__, level=logging.INFO)
""" Setup the access to the logging system of FogLAMP """
    

def decode_and_scale_registers(registers, data_size, scaling_value):
    """ Converts unsigned int from Modbus device to a signed integer divided by the scaling_value 

    It is customary to read a 32-bit signed integer from two consecutive 16-bit Modbus registers
    and then divide that value by a power of ten to get a scaled final value. The SEL values should
    be divided by 10.

    Word and Byte order vary by device. Experimentation with the SEL determined that the bytes are
    big endian, which is pretty normal. the word order, or order of the registers is little endian, which
    seems weird, except in the Modbus world, where it is pretty common.
    
    Use the Modbus Poll tool available at https://www.modbustools.com/modbus_poll.html for $129
    to test a device and determine byte and word orders.
    """
    if data_size is data_size_enum._16bit:
        decoder = BinaryPayloadDecoder.fromRegisters(registers, byteorder=Endian.Big)
        number = decoder.decode_16bit_int()
    else:
        decoder = BinaryPayloadDecoder.fromRegisters(registers, byteorder=Endian.Big, wordorder=Endian.Little)
        number = decoder.decode_32bit_int()

    number = number / scaling_value
    return number

def get_modbus_reading(reading_name, data_size, scaling_value, register_address, num_registers, unit):
    """ Poll the Modbus registers, decode, and scale the reading

        Any errors during readings will be logged to the FogLAMP log so that they may be seen in the
        FogLAMP GUI. We will also try to return reading values that help indicate the problem that 
        occurred when the reading was taken. We will try to approximate PI conventions for this
    """

    try:
        reading_registers = modbus_client.read_input_registers(register_address, num_registers,unit=unit)
        scaled_reading = decode_and_scale_registers(reading_registers.registers, data_size, scaling_value)
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
        _LOGGER.exception('reading_registers value is: {}').format(reading_registers)        
        return('error')

def get_sel_readings(address, port, 
                        b100_ltc_tank_temp_reg, 
                        b100_top_oil_temp_reg,
                        qualitrol_top_oil_reg,
                        qualitrol_ltc_tank_reg,
                        qualitrol_ltc_tap_position_reg
                        ):
    """
    The SEL FogLAMP plugin module calls this function to get the readings for the device.

    The address should be the IP address of the SEL
    The Modbus TCP port should usually be 502
    """

    # This global modbus_client object should allow us to leave a continuous Modbus
    # connection open
    global modbus_client

    # This will open the Modbus connection to the SEL the first time that we call get_sel_readings. 
    # It will also reopen the connection if it has been closed 
    if modbus_client is None:
        try:                
            modbus_client = ModbusClient(address, port=port, framer=ModbusFramer)
        except ModbusIOException as ex:
            _LOGGER.exception('Modbus I/O exception opening SEL connection: {}'.format(ex))
        except ParameterException as ex:
            _LOGGER.exception('Modbus I/O exception opening SEL connection: {}'.format(ex))
        except ModbusException as ex:
             _LOGGER.exception('Modbus exception opening SEL connection: {}'.format(ex))
        except Exception as ex:
            _LOGGER.exception('Exception opening SEL connection: {}'.format(ex))

    try:
        modbus_client_connected = modbus_client.connect()
        if modbus_client_connected:
            _LOGGER.info('Modbus TCP Client is connected. %s:%df', address, port)
        else:
            _LOGGER.execption('Modbus TCP Connection failed!')
    except:
        _LOGGER.warn('Failed to connect! Modbus TCP Host %s on port %d', address, port)


    # We are currently using the register values of the SEL. If the SEL equipment acts as an intermediary then 
    # the registers and unit will need to be changed to what the SEL equipment makes available. Make sure to update the 
    # byte and word order and scaling value in decode_and_scale_registers if that changes as well.
    UNIT = 1
    QUALITROL_SCALING_VALUE = 10
    B100_SCALING_VALUE = 1000
    # In general you will always need to read one 32-bit register to get the 32-bit signed integer Modbus reading. This
    # will probably not change.
    SINGLE_REGISTERS_TO_READ = 1
    DOUBLE_REGISTERS_TO_READ = 2

    # Additional readings may be easily added here by getting additional modbus readings and adding them to the 
    # readings object below
    b100_ltc_tank_temp = None
    b100_top_oil_temp = None
    qualitrol_ltc_tank_temp = None
    qualitrol_top_oil_temp = None
    qualitrol_tap_changer_position = None

    b100_ltc_tank_temp = get_modbus_reading('B100 LTC Tank Temp', 
                                            data_size_enum._32bit, 
                                            B100_SCALING_VALUE, 
                                            b100_ltc_tank_temp_reg, 
                                            DOUBLE_REGISTERS_TO_READ, 
                                            UNIT)
    b100_top_oil_temp = get_modbus_reading('B100 Top Oil Temp', 
                                            data_size_enum._32bit, 
                                            B100_SCALING_VALUE, 
                                            b100_top_oil_temp_reg, 
                                            DOUBLE_REGISTERS_TO_READ, 
                                            UNIT)    
    qualitrol_ltc_tank_temp = get_modbus_reading('Qualitrol LTC Tank Temp', 
                                            data_size_enum._16bit, 
                                            QUALITROL_SCALING_VALUE, 
                                            qualitrol_ltc_tank_reg, 
                                            SINGLE_REGISTERS_TO_READ, 
                                            UNIT)
    qualitrol_top_oil_temp = get_modbus_reading('Qualitrol Top oil Tank Temp', 
                                            data_size_enum._16bit, 
                                            QUALITROL_SCALING_VALUE, 
                                            qualitrol_top_oil_reg, 
                                            SINGLE_REGISTERS_TO_READ, 
                                            UNIT)
    qualitrol_tap_changer_position = get_modbus_reading('Qualitrol Tap changer position', 
                                            data_size_enum._16bit, 
                                            QUALITROL_SCALING_VALUE, 
                                            qualitrol_ltc_tap_position_reg, 
                                            SINGLE_REGISTERS_TO_READ, 
                                            UNIT)
    # tap changer needs to be rounded up.
    qualitrol_tap_changer_position = round(qualitrol_tap_changer_position)

			
    # This readings object returns the values to FogLAMP where they are embedded inside a FogLAMP reading object
    # containing the asset name, a timestamp, and a GUID. We may include any arbitrary set of readings in this 
    # readings object including static meta-data, if desired.        

    readings = {
                'B100.ltc_tank_temp': b100_ltc_tank_temp,
                'B100.top_oil_temp': b100_top_oil_temp,
                'Qualitrol.ltc_tank_temp': qualitrol_ltc_tank_temp,
                'Qualitrol.top_oil_temp': qualitrol_top_oil_temp,
                'Qualitrol.tap_change_position': qualitrol_tap_changer_position
        }
    
    # Return the readings object to the FogLAMP function plugin_poll function that called us.
    return readings

def close_connection():
    global modbus_client
    try:
        if modbus_client is not None:
            modbus_client.close()
            return('SEL Modbus client connection closed.')
    except:
        raise
    else:
        modbus_client = None
        return('SEL plugin shut down.')
