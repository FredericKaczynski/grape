import smbus
from RPi import GPIO
from time import sleep
import logging


BUSES = [0, 1]
DSP_INTERUPT_PIN = 17
TMP_INTERUPT_PIN = 27

# Currently Unused, this should be the base address for the PiDevice Class
# E.g. second pi of stack 013 in octal (bus 1, stack 3):
# 3 + RASP_CLASS_ADDRESSES[1] == 0x5b 
RASP_CLASS_ADDRESSES = [0x50, 0x58, 0x60, 0x68, 0x70, 0x78]


_log = logging.getLogger(__name__)


def _reverse_bits_of_byte(b):
    return (((b * 0x0802 & 0x22110) |(b * 0x8020 & 0x88440)) * 0x10101 >> 16) & 0xff

def big2little_endian(w):
    return ((w & 0xff) << 8) | ((w & 0xff00) >> 8)

def get_device_name(device):
    if device == PowerSwitch:
        return "Power Switch"
    elif device == Temperature:
        return "Temperature Meter"
    elif device == PowerMeter:
        return "Power Meter"

class ButtonHandler(object):
    def on_pressed(self, display):
        pass
    def on_left(self, display):
        pass
    def on_right(self, display):
        pass

class ButtonPrinter(ButtonHandler):
    def on_pressed(self, display):
        print("pressed")
    def on_left(self, display):
        print("left")
    def on_right(self, display):
        print("right")

class Stack(object):
    def __init__(self, bus, prefix):
        self._prefix = prefix
        self._bus = bus
        self.devices = {}
        for dev in STACK_DEVICES:
            if dev.probe(bus, prefix):
                self.devices[dev] = dev(bus, prefix)
        for dev in self.devices.itervalues():
            try:
                dev.setup()
            except Exception as e:
                _log.error("Unable to setup %s: %s", dev, e)
    def __getitem__(self, kind):
        return self.devices[kind]

class I2CDevice(object):
    CLASS_ADDRESS = 0x00 # Should be defined in each subclass
    PROBE_WRITE_QUICK = False

    def __init__(self, bus, prefix):
        self._bus = bus
        self._address = self.make_address(prefix)

    def __str__(self):
        return "{0}[0x{1}]".format(self.__class__.__name__, self._address)

    def setup(self):
        pass

    def read_byte(self, register = 0x00):
        return self._bus.read_byte_data(self._address, register)
    def write_byte(self, register, value):
        self._bus.write_byte_data(self._address, register, value)
    # TODO use big2little_endian here after, but check usage
    def read_word(self, register):
        return self._bus.read_word_data(self._address, register)
    def write_word(self, register, value):
        self._bus.write_word_data(self._address, register, value)

    def get_address(self):
        return self._address

    @classmethod
    def make_address(cls, prefix):
        return cls.CLASS_ADDRESS + prefix

    @classmethod
    def probe(cls, bus, prefix):
        address = cls.make_address(prefix)
        try:
            if cls.PROBE_WRITE_QUICK:
                bus.write_quick(address)
            else:
                bus.read_byte(address)
            return True
        except:
            return False

class PowerSwitch(I2CDevice):
    CLASS_ADDRESS = 0x38
    L2P = [1, 6, 3, 2, 5, 4]
    PROBE_WRITE_QUICK = False
    # FIXME autodetect should use write quick ? but with a value of 0xff
    # Maybe this is not the best way to init this component

    def setup(self):
        self._pin = 0xff # FIXME this is an ugly hack to fix startup
    def update(self):
        self._pin = self.read_byte()
    def write(self):
        self.write_byte(0x00, self._pin)
    def status(self):
        s = []
        for i in range(len(self.L2P)):
            if self[i]:
                s.append(i)
        return s
    def __getitem__(self, idx):
        return self._pin & (1 << self.L2P[idx]) == 0
    def __setitem__(self, idx, state):
        if state:
            self._pin &= ~(1 << self.L2P[idx])
        else:
            self._pin |= (1 << self.L2P[idx])
        self.write()
    def start_all(self):
        for idx in range(len(self.L2P)):
            self._pin &= ~(1 << self.L2P[idx])
        self.write()
    def stop_all(self):
        for idx in range(len(self.L2P)):
            self._pin |= 1 << self.L2P[idx]
        self.write()


