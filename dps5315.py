from __future__ import print_function
import crcmod
import serial
from time import sleep
from struct import pack
import threading


crc16 = crcmod.mkCrcFun(poly=0x18005, rev=False, initCrc=0x800D, xorOut=0x0000)

STX = '\x02' # Start symbol
ETX = '\x03' # End symbol
ACK = '\x06'

MODE_SERIES           = 0
MODE_DUAL             = 1
MODE_MASTER_SLAVE     = 3
MODE_SLAVE_STANBY_ON  = 4
MODE_MASTER_STANBY_ON = 8
MODE_REMOTE           = 16
MODE_LOCK             = 32
MODE_CALIBRATION      = 64 #not completely shure this is calibration
MODE_ERROR            = 128

CONTROL_MV = 1
CONTROL_MI = 2
CONTROL_SV = 4
CONTROL_SI = 8
CONTROL_OVERTEMP_ENDSTUFE = 16
CONTROL_OVERTEMP_TRAFO = 32

master_version = None
slave_version = None
mode = None
control_mode = None
mv = 0
mi = 0
sv = 0
si = 0
mv_limit = 0
mi_limit = 0
sv_limit = 0
si_limit = 0
temp_endstufe = None
temp_trafo = None


class SerialReader(threading.Thread):
    def __init__(self):
        print('create thread')
        threading.Thread.__init__(self)
        
        self.exitFlag = False
        
    def run(self):
        while True:
            getData()
            sleep(0.2)
            if self.exitFlag:
                break

    def exit(self):
        self.exitFlag = True


def raw2hexstring(bytestring, separator=''):
    return separator.join('%X'%ord(c) for c in bytestring)

def sendInstruction(instruction):
    if DEBUG:
        print('TX: ', end='')
        print(instruction)
    instruction += pack('!H', crc16(instruction))
    instruction = instruction.replace(STX, '\x10\x82').replace(ETX, '\x10\x83')
    line = STX + instruction + ETX
    ser.write(line)

def receiveResponse():
    sleep(0.1)
    frame = ''
    while True:
        ch = ser.read()
        frame += ch
        if ch == ETX:
            break
    
    msg = frame.replace(STX, '').replace(ETX, '').replace('\x10\x82', STX).replace('\x10\x83', ETX)
    if msg[0] == ACK:
        return msg
    else:
        crc = crc16(msg[:-2])
        crc_ok = (pack('!H', crc) == msg[-2:])
        if not crc_ok:
            print('(CRC ERROR)', raw2hexstring(msg, ' '), ', %X %X'%(ord(msg[-2]), ord(msg[-1])), ', %X'%crc)
            return ''
        return msg[:-2]

def raw2int(bytestring):
    return int(raw2hexstring(bytestring), 16)

def parseResponse(msg):
    global mode, control_mode, mv, mi, sv, si, mv_limit, mi_limit, sv_limit, si_limit, temp_endstufe, temp_trafo, master_version, slave_version

    if DEBUG:
        print('RX: ', raw2hexstring(msg))
                
    msg_type = msg[0]
    if msg_type == 'x': # Init
        pass
    elif msg_type == ACK:
        if DEBUG:
            print('(ACK)', end='')
    elif msg_type == 'c': # control / limit values
        mode = raw2int(msg[1])
        mv_limit = raw2int(msg[2:4])
        mi_limit = raw2int(msg[4:6])
        sv_limit = raw2int(msg[6:8])
        si_limit = raw2int(msg[8:10])
    elif msg_type == 'i': # status data
        mode = raw2int(msg[1])
        control_mode = raw2int(msg[2])
        mv = raw2int(msg[3:5])*0.01
        mi = raw2int(msg[5:7])*0.001
        sv = raw2int(msg[7:9])*0.01
        si = raw2int(msg[9:11])*0.001
        temp_endstufe = raw2int(msg[11])
        temp_trafo = raw2int(msg[12])
    elif msg_type == 'v': # version
        master_version = msg[1]
        slave_version = msg[2]
    elif msg_type == 'm': # mode
        mode = msg[1]
    else: 
        print('unknown message: ', raw2hexstring(msg))

