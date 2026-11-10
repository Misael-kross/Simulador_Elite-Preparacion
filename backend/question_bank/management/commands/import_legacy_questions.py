import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


LEGACY_ROOT = Path("/legacy_frontend")

JSON_ROOTS = [
    LEGACY_ROOT / "preguntas",
    LEGACY_ROOT / "preguntas_materia",
    LEGACY_ROOT / "preguntas_universidad",
]


def normalize_text(value):
    if value is None:
        return ""

    value = str(value).strip()
    value = unicodedata.normalize("NFKD", value)

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    value = value.lower()
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_subject_key(value):
    value = normalize_text(value)
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


SUBJECT_NORMALIZATION = {
    "formacion_civica_y_etica": "Formación Cívica y Ética",
    "habilidad_matematica": "Habilidad Matemática",
    "matematicas": "Matemáticas",
}


def canonical_subject(value):
    if not value:
        return None

    key = normalize_subject_key(value)

    return SUBJECT_NORMALIZATION.get(
        key,
        str(value).strip(),
    )


def resolve_legacy_path(relative_path):
    if not relative_path:
        return None

    clean_path = str(relative_path).replace("\\", "/")
    clean_path = clean_path.lstrip("./")

    return LEGACY_ROOT / clean_path


def file_info(relative_path):
    if not relative_path:
        return {
            "path": None,
            "exists": False,
            "sha256": None,
        }

    path = resolve_legacy_path(relative_path)

    if not path or not path.is_file():
        return {
            "path": str(relative_path),
            "exists": False,
            "sha256": None,
        }

    digest = hashlib.sha256()

    with path.open("rb") as file_obj:
        for chunk in iter(
            lambda: file_obj.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return {
        "path": str(relative_path),
        "exists": True,
        "sha256": digest.hexdigest(),
    }


def content_fingerprint(question):
    """
    Identidad académica candidata.

    Ignora las rutas de imágenes para poder
    detectar copias beta cuya ruta esté rota.

    No se usa todavía para escribir en PostgreSQL.
    """

    question_data = question.get("pregunta") or {}
    options = question.get("opciones") or []

    canonical_options = []

    for option in options:
        canonical_options.append(
            {
                "label": normalize_text(
                    option.get("inciso")
                ),
                "text": normalize_text(
                    option.get("texto")
                ),
            }
        )

    canonical = {
        "type": normalize_text(
            question_data.get("tipo")
        ),
        "content": normalize_text(
            question_data.get("contenido")
        ),
        "options": canonical_options,
        "correct": normalize_text(
            question.get("respuesta_correcta")
        ),
    }

    encoded = json.dumps(
        canonical,
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def option_resource_signature(question):
    """
    Identidad visual de las opciones.

    Compara el contenido real de los archivos
    mediante SHA-256, no sus rutas.
    """

    options = question.get("opciones") or []

    signature = []

    for option in options:
        image = option.get("imagen")
        info = file_info(image)

        signature.append(
            (
                str(option.get("inciso") or ""),
                bool(image),
                info["sha256"],
                info["exists"],
            )
        )

    return tuple(signature)

def visual_resource_profile(question):
    """
    Describe la identidad visual completa de
    una pregunta.

    Permite distinguir preguntas cuyo texto es
    igual pero cuyos gráficos son diferentes.
    """

    question_data = question.get("pregunta") or {}

    question_image = question_data.get("imagen")
    question_info = file_info(question_image)

    options = question.get("opciones") or []

    option_signature = []
    complete = True

    if (
        question_image
        and not question_info["exists"]
    ):
        complete = False

    for option in options:
        image = option.get("imagen")
        info = file_info(image)

        if image and not info["exists"]:
            complete = False

        option_signature.append(
            (
                str(option.get("inciso") or ""),
                bool(image),
                info["sha256"],
            )
        )

    signature = (
        bool(question_image),
        question_info["sha256"],
        tuple(option_signature),
    )

    return {
        "signature": signature,
        "complete": complete,
    }

class Command(BaseCommand):
    help = (
        "Simula la importación del banco heredado "
        "de preguntas de ELITE."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Analiza la importación sin escribir "
                "ningún dato en PostgreSQL."
            ),
        )

    def handle(self, *args, **options):
        if not options["dry_run"]:
            raise CommandError(
                "Por seguridad, esta versión solo puede "
                "ejecutarse usando --dry-run."
            )

        files = []

        for root in JSON_ROOTS:
            if root.exists():
                files.extend(
                    sorted(root.rglob("*.json"))
                )

        if not files:
            raise CommandError(
                "No se encontraron JSON heredados."
            )

        groups = defaultdict(list)

        subject_counts = Counter()
        raw_subject_counts = Counter()

        json_valid = 0
        json_invalid = 0
        total_records = 0
        total_choices = 0

        for json_path in files:
            relative_json = json_path.relative_to(
                LEGACY_ROOT
            )

            try:
                with json_path.open(
                    "r",
                    encoding="utf-8-sig",
                ) as file_obj:
                    data = json.load(file_obj)

            except Exception as exc:
                json_invalid += 1

                self.stderr.write(
                    self.style.ERROR(
                        f"JSON inválido: "
                        f"{relative_json} -> {exc}"
                    )
                )

                continue

            json_valid += 1

            questions = data.get("preguntas")

            if not isinstance(questions, list):
                self.stderr.write(
                    self.style.WARNING(
                        f"Sin lista válida de preguntas: "
                        f"{relative_json}"
                    )
                )
                continue

            for position, question in enumerate(
                questions,
                start=1,
            ):
                total_records += 1

                options_list = (
                    question.get("opciones") or []
                )

                if isinstance(options_list, list):
                    total_choices += len(options_list)
                else:
                    options_list = []

                raw_subject = question.get("materia")
                subject = canonical_subject(raw_subject)

                if raw_subject:
                    raw_subject_counts[
                        str(raw_subject)
                    ] += 1

                if subject:
                    subject_counts[subject] += 1

                question_data = (
                    question.get("pregunta") or {}
                )

                image_path = question_data.get(
                    "imagen"
                )
                image_info = file_info(image_path)

                visual_profile = visual_resource_profile(
                question
                )

                fingerprint = content_fingerprint(
                question
                )

                occurrence = {
                    "file": str(
                        relative_json
                    ),
                    "position": position,
                    "question_id": question.get("id"),
                    "raw_subject": raw_subject,
                    "subject": subject,
                    "question_image": image_path,
                    "question_image_exists": (
                        image_info["exists"]
                    ),
                    "question_image_sha256": (
                        image_info["sha256"]
                    ),
                    "option_resource_signature": (
                        option_resource_signature(
                            question
                        )
                    ),
                    "visual_signature": (
                        visual_profile["signature"]
                    ),
                    "visual_complete": (
                        visual_profile["complete"]
                    ),
                    "choice_count": len(
                        options_list
                    ),
                }

                groups[fingerprint].append(
                    occurrence
                )

        # =====================================================
        # Analizar grupos candidatos a una Question única
        # =====================================================

               # =====================================================
        # Refinar grupos usando identidad visual
        # =====================================================

        refined_groups = []

        for fingerprint, occurrences in groups.items():
            complete_visual_groups = defaultdict(list)
            incomplete_occurrences = []

            for occurrence in occurrences:
                if occurrence["visual_complete"]:
                    visual_key = json.dumps(
                        occurrence["visual_signature"],
                        sort_keys=True,
                        ensure_ascii=False,
                    )

                    complete_visual_groups[
                        visual_key
                    ].append(occurrence)

                else:
                    incomplete_occurrences.append(
                        occurrence
                    )

            # ---------------------------------------------
            # Caso 1:
            # No existen múltiples versiones visuales.
            # ---------------------------------------------

            if len(complete_visual_groups) <= 1:
                refined_groups.append(
                    {
                        "fingerprint": fingerprint,
                        "occurrences": occurrences,
                        "visual_ambiguity": False,
                    }
                )

                continue

            # ---------------------------------------------
            # Caso 2:
            # Mismo texto pero imágenes válidas distintas.
            #
            # Son preguntas diferentes.
            # ---------------------------------------------

            for index, visual_occurrences in enumerate(
                complete_visual_groups.values(),
                start=1,
            ):
                refined_groups.append(
                    {
                        "fingerprint": (
                            f"{fingerprint}:visual:{index}"
                        ),
                        "occurrences": visual_occurrences,
                        "visual_ambiguity": False,
                    }
                )

            # ---------------------------------------------
            # Caso 3:
            # Existen varias preguntas visualmente
            # diferentes y además una copia con imagen
            # rota.
            #
            # No podemos saber automáticamente a cuál
            # pertenece esa copia.
            # ---------------------------------------------

            if incomplete_occurrences:
                refined_groups.append(
                    {
                        "fingerprint": (
                            f"{fingerprint}:"
                            "unresolved-visual"
                        ),
                        "occurrences": (
                            incomplete_occurrences
                        ),
                        "visual_ambiguity": True,
                    }
                )

        # =====================================================
        # Analizar preguntas únicas refinadas
        # =====================================================

        candidate_unique_questions = len(
            refined_groups
        )

        duplicate_occurrences = (
            total_records
            - candidate_unique_questions
        )

        duplicate_groups = 0

        recoverable_missing_images = 0
        unresolved_missing_images = 0

        groups_with_unresolved_images = 0
        groups_with_resource_conflicts = 0

        safe_groups = 0

        estimated_unique_choices = 0

        review_groups = []

        for group in refined_groups:
            fingerprint = group["fingerprint"]
            occurrences = group["occurrences"]

            if len(occurrences) > 1:
                duplicate_groups += 1

            estimated_unique_choices += (
                occurrences[0]["choice_count"]
            )

            valid_question_hashes = {
                occurrence[
                    "question_image_sha256"
                ]
                for occurrence in occurrences
                if occurrence[
                    "question_image_sha256"
                ]
            }

            missing_question_images = [
                occurrence
                for occurrence in occurrences
                if (
                    occurrence["question_image"]
                    and not occurrence[
                        "question_image_exists"
                    ]
                )
            ]

            unresolved = False
            resource_conflict = False

            if group["visual_ambiguity"]:
                resource_conflict = True

            if missing_question_images:
                if len(valid_question_hashes) == 1:
                    recoverable_missing_images += len(
                        missing_question_images
                    )

                elif len(valid_question_hashes) == 0:
                    unresolved = True

                    unresolved_missing_images += len(
                        missing_question_images
                    )

                else:
                    resource_conflict = True

            if unresolved:
                groups_with_unresolved_images += 1

            if resource_conflict:
                groups_with_resource_conflicts += 1

            if not unresolved and not resource_conflict:
                safe_groups += 1

            else:
                review_groups.append(
                    {
                        "fingerprint": fingerprint,
                        "unresolved_image": unresolved,
                        "resource_conflict": (
                            resource_conflict
                        ),
                        "occurrences": occurrences,
                    }
                )

        normalized_changes = []

        for raw_name in sorted(raw_subject_counts):
            canonical = canonical_subject(raw_name)

            if canonical != raw_name:
                normalized_changes.append(
                    {
                        "from": raw_name,
                        "to": canonical,
                        "count": (
                            raw_subject_counts[raw_name]
                        ),
                    }
                )

        # =====================================================
        # Resultado
        # =====================================================

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "SIMULACIÓN DE IMPORTACIÓN COMPLETADA"
            )
        )

        self.stdout.write("")
        self.stdout.write(
            "No se escribió ningún dato "
            "en PostgreSQL."
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "ARCHIVOS"
            )
        )

        self.stdout.write(
            f"JSON encontrados: {len(files)}"
        )

        self.stdout.write(
            f"JSON válidos: {json_valid}"
        )

        self.stdout.write(
            f"JSON inválidos: {json_invalid}"
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "PREGUNTAS"
            )
        )

        self.stdout.write(
            f"Registros heredados: {total_records}"
        )

        self.stdout.write(
            "Grupos candidatos a preguntas únicas: "
            f"{candidate_unique_questions}"
        )

        self.stdout.write(
            "Registros duplicados potencialmente "
            "reutilizables: "
            f"{duplicate_occurrences}"
        )

        self.stdout.write(
            f"Grupos con duplicados: "
            f"{duplicate_groups}"
        )

        self.stdout.write(
            "Grupos seguros para importación: "
            f"{safe_groups}"
        )

        self.stdout.write(
            "Grupos que requieren revisión: "
            f"{len(review_groups)}"
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "IMÁGENES"
            )
        )

        self.stdout.write(
            "Referencias rotas recuperables "
            "desde duplicados: "
            f"{recoverable_missing_images}"
        )

        self.stdout.write(
            "Referencias rotas sin duplicado "
            "válido: "
            f"{unresolved_missing_images}"
        )

        self.stdout.write(
            "Grupos con recursos visuales "
            "en conflicto: "
            f"{groups_with_resource_conflicts}"
        )

        self.stdout.write(
            "Grupos con imágenes sin resolver: "
            f"{groups_with_unresolved_images}"
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "MATERIAS"
            )
        )

        self.stdout.write(
            f"Materias canónicas detectadas: "
            f"{len(subject_counts)}"
        )

        for subject, count in sorted(
            subject_counts.items()
        ):
            self.stdout.write(
                f"  {subject}: {count}"
            )

        self.stdout.write("")
        self.stdout.write(
            "Normalizaciones aplicadas "
            "durante la simulación:"
        )

        if normalized_changes:
            for change in normalized_changes:
                self.stdout.write(
                    f"  {change['from']} -> "
                    f"{change['to']} "
                    f"({change['count']} registros)"
                )

        else:
            self.stdout.write(
                "  Ninguna."
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "ESTIMACIÓN DE OBJETOS"
            )
        )

        self.stdout.write(
            "Question candidatas: "
            f"{candidate_unique_questions}"
        )

        self.stdout.write(
            "QuestionVersion candidatas: "
            f"{candidate_unique_questions}"
        )

        self.stdout.write(
            "Choice candidatas aproximadas: "
            f"{estimated_unique_choices}"
        )
        review_output = Path(
            "/reports/import_review_groups.json"
        )

        with review_output.open(
            "w",
            encoding="utf-8",
        ) as review_file:
            json.dump(
                review_groups,
                review_file,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

        self.stdout.write(
            "Reporte de grupos para revisión: "
            f"{review_output}"
        )
        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "Todavía NO se ha autorizado "
                "la importación real."
            )
        )

        if review_groups:
            self.stdout.write(
                self.style.WARNING(
                    "Existen grupos que deben "
                    "revisarse antes de escribir "
                    "en PostgreSQL."
                )
            )