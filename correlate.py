import numpy as np


# sig_i: I samples, already mixed with carrier
# sig_q: Q samples, already mixed with carrier
# code:  Oversampled code, just one code repetition, as +- 1 (NOT 0, 1)
# chip_rate: chip rate, chips/sec
# f_samp: sample rate, samples/sec
# num_coherent: How many code multiples to perform a coherent correlation with
# num_noncoherent: How many coherent correlations to sum together into a noncoherent correlation
# chip_spacing: How narrow code chip bins to search

# note: len(sig_i) and len(sig_q) must be equal to (len(code) * num_coherent * num_noncoherent)
def brute_force_correlate(sig_i, sig_q, code, chip_rate, f_samp, num_coherent=1, num_noncoherent=1, chip_spacing=0.5): 


    samples_per_chip = f_samp / chip_rate
    code_length = int(len(code) / samples_per_chip) # Figure out the code length in chips

    coherent_chunk_size = int(samples_per_chip*code_length*num_coherent) 

    corr_delays = np.arange(0, code_length, chip_spacing)
    corr_result = np.zeros_like(corr_delays, dtype='complex_')

    print('Code Length: {}'.format(code_length))
    print('Samples per Chip: {}'.format(f_samp / chip_rate))
    print('Coherent Chunk size: {} round to {}'.format(samples_per_chip*code_length*num_coherent, coherent_chunk_size))

    for idx, chip_delay in enumerate(corr_delays):

        # Circular shift our local code copy by chip_delay chips
        sample_delay = int(round(chip_delay * samples_per_chip))
        delayed_code = np.roll(code, sample_delay) #NOTE: assumes the coherent accumulation size is a multiple of the code length

        peak = 0

        # Perform coherent sub-correlations 
        for i in range(num_noncoherent):

            chunk_idx_min = i*coherent_chunk_size
            chunk_idx_max = (i+1)*coherent_chunk_size

            if chip_delay == 0:
                print('Noncoh {}'.format(i))
                print('\tmin {} max {}'.format(chunk_idx_min, chunk_idx_max))
            
            chunk_i = sig_i[chunk_idx_min:chunk_idx_max]
            chunk_q = sig_q[chunk_idx_min:chunk_idx_max]
            chunk_code = delayed_code

            # Correlate (I&Q)
            sum_i = np.dot(chunk_i, chunk_code)
            sum_q = np.dot(chunk_q, chunk_code)

            # Normalize sums... divide by the number of samples in the chunk
            sum_i /= (chunk_code.shape[0] * num_noncoherent)
            sum_q /= (chunk_code.shape[0] * num_noncoherent)

            coh_result = complex(sum_i, sum_q)
            
            peak += abs(coh_result)

        corr_result[idx] = peak

    return (corr_result, corr_delays)

def fft_correlate(sig_i, sig_q, code, chip_rate, f_samp, num_coherent=1, num_noncoherent=1, chip_spacing=0.5): 


    samples_per_chip = f_samp / chip_rate
    code_length = int(len(code) / samples_per_chip) # Figure out the code length in chips

    coherent_chunk_size = int(samples_per_chip*code_length*num_coherent) 

    corr_delays = code_length - np.arange(0, code_length, 1/samples_per_chip)

#    print('Code Length: {}'.format(code_length))
#    print('Samples per Chip: {}'.format(f_samp / chip_rate))
#    print('Coherent Chunk size: {} round to {}'.format(samples_per_chip*code_length*num_coherent, coherent_chunk_size))

    ncoh_result = np.zeros_like(code, dtype='float')

    for i in range(num_noncoherent):
        chunk_idx_min = i*coherent_chunk_size
        chunk_idx_max = (i+1)*coherent_chunk_size

#        print('Noncoh {}'.format(i))
#        print('\tmin {} max {}'.format(chunk_idx_min, chunk_idx_max))
        
        chunk_i = sig_i[chunk_idx_min:chunk_idx_max]
        chunk_q = sig_q[chunk_idx_min:chunk_idx_max]
        chunk_sig = chunk_i + (1j * chunk_q)

        # Multiplication in frequency domain -> convolution in time domain
        # Reverse sig so it's xcorr not convolution
        # We also get circular convolution effects for free
        chunk_f = np.fft.fft(np.flip(chunk_sig))
        code_f = np.fft.fft(code)

        coh_result = np.fft.ifft(np.multiply(chunk_f, code_f))
        ncoh_result += np.abs(coh_result)

    return (ncoh_result, corr_delays)
