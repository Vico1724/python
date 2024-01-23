
# Exercice 5

# Saisir un entier n strictement positif
n = int(input("Saisir un entier n : "))

# Vérifier s'il est parfait
sum = 0
for i in range(1, n):
    if n % i == 0:
        sum += i
if sum == n:
    print(n, "est un nombre parfait")
else:
    print(n, "n'est pas un nombre parfait")

# Afficher tous les nombres parfaits inférieurs ou égal à n
print("Liste des nombres parfaits inférieurs ou égaux à", n, ":")
for i in range(1, n + 1):
    sum = 0
    for j in range(1, i):
        if i % j == 0:
            sum += j
    if sum == i:
        print(i)