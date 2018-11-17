#!/usr/bin/python3
import math
import numpy
import scipy

import matplotlib.pyplot as plt

import codegen_gpsl1ca
import frontend

numpy.set_printoptions(edgeitems=5000)

CHIP_RATE = 1023000 # Chips/s
CODE_LENGTH = 1023
CODE_CHIP_BIN = 0.5

DOPP_MIN = -5000
DOPP_MAX =  5000
DOPP_BIN_WIDTH = 500

NUM_NONCOHERENT_CHUNKS = 1 

#TODO: mathematical basis for this
# Also this seems to be dependent on noncoherent chunk count...
# and it shouldnt be (??)
ACQUISITION_MIN_RATIO = 4


def acquire(prn, front):

    front.SAMPLES_PER_SUPERCHUNK = NUM_NONCOHERENT_CHUNKS * front.SAMPLES_PER_CHUNK

    print ('\nAttempting blind, offline acquisition of PRN {}'.format(prn))
    
    buff = front.get_chunk(front.SAMPLES_PER_SUPERCHUNK)

    t = numpy.zeros(front.SAMPLES_PER_SUPERCHUNK)
    for i in range(front.SAMPLES_PER_SUPERCHUNK):
        t[i] = i / front.F_SAMP

    # "upsample" the code bits to a buffer the same length as the sample buffer
    code_bits = codegen_gpsl1ca.CODE[prn] # need to upsample

    delayed_codes = []

    i = numpy.arange(front.SAMPLES_PER_SUPERCHUNK)
    chip_num = (i * CHIP_RATE / front.F_SAMP).astype(numpy.uint32) % CODE_LENGTH # floor, not round, to simulate "rect FIR filter"??
    code = code_bits[chip_num] * 2 - 2

    # NONCOHERENT ACQUISITION... 1ms chunks
    highscore = 0
    highscore_delay = None
    highscore_doppler = None
    noise_avg = 0


    for doppler in numpy.arange(DOPP_MIN, DOPP_MAX, DOPP_BIN_WIDTH):
        
        print ('\tDoppler: {} Hz'.format(doppler))
        
        # Genrate carrier 
        f_carrier = front.F_L1_IF + doppler
        carrier_i = numpy.cos(2 * math.pi * f_carrier * t)
        carrier_q = numpy.sin(2 * math.pi * f_carrier * t)

        # Mix with carrier
        carrier_mixed_i = carrier_i * buff
        carrier_mixed_q = carrier_q * buff

        for chip_delay in numpy.arange(0, 1023, 0.5):

            # Circular shift our local code copy by chip_delay chips
            sample_delay = int(round(chip_delay * (front.F_SAMP / CHIP_RATE)))
            delayed_code = numpy.roll(code, sample_delay) #NOTE: assumes the chunk length is a multiple of the code length, otherwise we can't just circularly roll a superchunk

            peak = 0

            # Perform coherent subaccumulations 
            for i in range(NUM_NONCOHERENT_CHUNKS):

                chunk_idx_min = i*front.SAMPLES_PER_CHUNK
                chunk_idx_max = (i+1)*front.SAMPLES_PER_CHUNK
                
                chunk_carrier_mixed_i = carrier_mixed_i[chunk_idx_min:chunk_idx_max]
                chunk_carrier_mixed_q = carrier_mixed_i[chunk_idx_min:chunk_idx_max]
                chunk_code = delayed_code[chunk_idx_min:chunk_idx_max]

                # Convolutinate (I&Q)
                sum_i = numpy.dot(chunk_carrier_mixed_i, chunk_code)
                sum_q = numpy.dot(chunk_carrier_mixed_q, chunk_code)

                # Normalize sums... divide by the number of samples in the chunk
                sum_i /= chunk_code.shape[0] 
                sum_q /= chunk_code.shape[0] 

                subpeak = math.sqrt(sum_i*sum_i + sum_q*sum_q) / NUM_NONCOHERENT_CHUNKS
                peak += subpeak
            
            # look at result of subaccums
            if peak > highscore:
                print('\t\tNew highscore: {} Delay: {}'.format(peak, chip_delay))
                highscore = peak
                highscore_delay = chip_delay
                highscore_doppler = doppler
            
            noise_avg += (peak / (1023*2 * (DOPP_MAX-DOPP_MIN)/DOPP_BIN_WIDTH))

   # print ('avg sig power: {}'.format(noise_avg))

    print('\n\tBest peak (ratio: {:0.3f}) -> Delay: {} chips, Doppler {} Hz'.format(highscore / noise_avg, highscore_delay, highscore_doppler))

    return {
        'success': (highscore/noise_avg) > ACQUISITION_MIN_RATIO,
        'prn': prn,
        'delay' : highscore_delay,
        'doppler' : highscore_doppler
    }

if __name__ == '__main__':
    stream = 1 #L1_PRI
    front = frontend.NTLABSamples('rawintegersamples.bin', stream)
    results = []

    prn_to_try = range(1,37)

    for prn in prn_to_try:
        results.append(acquire(prn, front))

    for result in results:
        if result['success']:
            print('Acquired PRN{:2d}: Delay: \t{} chips, Doppler \t{} Hz'.format(result['prn'], result['delay'], result['doppler']))

