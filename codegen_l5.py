#!/usr/bin/python3

import numpy as np
import matplotlib.pyplot as plt

np.set_printoptions(edgeitems=10)

# See IS-GPS-705E, Table 3-Ia.
CODE_ADVANCE_XBI = [
    None,   # PRN 0
    266,    # PRN 1
    365,
    804,
    1138,
    1509,
    1559,
    1756,
    2084,
    2170,
    2303,
    2527,
    2687,
    2930,
    3471,
    3940,
    4132,
    4332,
    4924,
    5343,
    5443,
    5641,
    5816,
    5898,
    5918,
    5955,
    6243,
    6345,
    6477,
    6518,
    6875,
    7168,
    7187,
    7329,
    7577,
    7720,
    7777,
    8057,   # PRN 37
    5358,
    3550,
    3412,
    819,
    4608,
    3698,
    962,
    3001,
    4441,
    4937,
    3717,
    4730,
    7291,
    2279,
    7613,
    5723,
    7030,
    1475,
    2593,
    2904,
    2056,
    2757,
    3756,
    6205,
    5053,
    6437    # PRN 63
]

CODE_ADVANCE_XBQ = [
    None,   # PRN 0
    1701,
    323,
    5292,
    2020,
    5429,
    7136,
    1041,
    5947,
    4315,
    148,
    535,
    1939,
    5206,
    5910,
    3595,
    5135,
    6082,
    6990,
    3546,
    1523,
    4548,
    4484,
    1893,
    3961,
    7106,
    5299,
    4660,
    276,
    4389,
    3783,
    1591,
    1601,
    749,
    1387,
    1661,
    3210,
    708, # PRN 37
    4226,
    5604,
    6375,
    3056,
    1772,
    3662,
    4401,
    5218,
    2838,
    6913,
    1685,
    1194,
    6963,
    5001,
    6694,
    991,
    7489,
    2441,
    639,
    2097,
    2498,
    6470,
    2399,
    242,
    3768,
    1186 # PRN 63
]

# Calculate num_bits of a n-bit LFSR with given taps & initial value
# Tap order mimics IS-GPS presentation (bit 1 is on the left, 13 on the right)
def gen_lfsr_code(n, taps, output_tap = 13, initial = 1, num_bits = 1):

    # Truncate register to n bits
    reg = initial & (2**n-1)

    # Output - array of 1, 0
    out = []

    for i in range(num_bits):
        out.append((reg >> (n - output_tap)) & 1)
        feedback = 0

        # Apply taps
        for tap in taps:
            feedback ^= (reg >> (n - tap)) & 1 

        reg = (reg >> 1) | (feedback << (n-1))

    return(np.array(out))

def gen_xa_code():

    TAPS = [9, 10, 12, 13]

    # XA code is shortened by one
    sub_code = gen_lfsr_code(13, TAPS, 13, (2**13)-1, 8190)

    # stick two codes together and cutoff at 10230 chips
    return np.append(sub_code, sub_code)[:10230]

def gen_xbi_code(prn):

    TAPS = [1, 3, 4, 6, 7, 8, 12, 13]

    initial_state = 2**13-1
    sub_code = np.roll(gen_lfsr_code(13, TAPS, 13, initial_state, 10230), -CODE_ADVANCE_XBI[prn]) 
    return np.append(sub_code, sub_code)[:10230]

def gen_xbq_code(prn):

    TAPS = [1, 3, 4, 6, 7, 8, 12, 13]

    initial_state = 2**13-1
    sub_code = np.roll(gen_lfsr_code(13, TAPS, 13, initial_state, 10230), -CODE_ADVANCE_XBQ[prn]) 
    return np.append(sub_code, sub_code)[:10230]

def gen_q5_code(prn):
    xa = gen_xa_code()
    xbq = gen_xbq_code(prn)

    return (xa ^ xbq) * 2 - 1

def gen_i5_code(prn):
    xa = gen_xa_code()
    xbi = gen_xbi_code(prn)

    return (xa ^ xbi) * 2 - 1


print(gen_q5_code(1))
