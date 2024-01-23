# -*- coding: utf-8 -*-

n = int(input("Saisir un entier : "))
print("En binaire :", bin(n))
print("En octal :", oct(n))
print("En hexadécimal :", hex(n))

chaine = str(input("Saisir une chaine de nombres séparés par des * : "))
codes_ascii = [chr(int(nombre)) for nombre in chaine.split('*')]
print(codes_ascii)
