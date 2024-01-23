#!/usr/bin/env python
# -*- coding: utf-8 -*-

x = input("Saisir un entier : ")
m = int(input("Saisir le multiplicateur : "))

for i in range(1, m+1):
    result = int(x) * i
    print("{0} x {1:02d} = {2:03d}".format(x, i, result))