class Temperature(I2CDevice):
    CLASS_ADDRESS = 0x48
    THM_REG = 0x00

    def get(self):
        data = self.read_word(self.THM_REG)
        if data & 0x0080:
            return - (~(data & 0x7F)) - (0.5 if data & 0x8000 else 0.0)
        else:
            return (data & 0xff) + (0.5 if 0x8000 else 0.0)

class PowerMeter(I2CDevice):
    CLASS_ADDRESS = 0x40

    CALIBRATION_VALUE = 0x0819 # This may be the right value, but has never been checked
    CURRENT_DIVIDER = (1000 * 50)

    CONF_REG = 0x00
    CALIB_REG = 0x05
    SHUNT_REG = 0x01
    VOLTAGE_REG = 0x02
    POWER_REG = 0x03
    CURRENT_REG = 0x04

    SHUNT_BUS_CONTINUOUS = 0x0007
    SADCRES_12B_1S = 0x0018
    BADCRES_12B = 0x0400
    GAIN_320MV = 0x1800
    GAIN2_80MV = 0x0800
    BUS_VOLTAGE_RANGE_32V = 0x2000

    def setup(self):
        # print("{0:x}".format(self.config_value()))
        self.write_word(self.CONF_REG, big2little_endian(self.config_value()))
        self.write_word(self.CALIB_REG, big2little_endian(self.CALIBRATION_VALUE))

    def config_value(self):
        return self.SHUNT_BUS_CONTINUOUS \
                | self.SADCRES_12B_1S \
                | self.BADCRES_12B \
                | self.GAIN2_80MV \
                | self.BUS_VOLTAGE_RANGE_32V

    def current(self): # in mA
        return big2little_endian(self.read_word(self.CURRENT_REG))
        #return self.read_word(self.CURRENT_REG) # / self.CURRENT_DIVIDER
    def voltage(self): # in mV
        return (big2little_endian(self.read_word(self.VOLTAGE_REG)) >> 3) * 4
        #return (self.read_word(self.VOLTAGE_REG) >> 3) * 4
    def power(self): # in mW
        return big2little_endian(self.read_word(self.POWER_REG))
        #return self.read_word(self.POWER_REG) / 2
    def shunt(self):
        return (big2little_endian(self.read_word(self.SHUNT_REG)) >> 3) * 4