def setMode(m):
    sendInstructionAndReceiveResponse('N' + pack('b', m)) # set mode

def initRemote():
    sendInstructionAndReceiveResponse('X')

def getControlValues():
    sendInstructionAndReceiveResponse('C')

def setControlValues(mv_lim=mv_limit, mi_lim=mi_limit, sv_lim=sv_limit, si_lim=si_limit):
    mv_lim = int(mv_lim*100)
    mi_lim = int(mi_lim*1000)
    sv_lim = int(sv_lim*100)
    si_lim = int(si_lim*1000)
    sendInstructionAndReceiveResponse('T' + pack('!HHHH', mv_lim, mi_lim, sv_lim, si_lim))

def getVersion():
    sendInstructionAndReceiveResponse('V')
    return master_version, slave_version

def getData():
    sendInstructionAndReceiveResponse('I')
    return (mode,control_mode, mv, mi, sv, si, temp_endstufe, temp_trafo)

def getMode():
    sendInstructionAndReceiveResponse('M')
    return mode

def setMasterSlaveMode():
    if not (mode & MODE_MASTER_SLAVE):
        setMode(MODE_REMOTE | MODE_MASTER_SLAVE | MODE_MASTER_STANBY_ON | MODE_SLAVE_STANBY_ON)

def setDualMode():
    if not (mode & MODE_DUAL):
        setMode(MODE_REMOTE | MODE_DUAL | MODE_MASTER_STANBY_ON | MODE_SLAVE_STANBY_ON)

def setSeriesMode():
    if not (mode & MODE_SERIES):
        setMode(MODE_REMOTE | MODE_SERIES | MODE_MASTER_STANBY_ON | MODE_SLAVE_STANBY_ON)

def enableMaster():
    setMode(mode & ~MODE_MASTER_STANBY_ON)

def disableMaster():
    setMode(mode | MODE_MASTER_STANBY_ON)

def enableSlave():
    setMode(mode & ~MODE_SLAVE_STANBY_ON)

def disableSlave():
    setMode(mode | MODE_SLAVE_STANBY_ON)

def sendInstructionAndReceiveResponse(instruction):
    sendInstruction(instruction)
    msg = receiveResponse()
    parseResponse(msg)
    return msg

def init():
    initRemote()
    getControlValues()
    getVersion()
    setMode( MODE_REMOTE | MODE_MASTER_SLAVE | MODE_MASTER_STANBY_ON | MODE_SLAVE_STANBY_ON ) # set mode

def connect(port='/dev/ttyUSB0'):
    global ser, thread
    # connect and disconnect (workaround for ch340 chip bug under linux)
    ser = serial.Serial(port, baudrate=9600)
    ser.close()
    ser = serial.Serial(port, baudrate=115200, timeout=1)
    init()
    thread = SerialReader()
    thread.start()

def disconnect():
    thread.exit()
    sleep(0.1) # would be nicer to check if thread has finished
    ser.close()

def printData():
    print('mode: ', mode, 'control_mode: ', control_mode,
          'mv: ',mv, 'mi: ', mi , 'sv: ', sv, 'si: ', si ,
          'mv_limit: ', mv_limit, 'mi_limit: ', mi_limit , 'sv_limit: ', sv_limit, 'si_limit: ', si_limit,
          'temp_endstufe: ', temp_endstufe , 'temp_trafo: ', temp_trafo)

DEBUG = True
DEBUG = False

# setControlValues(mv_lim=0.1, mi_lim=0.02, sv_lim=0.3, si_lim=0.04)

if __name__ == '__main__':
    connect()  # adjust here if you use a none default port
    try:
        while True:
            printData()
            sleep(0.2)
    except KeyboardInterrupt:
        disconnect()
