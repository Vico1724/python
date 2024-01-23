#!/usr/bin/env python
# -*- coding: utf-8 -*-

notes = [12, 4, 14, 11, 18, 13, 7, 10, 5, 9, 15, 8, 14, 16]
notes_sup_moyenne = []

# Calculer la moyenne des notes
moyenne = sum(notes) / len(notes)

# Ajouter les notes au-dessus de la moyenne à la nouvelle liste
for note in notes:
    if note >= 10:
        notes_sup_moyenne.append(note)

print(notes_sup_moyenne)
