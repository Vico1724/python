# -*- coding: utf-8 -*-
"""
Created on Mon Feb  6 15:43:05 2023

@author: vicoc

"""
n = int(input("nombre de ligne (5 <= n <= 20): "))

print("Figure 1")
if 5 <= n <= 20:
  for i in range(1, n+1):
    print("*" * i)
else:
  print("Invalid input")
  
