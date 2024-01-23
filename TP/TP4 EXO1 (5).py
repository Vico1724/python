# -*- coding: utf-8 -*-
"""
Created on Wed Feb 22 14:07:47 2023

@author: Victor Orlando"""

def NbCMin(passwd):
    """
    Retourne le nombre de caractères minuscules dans le mot de passe.
    """
    nb_min = 0
    for char in passwd:
        if char.islower():
            nb_min += 1
    return nb_min

def NbCMaj(passwd):
    """
    Retourne le nombre de caractères majuscules dans le mot de passe.
    """
    nb_maj = 0
    for char in passwd:
        if char.isupper():
            nb_maj += 1
    return nb_maj

def NbCAlpha(passwd):
    """
    Retourne le nombre de caractères non alphabétiques dans le mot de passe.
    """
    nb_alpha = 0
    for char in passwd:
        if not char.isalpha():
            nb_alpha += 1
    return nb_alpha

def LongMaj(passwd):
    """
    Retourne la longueur de la plus longue séquence de lettres majuscules dans le mot de passe.
    """
    max_len = 0
    current_len = 0
    for char in passwd:
        if char.isupper():
            current_len += 1
        else:
            max_len = max(max_len, current_len)
            current_len = 0
    return max_len

def LongMin(passwd):
    """
    Retourne la longueur de la plus longue séquence de lettres minuscules dans le mot de passe.
    """
    max_len = 0
    current_len = 0
    for char in passwd:
        if char.islower():
            current_len += 1
        else:
            max_len = max(max_len, current_len)
            current_len = 0
    return max_len

def Score(passwd):
    """
    Calcule et affiche le score d'un mot de passe et sa force.
    """
    total_bonus = len(passwd) * 4 + (len(passwd) - NbCMaj(passwd)) * 2 + (len(passwd) - NbCMin(passwd)) * 3 + NbCAlpha(passwd) * 5
    total_penalty = LongMin(passwd) * 2 + LongMaj(passwd)
    score = total_bonus - total_penalty

    if score < 20:
        force = 'Très faible'
    elif score < 40:
        force = 'Faible'
    elif score < 80:
        force = 'Fort'
    else:
        force = 'Très fort'

    print(f"Score : {score}, force : {force}")

# Exemple d'utilisation
passwd = "P@cSI_promo2017"
Score(passwd)