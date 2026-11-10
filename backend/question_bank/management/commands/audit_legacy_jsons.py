import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand


LEGACY_ROOT = Path("/legacy_frontend")

JSON_ROOTS = [
    LEGACY_ROOT / "preguntas",
    LEGACY_ROOT / "preguntas_materia",
    LEGACY_ROOT / "preguntas_universidad",
]

DEFAULT_OUTPUT = Path(
    "/reports/legacy_json_audit.json"
)


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

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def normalize_label(value):
    value = normalize_text(value)

    value = re.sub(
        r"[^a-z0-9]+",
        "_",
        value,
    )

    return value.strip("_")


def file_signature(relative_path):
    if not relative_path:
        return None

    path = LEGACY_ROOT / relative_path

    if not path.exists():
        return {
            "exists": False,
            "path": str(relative_path),
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
        "exists": True,
        "path": str(relative_path),
        "sha256": digest.hexdigest(),
    }


def exact_question_fingerprint(question):
    """
    Firma estricta.

    Incluye texto, opciones, respuesta correcta
    e imágenes.

    Sirve para detectar preguntas prácticamente
    idénticas incluyendo sus recursos.
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
                "image": file_signature(
                    option.get("imagen")
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
        "image": file_signature(
            question_data.get("imagen")
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


def content_question_fingerprint(question):
    """
    Firma académica.

    IGNORA las imágenes.

    Si dos preguntas tienen el mismo enunciado,
    opciones y respuesta correcta, quedarán
    agrupadas aunque una de ellas tenga una ruta
    de imagen incorrecta.
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


