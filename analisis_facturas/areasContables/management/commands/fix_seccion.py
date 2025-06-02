# management/commands/fix_pg_seccion.py
from django.core.management.base import BaseCommand
from areasContables.models import SeccionContable, AreaContable

class Command(BaseCommand):
    help = 'Corrige las áreas de Pérdidas y Ganancias mal clasificadas en la Sección D y las mueve a la Sección F'

    def handle(self, *args, **options):
        # Crear sección F si no existe
        seccion_f, creado = SeccionContable.objects.get_or_create(
            letra="F",
            defaults={"nombre": "F) CUENTA DE PÉRDIDAS Y GANANCIAS"}
        )

        if creado:
            self.stdout.write(self.style.SUCCESS("✅ Sección F creada correctamente."))
        else:
            self.stdout.write("ℹ️ Sección F ya existía.")

        # Áreas mal clasificadas que deben eliminarse de la sección D
        nombres_pg = [
            "1. Importe neto de la cifra de negocios",
            "2. Variación de existencias de productos terminados y en curso de fabricación",
            "3. Trabajos realizados por la empresa para su activo",
            "4. Aprovisionamientos",
            "5. Otros ingresos de explotación",
            "6. Gastos de personal",
            "7. Otros gastos de explotación",
            "8. Amortización del inmovilizado",
            "9. Imputación de subvenciones de inmovilizado no financiero y otras",
            "10. Excesos de provisiones",
            "11. Deterioro y resultado por enajenaciones del inmovilizado",
            "12. Ingresos financieros",
            "13. Gastos financieros",
            "14. Variación de valor razonable en instrumentos financieros",
            "15. Diferencias de cambio",
            "16. Deterioro y resultado por enajenaciones de instrumentos financieros",
            "17. Impuestos sobre beneficios"
        ]

        # Eliminar las áreas mal clasificadas (y sus subáreas por cascada)
        eliminadas = AreaContable.objects.filter(seccion__letra="D", nombre__in=nombres_pg).delete()

        self.stdout.write(self.style.WARNING(f"⚠️ Se eliminaron {eliminadas[0]} áreas/subáreas de la Sección D."))
        self.stdout.write(self.style.SUCCESS("✅ Limpieza y corrección completada. Puedes volver a cargar las áreas ahora en la Sección F."))