class Display(I2CDevice):
    CLASS_ADDRESS = 0x20
    DEFAULT_PREFIX = 0x00
    PROBE_WRITE_QUICK = True

    RED = 0x08
    GREEN = 0x10

    DELAY = 0.004
    SHORT_DELAY = 0.001

    BTN_PRESS = 0x20
    BTN_LEFT_RIGHT = 0x40 | 0x80
    BUTTONS = BTN_PRESS | BTN_LEFT_RIGHT
    _LEFT_SUCCESSOR = [1, 3, 0, 2]

    CFG_DISPLAY = 0x08
    DISPLAY = 0x04
    CURSOR = 0x02
    BLINK = 0x01

    SCROLL_RIGHT = 0x02
    SCROLL_DISPLAY = 0x01

    def setup(self):
        # PCA init
        self.write_byte(0x04, 0x00)
        self.write_byte(0x05, 0x00)
        self.write_byte(0x06, 0x00)
        self.write_byte(0x07, 0xE0)

        # LCD init
        sleep(0.015)
        # Ensure that buttons are output are all zeros
        self._write_state(self._read_state() & 0xF8)
        # Init proc : send 3 x 0x30
        self._lcd(0x30)
        self._lcd(0x30)
        self._lcd(0x30)
        self._lcd(0x38) # 0x30 = 8bit mode; 0x08 = screen physical properties
        self.lcd_state()
        self.clear_screen()
        self.scroll(self.SCROLL_RIGHT)

        self.btn_handler = ButtonHandler()
        self._status = self.btn_status()

        # Interupt
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(DSP_INTERUPT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(DSP_INTERUPT_PIN, GPIO.RISING, callback = self.interrupt)

    def led(self, index, state):
        state = self._read_state()
        if state:
            self._write_state(state &~ index)
        else:
            self._write_state(state | index)

    def home(self, line = 0):
        if line == 0:
            self._lcd(0x02)
        elif line == 1:
            self._lcd(0x40 | 0x80)

    def position(self, line, pos):
        line = 1 if line > 1 else line
        pos = 39 if pos > 39 else pos
        pos += line * 0x40
        self._lcd(pos | 0x80)

    def lcd_state(self, status = DISPLAY | CURSOR | BLINK):
        self._lcd(status & (self.CURSOR | self.BLINK | self.DISPLAY) | self.CFG_DISPLAY)

    def clear_screen(self):
        self._lcd(0x01)

    def scroll(self, direction):
        self._lcd(0x04 | (direction & (self.SCROLL_DISPLAY | self.SCROLL_RIGHT)))

    def shift_screen(self):
        self._lcd(0x1F)

    def unshift_screen(self):
        self._lcd(0x18)

    def lcd_status(self):
        return self.read_byte(0x01) & 0x1C

    def btn_status(self):
        return self.read_byte(0x01) & self.BUTTONS

    def print_str(self, msg):
        # TODO ensure that msg has less than 40 char.
        for c in msg:
            self.print_char(ord(c))

    def print_at(self, line, pos, char):
        self.position(line, pos)
        self.print_char(ord(char[0]))

    def print_char(self, char):
        state = self._read_state()
        self._write_state(state | 0x04)
        self.write_byte(0x02, _reverse_bits_of_byte(char))
        self._lcd_enable()
        self._write_state(state &~ 0x04)

    def interrupt(self, channel):
        p_state = self._status
        state = self._status = self.btn_status()
        #print("interrupt {0}".format(p_state != state))
        if self.btn_handler is None: return
        if state & self.BTN_PRESS: self.btn_handler.on_pressed(self)
        state = (state & self.BTN_LEFT_RIGHT) >> 6 # FIXME function or constant for this
        p_state = (p_state & self.BTN_LEFT_RIGHT) >> 6
        if state != p_state:
            if self._LEFT_SUCCESSOR[p_state] == state:
                self.btn_handler.on_left(self)
            else:
                self.btn_handler.on_right(self)

    def _lcd(self, instr):
        self.write_byte(0x02, _reverse_bits_of_byte(instr))
        sleep(self.DELAY)
        self._lcd_enable()
        sleep(self.DELAY)
    def _lcd_enable(self):
        state = self._read_state()
        self._write_state(state | 0x01)
        sleep(self.SHORT_DELAY)
        self._write_state(state & ~0x01)
    def _reset(self):
        self.write_byte(0x03, 0x03)
    def _read_state(self):
        return self.read_byte(0x03)
    def _write_state(self, value):
        self.write_byte(0x03, value)
    def _config_rw(self):
        self.write_byte(0x03, 0x02)


STACK_DEVICES = [PowerSwitch, Temperature, PowerMeter]


def get_stacks():
    buses = {}
    stacks = {}
    display = None

    for bus_id in BUSES:
        try:
            _log.debug("Probing SMBus %d.", bus_id)
            bus = smbus.SMBus(bus_id)
            buses[bus_id] = bus
            _log.debug("SMBus %d detected.", bus_id)
        except:
            _log.warn("SMBus %d not enabled.", bus_id)

    for bid, bus in buses.items():
        _log.debug("Probing display on bus %d.", bid)
        if Display.probe(bus, Display.DEFAULT_PREFIX):
            display = Display(bus, Display.DEFAULT_PREFIX)
            display.setup()
            _log.debug("Display found on bus %d.", bid)
        else:
            _log.debug("Display on bus %d not found.", bid)
        for sid in range(8):
            try:
                _log.debug("Probing stack %d on bus %d.", sid, bid)
                bus.read_byte(PowerSwitch.make_address(sid))
                stacks[8*bid + sid] = Stack(bus, sid)
                _log.debug("stack %d on bus %d detected.", sid, bid)
            except Exception as e:
                _log.debug("stack %d on bus %d not found.", sid, bid)

    return buses, stacks, display