class Command(BaseCommand):
    help = (
        "Audita los bancos JSON heredados de ELITE "
        "sin modificar PostgreSQL."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default=str(DEFAULT_OUTPUT),
            help=(
                "Ruta del archivo JSON donde se "
                "guardará el reporte."
            ),
        )

    def handle(self, *args, **options):
        output_path = Path(options["output"])

        files = []

        for root in JSON_ROOTS:
            if root.exists():
                files.extend(
                    sorted(root.rglob("*.json"))
                )

        if not files:
            self.stderr.write(
                self.style.ERROR(
                    "No se encontraron archivos JSON."
                )
            )
            return

        exact_subjects = Counter()
        subject_variants = defaultdict(set)

        levels = Counter()
        institutions = Counter()
        option_counts = Counter()

        exact_fingerprints = defaultdict(list)
        content_fingerprints = defaultdict(list)

        file_reports = []
        warnings = []

        total_questions = 0
        question_images = 0
        option_images = 0
        missing_images = 0

        parsed_files = 0
        invalid_json_files = 0

        for json_path in files:
            relative_json_path = json_path.relative_to(
                LEGACY_ROOT
            )

            file_report = {
                "file": str(relative_json_path),
                "valid_json": False,
                "questions": 0,
                "level": None,
                "institution": None,
                "subjects": [],
                "warnings": [],
            }

            try:
                with json_path.open(
                    "r",
                    encoding="utf-8-sig",
                ) as file_obj:
                    data = json.load(file_obj)

                parsed_files += 1
                file_report["valid_json"] = True

            except Exception as exc:
                invalid_json_files += 1

                warning = {
                    "type": "invalid_json",
                    "file": str(relative_json_path),
                    "detail": str(exc),
                }

                file_report["warnings"].append(
                    warning
                )

                warnings.append(warning)
                file_reports.append(file_report)

                continue

            level = data.get("nivel")
            institution = data.get("institucion")

            file_report["level"] = level
            file_report["institution"] = institution

            if level:
                levels[level] += 1

            if institution:
                institutions[institution] += 1

            questions = data.get("preguntas")

            if not isinstance(questions, list):
                warning = {
                    "type": "questions_not_list",
                    "file": str(relative_json_path),
                }

                warnings.append(warning)
                file_report["warnings"].append(
                    warning
                )

                file_reports.append(file_report)

                continue

            file_report["questions"] = len(
                questions
            )

            total_questions += len(questions)

            ids_in_file = Counter()
            subjects_in_file = set()

            for index, question in enumerate(
                questions,
                start=1,
            ):
                question_id = question.get("id")

                if question_id is not None:
                    ids_in_file[str(question_id)] += 1

                else:
                    warning = {
                        "type": "missing_question_id",
                        "file": str(
                            relative_json_path
                        ),
                        "position": index,
                    }

                    warnings.append(warning)
                    file_report["warnings"].append(
                        warning
                    )

                subject = question.get("materia")

                if not subject:
                    warning = {
                        "type": "missing_subject",
                        "file": str(
                            relative_json_path
                        ),
                        "question_id": question_id,
                    }

                    warnings.append(warning)
                    file_report["warnings"].append(
                        warning
                    )

                else:
                    exact_subjects[subject] += 1

                    normalized_subject = (
                        normalize_label(subject)
                    )

                    subject_variants[
                        normalized_subject
                    ].add(subject)

                    subjects_in_file.add(subject)

                question_data = (
                    question.get("pregunta") or {}
                )

                content = question_data.get(
                    "contenido"
                )

                if not content:
                    warning = {
                        "type": "empty_question_content",
                        "file": str(
                            relative_json_path
                        ),
                        "question_id": question_id,
                    }

                    warnings.append(warning)
                    file_report["warnings"].append(
                        warning
                    )

                question_image = question_data.get(
                    "imagen"
                )

                question_image_exists = False

                if question_image:
                    question_images += 1

                    signature = file_signature(
                        question_image
                    )

                    question_image_exists = (
                        signature["exists"]
                    )

                    if not question_image_exists:
                        missing_images += 1

                        warning = {
                            "type": (
                                "missing_question_image"
                            ),
                            "file": str(
                                relative_json_path
                            ),
                            "question_id": question_id,
                            "image": question_image,
                        }

                        warnings.append(warning)

                        file_report[
                            "warnings"
                        ].append(warning)

                options = question.get("opciones")

                if not isinstance(options, list):
                    warning = {
                        "type": "options_not_list",
                        "file": str(
                            relative_json_path
                        ),
                        "question_id": question_id,
                    }

                    warnings.append(warning)

                    file_report[
                        "warnings"
                    ].append(warning)

                    options = []

                option_counts[len(options)] += 1

                labels = []

                for option in options:
                    label = option.get("inciso")

                    if label:
                        labels.append(str(label))

                    option_image = option.get(
                        "imagen"
                    )

                    if option_image:
                        option_images += 1

                        signature = file_signature(
                            option_image
                        )

                        if not signature["exists"]:
                            missing_images += 1

                            warning = {
                                "type": (
                                    "missing_option_image"
                                ),
                                "file": str(
                                    relative_json_path
                                ),
                                "question_id": (
                                    question_id
                                ),
                                "label": label,
                                "image": option_image,
                            }

                            warnings.append(
                                warning
                            )

                            file_report[
                                "warnings"
                            ].append(warning)

                duplicate_labels = [
                    label
                    for label, count
                    in Counter(labels).items()
                    if count > 1
                ]

                if duplicate_labels:
                    warning = {
                        "type": (
                            "duplicate_option_labels"
                        ),
                        "file": str(
                            relative_json_path
                        ),
                        "question_id": question_id,
                        "labels": duplicate_labels,
                    }

                    warnings.append(warning)

                    file_report[
                        "warnings"
                    ].append(warning)

                correct = question.get(
                    "respuesta_correcta"
                )

                if not correct:
                    warning = {
                        "type": (
                            "missing_correct_answer"
                        ),
                        "file": str(
                            relative_json_path
                        ),
                        "question_id": question_id,
                    }

                    warnings.append(warning)

                    file_report[
                        "warnings"
                    ].append(warning)

                elif str(correct) not in labels:
                    warning = {
                        "type": (
                            "correct_answer_not_in_options"
                        ),
                        "file": str(
                            relative_json_path
                        ),
                        "question_id": question_id,
                        "correct_answer": correct,
                        "available_labels": labels,
                    }

                    warnings.append(warning)

                    file_report[
                        "warnings"
                    ].append(warning)

                exact_fingerprint = (
                    exact_question_fingerprint(
                        question
                    )
                )

                content_fingerprint = (
                    content_question_fingerprint(
                        question
                    )
                )

                occurrence = {
                    "file": str(
                        relative_json_path
                    ),
                    "question_id": question_id,
                    "subject": subject,
                    "question_image": question_image,
                    "question_image_exists": (
                        question_image_exists
                    ),
                }

                exact_fingerprints[
                    exact_fingerprint
                ].append(occurrence)

                content_fingerprints[
                    content_fingerprint
                ].append(occurrence)

            duplicate_ids = [
                question_id
                for question_id, count
                in ids_in_file.items()
                if count > 1
            ]

            if duplicate_ids:
                warning = {
                    "type": (
                        "duplicate_question_ids"
                    ),
                    "file": str(relative_json_path),
                    "ids": duplicate_ids,
                }

                warnings.append(warning)

                file_report["warnings"].append(
                    warning
                )

            file_report["subjects"] = sorted(
                subjects_in_file
            )

            file_reports.append(file_report)

        # =====================================================
        # Duplicados exactos
        # =====================================================

        exact_duplicate_groups = []

        for fingerprint, occurrences in (
            exact_fingerprints.items()
        ):
            if len(occurrences) > 1:
                exact_duplicate_groups.append(
                    {
                        "fingerprint": fingerprint,
                        "occurrences": occurrences,
                    }
                )

        # =====================================================
        # Duplicados académicos ignorando imágenes
        # =====================================================

        content_duplicate_groups = []

        for fingerprint, occurrences in (
            content_fingerprints.items()
        ):
            if len(occurrences) > 1:
                content_duplicate_groups.append(
                    {
                        "fingerprint": fingerprint,
                        "occurrences": occurrences,
                    }
                )

        # =====================================================
        # Recuperación potencial de imágenes faltantes
        # =====================================================

        recoverable_missing_question_images = []
        unresolved_missing_question_images = []

        for fingerprint, occurrences in (
            content_fingerprints.items()
        ):
            valid_image_occurrences = [
                occurrence
                for occurrence in occurrences
                if (
                    occurrence[
                        "question_image"
                    ]
                    and occurrence[
                        "question_image_exists"
                    ]
                )
            ]

            missing_image_occurrences = [
                occurrence
                for occurrence in occurrences
                if (
                    occurrence[
                        "question_image"
                    ]
                    and not occurrence[
                        "question_image_exists"
                    ]
                )
            ]

            for missing_occurrence in (
                missing_image_occurrences
            ):
                if valid_image_occurrences:
                    recoverable_missing_question_images.append(
                        {
                            "target": missing_occurrence,
                            "candidate_sources": (
                                valid_image_occurrences
                            ),
                            "content_fingerprint": (
                                fingerprint
                            ),
                        }
                    )

                else:
                    unresolved_missing_question_images.append(
                        {
                            "target": missing_occurrence,
                            "content_fingerprint": (
                                fingerprint
                            ),
                        }
                    )

        variant_groups = {
            normalized: sorted(variants)
            for normalized, variants
            in subject_variants.items()
            if len(variants) > 1
        }

        warning_counts = Counter(
            warning["type"]
            for warning in warnings
        )

        report = {
            "summary": {
                "json_files_found": len(files),
                "json_files_parsed": parsed_files,
                "invalid_json_files": (
                    invalid_json_files
                ),
                "total_questions": total_questions,
                "question_image_references": (
                    question_images
                ),
                "option_image_references": (
                    option_images
                ),
                "missing_image_references": (
                    missing_images
                ),
                "unique_subject_names": len(
                    exact_subjects
                ),
                "subject_variant_groups": len(
                    variant_groups
                ),
                "exact_duplicate_groups": len(
                    exact_duplicate_groups
                ),
                "content_duplicate_groups": len(
                    content_duplicate_groups
                ),
                "recoverable_missing_question_images": (
                    len(
                        recoverable_missing_question_images
                    )
                ),
                "unresolved_missing_question_images": (
                    len(
                        unresolved_missing_question_images
                    )
                ),
                "warnings": len(warnings),
            },

            "levels": [
                {
                    "name": name,
                    "count": count,
                }
                for name, count
                in sorted(levels.items())
            ],

            "institutions": [
                {
                    "name": name,
                    "count": count,
                }
                for name, count
                in sorted(institutions.items())
            ],

            "option_count_distribution": [
                {
                    "options": key,
                    "questions": value,
                }
                for key, value
                in sorted(option_counts.items())
            ],

            "subjects": [
                {
                    "name": name,
                    "count": count,
                }
                for name, count
                in sorted(exact_subjects.items())
            ],

            "subject_variants": [
                {
                    "normalized": normalized,
                    "variants": variants,
                }
                for normalized, variants
                in sorted(variant_groups.items())
            ],

            "warning_counts": [
                {
                    "type": warning_type,
                    "count": count,
                }
                for warning_type, count
                in sorted(warning_counts.items())
            ],

            "exact_duplicates": (
                exact_duplicate_groups
            ),

            "content_duplicates": (
                content_duplicate_groups
            ),

            "recoverable_missing_question_images": (
                recoverable_missing_question_images
            ),

            "unresolved_missing_question_images": (
                unresolved_missing_question_images
            ),

            "warnings": warnings,
            "files": file_reports,
        }

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with output_path.open(
            "w",
            encoding="utf-8",
        ) as output_file:
            json.dump(
                report,
                output_file,
                ensure_ascii=False,
                indent=2,
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Auditoría completada."
            )
        )

        self.stdout.write(
            f"JSON encontrados: {len(files)}"
        )

        self.stdout.write(
            f"JSON válidos: {parsed_files}"
        )

        self.stdout.write(
            f"JSON inválidos: {invalid_json_files}"
        )

        self.stdout.write(
            f"Preguntas totales: {total_questions}"
        )

        self.stdout.write(
            "Referencias de imagen en pregunta: "
            f"{question_images}"
        )

        self.stdout.write(
            "Referencias de imagen en opciones: "
            f"{option_images}"
        )

        self.stdout.write(
            "Referencias de imagen faltantes: "
            f"{missing_images}"
        )

        self.stdout.write(
            "Nombres exactos de materia: "
            f"{len(exact_subjects)}"
        )

        self.stdout.write(
            "Grupos con variantes de materia: "
            f"{len(variant_groups)}"
        )

        self.stdout.write(
            "Duplicados exactos: "
            f"{len(exact_duplicate_groups)}"
        )

        self.stdout.write(
            "Duplicados por contenido: "
            f"{len(content_duplicate_groups)}"
        )

        self.stdout.write(
            "Imágenes faltantes recuperables: "
            f"{len(recoverable_missing_question_images)}"
        )

        self.stdout.write(
            "Imágenes faltantes sin resolver: "
            f"{len(unresolved_missing_question_images)}"
        )

        self.stdout.write(
            f"Advertencias totales: "
            f"{len(warnings)}"
        )

        self.stdout.write("")
        self.stdout.write(
            f"Reporte guardado en: "
            f"{output_path}"
        )