"""Mide que tan separadas estan las mascotas segun su descriptor.

Sirve para elegir el umbral con datos en vez de a ojo: imprime la similitud
entre el centroide de cada mascota y cada una de sus fotos, y entre mascotas.

    python manage.py similarity
"""
from itertools import combinations

from django.core.management.base import BaseCommand

from pets import embedding
from pets.models import Pet


class Command(BaseCommand):
    help = "Similitud entre mascotas y sus fotos, para calibrar el umbral."

    def handle(self, *args, **options):
        pets = [p for p in Pet.objects.all() if p.centroid]
        if not pets:
            self.stdout.write("No hay mascotas con vector guardado. Sube fotos primero.")
            return

        self.stdout.write("Mascotas con vector: %s\n" % ", ".join(p.name for p in pets))

        for pet in pets:
            fotos = [f for f in pet.photos.all() if f.embedding]
            if not fotos:
                continue
            self.stdout.write("%s (%d fotos)" % (pet.name, len(fotos)))
            for foto in fotos:
                valor = embedding.similarity(foto.embedding, pet.centroid)
                self.stdout.write("   %-8s %.3f" % (foto.pose or "foto", valor))

        if len(pets) < 2:
            self.stdout.write("\nSolo hay una mascota: no se puede medir separacion.")
            return

        self.stdout.write("\nSeparacion entre mascotas (cuanto mas bajo, mejor):")
        minimo = 1.0
        for a, b in combinations(pets, 2):
            valor = embedding.similarity(a.centroid, b.centroid)
            minimo = min(minimo, valor)
            self.stdout.write("   %-10s vs %-10s %.3f" % (a.name, b.name, valor))

        self.stdout.write(
            "\nUmbral sugerido: entre %.2f (la separacion mas baja) y 1.00."
            % minimo
        )
        self.stdout.write(
            "Si la separacion mas baja es mayor que 0.90, las mascotas se parecen "
            "demasiado para este descriptor: usa fotos con mas contraste entre ellas."
        )
