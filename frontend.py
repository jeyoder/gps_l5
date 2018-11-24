import numpy
import math

class FrontEnd():
    def __init__(self, filename):
        print('Default Frontend __init__')

    def skip(self, time_ms):
        print('Default Frontend skip()')

    def get_chunk(self, length):
        print('Default Frontend load()')

    def get_chunks(self, num):
        data = self.get_chunk(-1)
        for i in range(num-1):
            new_chunk = self.get_chunk(-1)
            data = numpy.concatenate((data, new_chunk))

        return data

    def get_if(self):
        return 0

class LynxSB(FrontEnd):

    F_SAMP = 19199984          # ~19.2 MHz 
    F_L1_IF = 2.392739428572e6 # ~2.393 MHz

    F_L1_IF_Rad = 2 * math.pi * F_L1_IF / F_SAMP

    SAMPLES_PER_CHUNK = int(F_SAMP / 1000)

    def __init__(self, filename):
    
        self.file = open(filename, 'rb')

    def skip(self, time_ms):

        words_to_skip = (self.F_SAMP / 1000 / 8)

        for i in range(int(words_to_skip)):
            self.file.read(4)

    def get_chunk(self, length): #TODO: use length

        # So we want 1ms of data. i.e. we want (F_SAMP / 1000) samples
        # LYNX_SB bitpacking format: [A1 B1 A2 B2]. Therefore, 16 samples per 32-bit
        # word. Then *4 to turn words -> bytes. 
        self.SAMPLES_PER_CHUNK = int(self.F_SAMP / 1000)

        # Skip a bunch of words

        # READ & UNPACK LYNX SAMPLES
        print('Reading {} samples'.format(self.SAMPLES_PER_CHUNK))

        buff = numpy.zeros(self.SAMPLES_PER_CHUNK, dtype=numpy.int8)
        samples_read = 0
        while samples_read < self.SAMPLES_PER_CHUNK:
            # Read a 32-bit word...
            word = self.file.read(4)
            byte = word[0] # Byte 0 of each word is Primary L1
            bits = [(byte>>0)&1,(byte>>1)&1,(byte>>2)&1,(byte>>3)&1,(byte>>4)&1,(byte>>5)&1,(byte>>6)&1,(byte>>7)&1]
            for i in range(8):
                if(i + samples_read < self.SAMPLES_PER_CHUNK):
                    buff[i + samples_read] = bits[i] * 2 - 1
            samples_read += 8
    
        return buff
    
class Bavaro(FrontEnd):

    F_SAMP = 5456000          
    F_L1_IF = 4092000 

    F_L1_IF_Rad = 2 * math.pi * F_L1_IF / F_SAMP

    SAMPLES_PER_CHUNK = 1*int(F_SAMP / 1000)

    leftover_bits = []

    def __init__(self, filename):
    
        self.file = open(filename, 'rb')

    def skip(self, time_ms):
        print('[frontend]: skipping {} ms'.format(time_ms))

        bytes_to_skip = (self.F_SAMP / 1000 / 8)

        for i in range(int(bytes_to_skip)):
            self.file.read(1)

    def get_chunk(self, length):
#        print('[frontend]: reading ~{} ms'.format(length*1000 / self.F_SAMP))

        # So we want 1ms of data. i.e. we want (F_SAMP / 1000) samples

        # READ & UNPACK 

        buff = numpy.zeros(length, dtype=numpy.int8)
        samples_read = 0

        while(len(self.leftover_bits) > 0 and samples_read < length):
            buff[i + samples_read] = self.leftover_bits.pop(0)
            samples_read += 1

        while samples_read < length:
            # Read a packed byte...
            byte = self.file.read(1)[0]
            bits = [(byte>>0)&1,(byte>>1)&1,(byte>>2)&1,(byte>>3)&1,(byte>>4)&1,(byte>>5)&1,(byte>>6)&1,(byte>>7)&1]
            for i in range(8):
                if(i + samples_read < length):
                    buff[i + samples_read] = bits[i] * 2 - 1
                else:
                    # we have some bits we need to deal with... store them in the bit stash
                    self.leftover_bits.append(bits[i])
            samples_read += 8
    
        return buff

class NTLABSamples(FrontEnd):

    F_SAMP = 53e6
    F_L5_IF = 13.55e6
    F_L1_IF = 14.58e6
    NUM_STREAMS = 4

    SAMPLES_PER_CHUNK = 1*int(F_SAMP / 1000)

    def __init__(self, filename, stream):
    
        self.file = open(filename, 'rb')
        self.stream = stream

    def skip(self, time_ms):
        print('[frontend]: skipping {} ms'.format(time_ms))

        bytes_to_skip = (self.F_SAMP / 1000 / 8)

        for i in range(int(bytes_to_skip)):
            self.file.read(1)

    def get_chunk(self, length):
#        print('[frontend]: reading ~{} ms'.format(length*1000 / self.F_SAMP))

        samples_read = 0

        # Slurp up all the data in the next chunk
        raw_buf = numpy.frombuffer(self.file.read(self.NUM_STREAMS * length), dtype='int8')
        
        # Decimate to extract only the stream we're interested in
        buf = raw_buf[self.stream-1::self.NUM_STREAMS]         

        return buf
