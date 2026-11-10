from django.core.management.base import BaseCommand

from question_bank.models import (
    Area,
    EducationLevel,
    Institution,
)


LEVELS = [
    {
        "code": "BACHILLERATO",
        "name": "Bachillerato",
    },
    {
        "code": "UNIVERSIDAD",
        "name": "Universidad",
    },
]


INSTITUTIONS = [
    {
        "code": "ECOEMS",
        "name": "ECOEMS",
    },
    {
        "code": "CENEVAL_EXANI_I",
        "name": "CENEVAL EXANI I",
    },
    {
        "code": "UACH",
        "name": "UACH",
    },
    {
        "code": "UNAM",
        "name": "UNAM",
    },
    {
        "code": "IPN",
        "name": "IPN",
    },
    {
        "code": "UAM",
        "name": "UAM",
    },
    {
        "code": "EXANI_II",
        "name": "EXANI II",
    },
]


AREAS = [
    # =========================================================
    # UNAM
    # =========================================================
    {
        "level": "UNIVERSIDAD",
        "institution": "UNAM",
        "code": "AREA1",
        "name": (
            "Área 1 - Ciencias Físico-Matemáticas "
            "y de las Ingenierías"
        ),
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "UNAM",
        "code": "AREA2",
        "name": (
            "Área 2 - Ciencias Biológicas, "
            "Químicas y de la Salud"
        ),
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "UNAM",
        "code": "AREA3",
        "name": "Área 3 - Ciencias Sociales",
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "UNAM",
        "code": "AREA4",
        "name": "Área 4 - Humanidades y Artes",
    },

    # =========================================================
    # IPN
    # =========================================================
    {
        "level": "UNIVERSIDAD",
        "institution": "IPN",
        "code": "IYCFM",
        "name": (
            "Ingeniería y Ciencias "
            "Físico-Matemáticas"
        ),
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "IPN",
        "code": "CMB",
        "name": "Ciencias Médico-Biológicas",
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "IPN",
        "code": "CSA",
        "name": (
            "Ciencias Sociales "
            "y Administrativas"
        ),
    },

    # =========================================================
    # UAM
    # =========================================================
    {
        "level": "UNIVERSIDAD",
        "institution": "UAM",
        "code": "CBI",
        "name": "Ciencias Básicas e Ingeniería",
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "UAM",
        "code": "CBS",
        "name": (
            "Ciencias Biológicas "
            "y de la Salud"
        ),
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "UAM",
        "code": "CSH",
        "name": (
            "Ciencias Sociales "
            "y Humanidades"
        ),
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "UAM",
        "code": "CAD",
        "name": (
            "Ciencias y Artes "
            "para el Diseño"
        ),
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "UAM",
        "code": "CNI",
        "name": (
            "Ciencias Naturales e Ingeniería "
            "- Unidad Cuajimalpa"
        ),
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "UAM",
        "code": "CCD",
        "name": (
            "Ciencias de la Comunicación y Diseño "
            "- Unidad Cuajimalpa"
        ),
    },

    # =========================================================
    # EXANI II
    # =========================================================
    {
        "level": "UNIVERSIDAD",
        "institution": "EXANI_II",
        "code": "PREMEDICINA",
        "name": "Premedicina",
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "EXANI_II",
        "code": "CIENCIAS_SALUD",
        "name": "Ciencias de la Salud",
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "EXANI_II",
        "code": "CALCULO",
        "name": (
            "Cálculo diferencial "
            "e integral"
        ),
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "EXANI_II",
        "code": "FISICA",
        "name": "Física",
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "EXANI_II",
        "code": "QUIMICA",
        "name": "Química",
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "EXANI_II",
        "code": "BIOLOGIA",
        "name": "Biología",
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "EXANI_II",
        "code": "ADMINISTRACION",
        "name": "Administración",
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "EXANI_II",
        "code": "ECONOMIA",
        "name": "Economía",
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "EXANI_II",
        "code": "DERECHO",
        "name": "Derecho",
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "EXANI_II",
        "code": "CIENCIAS_SOCIALES",
        "name": "Ciencias Sociales",
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "EXANI_II",
        "code": "HISTORIA",
        "name": "Historia",
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "EXANI_II",
        "code": "LITERATURA",
        "name": "Literatura",
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "EXANI_II",
        "code": "FILOSOFIA",
        "name": "Filosofía",
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "EXANI_II",
        "code": "PSICOLOGIA",
        "name": "Psicología",
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "EXANI_II",
        "code": "PROBABILIDAD_ESTADISTICA",
        "name": "Probabilidad y Estadística",
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "EXANI_II",
        "code": "ARITMETICA_MATEMATICAS_FINANCIERAS",
        "name": (
            "Aritmética / "
            "Matemáticas Financieras"
        ),
    },

    # =========================================================
    # UACH UNIVERSIDAD
    # =========================================================
    {
        "level": "UNIVERSIDAD",
        "institution": "UACH",
        "code": "MEDICINA_CIENCIAS_BIOMEDICAS",
        "name": (
            "Medicina y Ciencias Biomédicas "
            "- Premedicina"
        ),
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "UACH",
        "code": "INGENIERIA",
        "name": (
            "Ingeniería - Cálculo diferencial "
            "e integral + Física"
        ),
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "UACH",
        "code": "DERECHO",
        "name": (
            "Derecho - Derecho + "
            "Ciencias Sociales / Historia"
        ),
    },
    {
        "level": "UNIVERSIDAD",
        "institution": "UACH",
        "code": "CONTADURIA_ADMINISTRACION",
        "name": (
            "Contaduría y Administración - "
            "Administración + Aritmética / "
            "Matemáticas Financieras"
        ),
    },
]


