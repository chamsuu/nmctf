import numpy as np
import random
from flag import flag
from Crypto.Cipher import AES

A = np.random.uniform(-50,50,(3,3)) # generate a random 3x3 matrice where each entry is between -50 and 50
seed = round(np.linalg.det(A)) # calculate the det of the matrix

random.seed(seed)

key = random.randbytes(16)
cipher = AES.new(key,AES.MODE_ECB)

ct = cipher.encrypt(flag)



with open('secret.txt','w') as f : 
    f.write(f'seed : {seed}\n')
    f.write(f'A: {A}')


with open('output.txt','w') as f : 
    f.write(f'ct: {ct.hex()}')
