#coding=utf-8
import BitVector
import os
import sys

class SimpleHash():

    def __init__(self, cap, seed):
        self.cap = cap
        self.seed = seed
    
    def hash(self, value):
        ret = 0
        for i in range(len(value)):
            ret += self.seed*ret + ord(value[i])
        return (self.cap-1) & ret    

class BloomFilter():
    
    def __init__(self, BIT_SIZE=1<<25):
        self.BIT_SIZE = 1 << 25
        self.seeds = [5, 7, 11, 13, 31, 37, 61]
        self.bitset = BitVector.BitVector(size=self.BIT_SIZE)
        self.hashFunc = []
        
        for i in range(len(self.seeds)):
            self.hashFunc.append(SimpleHash(self.BIT_SIZE, self.seeds[i]))
        
    def insert(self, value):
        for f in self.hashFunc:
            loc = f.hash(value)
            self.bitset[loc] = 1
    def isContain(self, value):
        if value == None:
            return False
        ret = True
        for f in self.hashFunc:
            loc = f.hash(value)
            ret = ret & self.bitset[loc]
        return ret