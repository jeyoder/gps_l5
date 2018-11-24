#!/usr/bin/python3
import math
import numpy
import scipy
import scipy.fftpack
import scipy.signal

import matplotlib.pyplot as plt
import matplotlib

import codegen_gpsl1ca
import codegen_l5
import frontend
import correlate

numpy.set_printoptions(edgeitems=10)
matplotlib.style.use('classic')

L5_MODE = True
I5_CODE = False
PLOT = True

if  L5_MODE:
    CHIP_RATE = 10230000 # 10.23 MC/s
    CODE_LENGTH = 10230
else:
    CHIP_RATE = 1023000 # Chips/s
    CODE_LENGTH = 1023

DOPP_MIN = -5000
DOPP_MAX = 5000
DOPP_BIN_WIDTH = 500

NUM_NONCOHERENT_CHUNKS = 100 


#TODO: mathematical basis for this
# Also this seems to be dependent on noncoherent chunk count...
# and it shouldnt be (??)
ACQUISITION_MIN_RATIO = 7


def acquire(prn, front, dopp_min=DOPP_MIN, dopp_max=DOPP_MAX):

    front.SAMPLES_PER_SUPERCHUNK = NUM_NONCOHERENT_CHUNKS * front.SAMPLES_PER_CHUNK

    print ('\nAttempting blind, offline acquisition of PRN {}'.format(prn))
    
    buff = front.get_chunk(front.SAMPLES_PER_SUPERCHUNK)

    t = numpy.zeros(front.SAMPLES_PER_SUPERCHUNK)
    for i in range(front.SAMPLES_PER_SUPERCHUNK):
        t[i] = i / front.F_SAMP

    # "upsample" the code bits to a buffer the same length as the sample buffer
    if L5_MODE:
        if I5_CODE:
            code_bits = codegen_l5.gen_i5_code(prn)
        else:
            code_bits = codegen_l5.gen_q5_code(prn)
    else:
        code_bits = codegen_gpsl1ca.CODE[prn] # need to upsample

    delayed_codes = []

    i = numpy.arange(front.SAMPLES_PER_CHUNK)
    chip_num = (i * CHIP_RATE / front.F_SAMP).astype(numpy.uint32) % CODE_LENGTH # floor, not round, to simulate "rect FIR filter"??
    code = code_bits[chip_num] * 2 - 2

    best_ratio = 0
    best_doppler = 0
    success = False

    for doppler in numpy.arange(dopp_min, dopp_max, DOPP_BIN_WIDTH):
        
        print ('\tDoppler: {} Hz'.format(doppler))
        
        # Genrate carrier 
        if L5_MODE:
            f_carrier = front.F_L5_IF + doppler
        else:
            f_carrier = front.F_L1_IF + doppler
        carrier_i = numpy.cos(2 * math.pi * f_carrier * t)
        carrier_q = numpy.sin(2 * math.pi * f_carrier * t)

        # Mix with carrier
        carrier_mixed_i = carrier_i * buff
        carrier_mixed_q = carrier_q * buff

        (corr_result, corr_delays) = correlate.fft_correlate(carrier_mixed_i, carrier_mixed_q, code,
                chip_rate=CHIP_RATE, f_samp=front.F_SAMP, 
                num_coherent=1,
                num_noncoherent=NUM_NONCOHERENT_CHUNKS,
                chip_spacing=0.5)

        noise_avg = numpy.average(corr_result)
        noise_sigma = numpy.sqrt(numpy.average(numpy.square(corr_result - noise_avg)))
        peak = numpy.max(corr_result)
        ratio = (peak-noise_avg) / noise_sigma

        if ratio > best_ratio:
            best_ratio = ratio
            best_doppler = doppler

#        print('Noise sigma: {}'.format(noise_sigma))

        if (ratio > ACQUISITION_MIN_RATIO):
            # Acquisition successful!
            success = True
            print('************GOT EM COACH**************')
            print('Peak: {} sigma'.format(ratio))

            if PLOT:
                plt.figure()
                plt.plot(corr_delays, abs(corr_result), 'r-')
                if L5_MODE:
                    if I5_CODE:
                        sig_name = 'L5 I'
                    else:
                        sig_name = 'L5 Q'
                else:
                    sig_name = 'L1 C/A'
                plt.title('PRN {}, {}, f_doppler={}, {}ms accum'.format(prn, sig_name, doppler, NUM_NONCOHERENT_CHUNKS))
                plt.show()


    return {
        'ratio':  best_ratio,
        'doppler': best_doppler,
        'success': success
    }
if __name__ == '__main__':

    # Generate test periodogram for comparison with MATLAB code
    if L5_MODE:
        stream = 3
    else:
        stream = 1 #L1_PRI
#    front = frontend.NTLABSamples('rawintegersamples.bin', stream)
#    nfft = 2**13
#    data = front.get_chunks(500)
#
#    # mimic methods of matlab code
#    print(len(data))
#    [spec_f, spec] = scipy.signal.welch(data, front.F_SAMP, nperseg=nfft)
#
#    plt.figure()
#    plt.plot(spec_f, 10*numpy.log10(numpy.abs(spec)), 'r.')
#    plt.title('Welch PSD estimate, F_L1, stream 1')
#    plt.show()

    front = frontend.NTLABSamples('rawintegersamples.bin', stream)
    front.get_chunk(int(689.6 * front.SAMPLES_PER_CHUNK / 1000))
#    front = frontend.Bavaro('/home/james/rnlab/gnss_work/gnss_receiver/bavaro.bin')
    results = []

#    prn_to_try = range(1,37)
    prn_to_try = [10] #, 32]

    for prn in prn_to_try:
        results.append(acquire(prn, front))

