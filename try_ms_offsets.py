#!/usr/bin/python3

import acquire
import frontend
import matplotlib.pyplot as plt
import numpy as np

PRN = 10
ratios = []

for ms_offset in np.arange(0, 1000, 20):

    print(ms_offset)
   
    # stream 3: L5 pri
    front = frontend.NTLABSamples('rawintegersamples.bin', 3)

    # discard ms_offset ms of data to synchronize with NH code edges
    front.get_chunk(int(ms_offset * front.SAMPLES_PER_CHUNK / 1000))

    result = acquire.acquire(PRN, front, dopp_min=0, dopp_max=1500)
    ratios.append(result['ratio'])

plt.figure()
plt.plot(ratios)
plt.title('corr result for frame offsets:')
plt.show()
