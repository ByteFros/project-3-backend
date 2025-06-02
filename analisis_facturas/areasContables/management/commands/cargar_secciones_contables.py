from django.core.management.base import BaseCommand
from areasContables.models import SeccionContable

class Command(BaseCommand):
    help = 'Crea las secciones contables según el BOE (A a G)'

    SECCIONES = [
        ("A", "Activo no corriente"),
        ("B", "Activo corriente"),
        ("C", "Patrimonio neto"),
        ("D", "Pasivo no corriente"),
        ("E", "Pasivo corriente"),
        ("F", "Cuenta de Pérdidas y Ganancias"),
        ("G", "Ingresos y Gastos Reconocidos"),
    ]

    def handle(self, *args, **options):
        total_creadas = 0

        for letra, nombre in self.SECCIONES:
            seccion, creada = SeccionContable.objects.get_or_create(
                letra=letra,
                defaults={"nombre": nombre}
            )
            if creada:
                self.stdout.write(f"Sección creada: {letra} - {nombre}")
                total_creadas += 1
            else:
                self.stdout.write(f"Sección ya existente: {letra} - {nombre}")

        self.stdout.write(self.style.SUCCESS(f"✔ Total de secciones nuevas: {total_creadas}"))
