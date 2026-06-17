import os
import json
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

class SecureECDH:
    def __init__(self):
        self.p = 2**255 - 19
        self.A = 486662
        self.secret_scalar = int.from_bytes(os.urandom(32), 'big') % self.p

    def _is_on_curve(self, x, y):
        a = 1
        d = (self.A + 2) * pow(self.A - 2, -1, self.p) % self.p
        
        lhs = (a * (x**2) + y**2) % self.p
        rhs = (1 + d * (x**2) * (y**2)) % self.p
        return lhs == rhs

    def _edwards_to_weierstrass(self, x, y):
        if not self._is_on_curve(x, y):
            raise ValueError("Invalid Point: Point does not exist on the curve.")

        inv_1_minus_y = pow((1 - y) % self.p, -1, self.p)
        u = ((1 + y) * inv_1_minus_y) % self.p
        v = ((1 + y) * pow((x * (1 - y)) % self.p, -1, self.p)) % self.p

        X = (u - self.A * pow(3, -1, self.p)) % self.p 
        Y = v % self.p

        return X, Y

    def _weierstrass_add(self, P, Q, a_w):
        if P == (None, None): return Q
        if Q == (None, None): return P
        
        x1, y1 = P
        x2, y2 = Q
        
        if x1 == x2 and y1 != y2:
            return (None, None)
            
        if x1 == x2:
            if y1 == 0:
                return (None, None)
            lam = ((3 * x1**2 + a_w) * pow(2 * y1, -1, self.p)) % self.p
        else:
            lam = ((y2 - y1) * pow(x2 - x1, -1, self.p)) % self.p
            
        x3 = (lam**2 - x1 - x2) % self.p
        y3 = (lam * (x1 - x3) - y1) % self.p
        
        return x3, y3

    def _weierstrass_scalar_mult(self, X, Y, scalar):
        a_w = (1 - pow(self.A, 2, self.p) * pow(3, -1, self.p)) % self.p
        
        R = (None, None)
        P = (X, Y)
        
        for bit in bin(scalar)[2:]:
            R = self._weierstrass_add(R, R, a_w)
            if bit == '1':
                R = self._weierstrass_add(R, P, a_w)
                
        return R

    def process_key_exchange(self, x_in, y_in):
        try:
            w_x, w_y = self._edwards_to_weierstrass(x_in, y_in)
            
            shared_X, shared_Y = self._weierstrass_scalar_mult(w_x, w_y, self.secret_scalar)
            
            return shared_X, shared_Y
        except Exception as e:
            return None, str(e)

    def get_encrypted_flag(self):
        key = hashlib.sha256(self.secret_scalar.to_bytes(32, 'big')).digest()
        cipher = AES.new(key, AES.MODE_CBC)
        with open("flag.txt", "rb") as f:
            flag = f.read()
        ciphertext = cipher.encrypt(pad(flag, 16))
        return cipher.iv.hex(), ciphertext.hex()

if __name__ == "__main__":
    server = SecureECDH()
    
    print("==================================================")
    print(" Secure ECDH Key Exchange Portal ")
    print("==================================================")
    
    iv, ciphertext = server.get_encrypted_flag()
    print(f"[*] Encrypted Flag IV: {iv}")
    print(f"[*] Encrypted Flag CT: {ciphertext}")
    print("--------------------------------------------------")

    while True:
        try:
            print("\nEnter your public point (Edwards coordinates):")
            user_x = input("x (hex or int): ").strip()
            user_y = input("y (hex or int): ").strip()
            
            if not user_x or not user_y:
                break
                
            x_int = int(user_x, 16) if user_x.startswith("0x") else int(user_x)
            y_int = int(user_y, 16) if user_y.startswith("0x") else int(user_y)
            
            res_x, res_y = server.process_key_exchange(x_int, y_int)
            
            if res_x is None:
                print(f"[!] Error: {res_y}")
            else:
                print("[+] Key exchange successful!")
                print(f"Shared X: {hex(res_x)}")
                print(f"Shared Y: {hex(res_y)}")
                
        except ValueError:
            print("[!] Invalid input format. Please enter integers.")
        except KeyboardInterrupt:
            print("\nExiting...")
            break