class Command(BaseCommand):
    help = (
        "Carga o actualiza el catálogo "
        "académico base de ELITE."
    )

    def handle(self, *args, **options):
        levels = {}
        institutions = {}

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Cargando niveles educativos..."
            )
        )

        for data in LEVELS:
            obj, created = (
                EducationLevel.objects.update_or_create(
                    code=data["code"],
                    defaults={
                        "name": data["name"],
                        "is_active": True,
                    },
                )
            )

            levels[data["code"]] = obj

            action = (
                "Creado"
                if created
                else "Actualizado"
            )

            self.stdout.write(
                f"  {action}: "
                f"{obj.code} - {obj.name}"
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Cargando instituciones..."
            )
        )

        for data in INSTITUTIONS:
            obj, created = (
                Institution.objects.update_or_create(
                    code=data["code"],
                    defaults={
                        "name": data["name"],
                        "is_active": True,
                    },
                )
            )

            institutions[data["code"]] = obj

            action = (
                "Creada"
                if created
                else "Actualizada"
            )

            self.stdout.write(
                f"  {action}: "
                f"{obj.code} - {obj.name}"
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Cargando áreas y módulos..."
            )
        )

        for data in AREAS:
            level = levels[
                data["level"]
            ]

            institution = institutions[
                data["institution"]
            ]

            obj, created = (
                Area.objects.update_or_create(
                    level=level,
                    institution=institution,
                    code=data["code"],
                    defaults={
                        "name": data["name"],
                        "is_active": True,
                    },
                )
            )

            action = (
                "Creada"
                if created
                else "Actualizada"
            )

            self.stdout.write(
                f"  {action}: "
                f"{institution.code} / "
                f"{obj.code} - "
                f"{obj.name}"
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Catálogo académico base "
                "cargado correctamente."
            )
        )

        self.stdout.write(
            f"Niveles: "
            f"{EducationLevel.objects.count()}"
        )

        self.stdout.write(
            f"Instituciones: "
            f"{Institution.objects.count()}"
        )

        self.stdout.write(
            f"Áreas/módulos: "
            f"{Area.objects.count()}"
        )