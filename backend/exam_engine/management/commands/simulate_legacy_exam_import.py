import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand

from question_bank.models import (
    Area,
    EducationLevel,
    Institution,
)

from question_bank.management.commands.import_legacy_questions import (
    canonical_subject,
    content_fingerprint,
    visual_resource_profile,
)


LEGACY_ROOT = Path("/legacy_frontend")

JSON_ROOTS = [
    LEGACY_ROOT / "preguntas",
    LEGACY_ROOT / "preguntas_materia",
    LEGACY_ROOT / "preguntas_universidad",
]

REPORT_PATH = Path(
    "/reports/exam_import_dry_run.json"
)


INSTITUTION_ALIASES = {
    "ecoems": "ECOEMS",
    "ceneval_exani_i": "CENEVAL_EXANI_I",
    "exani_i": "CENEVAL_EXANI_I",
    "uach": "UACH",
    "unam": "UNAM",
    "ipn": "IPN",
    "uam": "UAM",
    "exani_ii": "EXANI_II",
    "ceneval_exani_ii": "EXANI_II",
}


AREA_CODES = {
    "UNAM": {
        "area1": "AREA1",
        "area2": "AREA2",
        "area3": "AREA3",
        "area4": "AREA4",
    },

    "IPN": {
        "iycfm": "IYCFM",
        "cmb": "CMB",
        "csa": "CSA",
    },

    "UAM": {
        "cbi": "CBI",
        "cbs": "CBS",
        "csh": "CSH",
        "cad": "CAD",
        "cni": "CNI",
        "ccd": "CCD",
    },

    "EXANI_II": {
        "premedicina": "PREMEDICINA",
        "ciencias_salud": "CIENCIAS_SALUD",
        "calculo": "CALCULO",
        "fisica": "FISICA",
        "quimica": "QUIMICA",
        "biologia": "BIOLOGIA",
        "administracion": "ADMINISTRACION",
        "economia": "ECONOMIA",
        "derecho": "DERECHO",
        "ciencias_sociales": "CIENCIAS_SOCIALES",
        "historia": "HISTORIA",
        "literatura": "LITERATURA",
        "filosofia": "FILOSOFIA",
        "psicologia": "PSICOLOGIA",
        "probabilidad_estadistica": (
            "PROBABILIDAD_ESTADISTICA"
        ),
        "aritmetica_matematicas_financieras": (
            "ARITMETICA_MATEMATICAS_FINANCIERAS"
        ),
    },

    "UACH": {
        "medicina_ciencias_biomedicas": (
            "MEDICINA_CIENCIAS_BIOMEDICAS"
        ),
        "ingenieria": "INGENIERIA",
        "derecho": "DERECHO",
        "contaduria_administracion": (
            "CONTADURIA_ADMINISTRACION"
        ),
    },
}


def normalize_key(value):
    if value is None:
        return ""

    value = str(value).strip()

    value = unicodedata.normalize(
        "NFKD",
        value,
    )

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    value = value.lower()

    value = re.sub(
        r"[^a-z0-9]+",
        "_",
        value,
    )

    return value.strip("_")


def canonical_level(value):
    key = normalize_key(value)

    if key in {
        "bachillerato",
        "media_superior",
        "educacion_media_superior",
        "preparatoria",
    }:
        return "BACHILLERATO"

    if key in {
        "universidad",
        "superior",
        "educacion_superior",
        "licenciatura",
    }:
        return "UNIVERSIDAD"

    return None


def canonical_institution(value, relative_path):
    key = normalize_key(value)

    if key in INSTITUTION_ALIASES:
        return INSTITUTION_ALIASES[key]

    parts = [
        normalize_key(part)
        for part in relative_path.parts
    ]

    for part in parts:
        if part in INSTITUTION_ALIASES:
            return INSTITUTION_ALIASES[part]

    return None


def source_kind(relative_path):
    root = relative_path.parts[0]

    if root == "preguntas":
        return "GENERAL"

    if root == "preguntas_materia":
        return "SUBJECT"

    if root == "preguntas_universidad":
        return "UNIVERSITY"

    return "OTHER"


def infer_area_code(
    relative_path,
    institution_code,
):
    if not institution_code:
        return None

    mappings = AREA_CODES.get(
        institution_code,
        {},
    )

    normalized_parts = [
        normalize_key(part)
        for part in relative_path.parts
    ]

    for part in normalized_parts:
        if part in mappings:
            return mappings[part]

    return None


def build_exam_code(relative_path):
    value = str(
        relative_path.with_suffix("")
    )

    value = value.replace("\\", "/")

    value = normalize_key(value)

    return f"LEGACY_{value.upper()}"


def configured_duration(configuration):
    candidates = [
        "duracion",
        "duración",
        "duration",
        "duracion_minutos",
    ]

    for key in candidates:
        value = configuration.get(key)

        if value is None:
            continue

        try:
            return int(value)

        except (TypeError, ValueError):
            pass

    return None


def config_boolean(
    configuration,
    keys,
    default,
):
    for key in keys:
        if key in configuration:
            return bool(
                configuration[key]
            )

    return default


class Command(BaseCommand):
    help = (
        "Simula la conversión de los JSON "
        "heredados en ExamTemplate y "
        "ExamQuestion sin escribir en PostgreSQL."
    )

    def handle(self, *args, **options):
        files = []

        for root in JSON_ROOTS:
            if root.exists():
                files.extend(
                    sorted(
                        root.rglob("*.json")
                    )
                )

        parsed = []

        question_groups = defaultdict(list)

        invalid_json = []

        for path in files:
            relative_path = path.relative_to(
                LEGACY_ROOT
            )

            try:
                with path.open(
                    "r",
                    encoding="utf-8-sig",
                ) as file_obj:
                    data = json.load(file_obj)

            except Exception as exc:
                invalid_json.append(
                    {
                        "file": str(
                            relative_path
                        ),
                        "error": str(exc),
                    }
                )
                continue

            questions = data.get(
                "preguntas"
            )

            if not isinstance(
                questions,
                list,
            ):
                invalid_json.append(
                    {
                        "file": str(
                            relative_path
                        ),
                        "error": (
                            "preguntas no es "
                            "una lista"
                        ),
                    }
                )
                continue

            exam_record = {
                "path": path,
                "relative_path": (
                    relative_path
                ),
                "data": data,
                "questions": questions,
            }

            parsed.append(
                exam_record
            )

            for position, question in enumerate(
                questions,
                start=1,
            ):
                fingerprint = (
                    content_fingerprint(
                        question
                    )
                )

                profile = (
                    visual_resource_profile(
                        question
                    )
                )

                occurrence = {
                    "file": str(
                        relative_path
                    ),
                    "position": position,
                    "legacy_question_id": (
                        question.get("id")
                    ),
                    "subject": (
                        canonical_subject(
                            question.get(
                                "materia"
                            )
                        )
                    ),
                    "visual_signature": (
                        profile["signature"]
                    ),
                    "visual_complete": (
                        profile["complete"]
                    ),
                }

                question_groups[
                    fingerprint
                ].append(
                    occurrence
                )

        candidate_groups = []

        occurrence_mapping = {}

        for fingerprint, occurrences in (
            question_groups.items()
        ):
            complete_groups = defaultdict(
                list
            )

            incomplete = []

            for occurrence in occurrences:
                if occurrence[
                    "visual_complete"
                ]:
                    visual_key = json.dumps(
                        occurrence[
                            "visual_signature"
                        ],
                        sort_keys=True,
                        ensure_ascii=False,
                    )

                    complete_groups[
                        visual_key
                    ].append(
                        occurrence
                    )

                else:
                    incomplete.append(
                        occurrence
                    )

            if len(complete_groups) <= 1:
                candidate_key = fingerprint

                candidate_groups.append(
                    {
                        "key": candidate_key,
                        "occurrences": (
                            occurrences
                        ),
                        "needs_review": (
                            bool(incomplete)
                            and not complete_groups
                        ),
                    }
                )

                for occurrence in occurrences:
                    occurrence_mapping[
                        (
                            occurrence["file"],
                            occurrence["position"],
                        )
                    ] = candidate_key

                continue

            for index, visual_occurrences in (
                enumerate(
                    complete_groups.values(),
                    start=1,
                )
            ):
                candidate_key = (
                    f"{fingerprint}:"
                    f"visual:{index}"
                )

                candidate_groups.append(
                    {
                        "key": candidate_key,
                        "occurrences": (
                            visual_occurrences
                        ),
                        "needs_review": False,
                    }
                )

                for occurrence in (
                    visual_occurrences
                ):
                    occurrence_mapping[
                        (
                            occurrence["file"],
                            occurrence["position"],
                        )
                    ] = candidate_key

            if incomplete:
                candidate_key = (
                    f"{fingerprint}:"
                    "unresolved-visual"
                )

                candidate_groups.append(
                    {
                        "key": candidate_key,
                        "occurrences": (
                            incomplete
                        ),
                        "needs_review": True,
                    }
                )

                for occurrence in incomplete:
                    occurrence_mapping[
                        (
                            occurrence["file"],
                            occurrence["position"],
                        )
                    ] = candidate_key

        exam_reports = []

        source_counts = Counter()

        total_positions = 0
        mapped_positions = 0

        duplicate_exam_codes = Counter()

        catalog_errors = []

        subjects_to_create = set()

        for exam_record in parsed:
            relative_path = exam_record[
                "relative_path"
            ]

            data = exam_record["data"]

            questions = exam_record[
                "questions"
            ]

            kind = source_kind(
                relative_path
            )

            source_counts[kind] += 1

            level_code = canonical_level(
                data.get("nivel")
            )

            institution_code = (
                canonical_institution(
                    data.get(
                        "institucion"
                    ),
                    relative_path,
                )
            )

            area_code = infer_area_code(
                relative_path,
                institution_code,
            )

            exam_code = build_exam_code(
                relative_path
            )

            duplicate_exam_codes[
                exam_code
            ] += 1

            configuration = (
                data.get(
                    "configuracion"
                )
                or {}
            )

            subjects = {
                canonical_subject(
                    question.get(
                        "materia"
                    )
                )
                for question in questions
                if question.get(
                    "materia"
                )
            }

            subjects.discard(None)

            for subject in subjects:
                subjects_to_create.add(
                    subject
                )

            template_subject = None

            if (
                kind == "SUBJECT"
                and len(subjects) == 1
            ):
                template_subject = next(
                    iter(subjects)
                )

            level_exists = False

            if level_code:
                level_exists = (
                    EducationLevel.objects.filter(
                        code=level_code
                    ).exists()
                )

            institution_exists = False

            if institution_code:
                institution_exists = (
                    Institution.objects.filter(
                        code=institution_code
                    ).exists()
                )

            area_exists = True

            if area_code:
                area_exists = (
                    Area.objects.filter(
                        code=area_code,
                        institution__code=(
                            institution_code
                        ),
                        level__code=level_code,
                    ).exists()
                )

            if not level_exists:
                catalog_errors.append(
                    {
                        "file": str(
                            relative_path
                        ),
                        "type": (
                            "level_not_resolved"
                        ),
                        "value": level_code,
                    }
                )

            if not institution_exists:
                catalog_errors.append(
                    {
                        "file": str(
                            relative_path
                        ),
                        "type": (
                            "institution_not_resolved"
                        ),
                        "value": (
                            institution_code
                        ),
                    }
                )

            if (
                area_code
                and not area_exists
            ):
                catalog_errors.append(
                    {
                        "file": str(
                            relative_path
                        ),
                        "type": (
                            "area_not_resolved"
                        ),
                        "value": area_code,
                    }
                )

            positions = []

            for position, question in enumerate(
                questions,
                start=1,
            ):
                total_positions += 1

                mapping_key = (
                    str(relative_path),
                    position,
                )

                candidate_key = (
                    occurrence_mapping.get(
                        mapping_key
                    )
                )

                if candidate_key:
                    mapped_positions += 1

                positions.append(
                    {
                        "position": position,
                        "legacy_question_id": (
                            question.get("id")
                        ),
                        "subject": (
                            canonical_subject(
                                question.get(
                                    "materia"
                                )
                            )
                        ),
                        "candidate_question": (
                            candidate_key
                        ),
                    }
                )

            exam_reports.append(
                {
                    "code": exam_code,
                    "name": (
                        data.get("nombre")
                        or relative_path.stem
                    ),
                    "legacy_source_file": str(
                        relative_path
                    ),
                    "level": level_code,
                    "institution": (
                        institution_code
                    ),
                    "area": area_code,
                    "subject": (
                        template_subject
                    ),
                    "source_kind": kind,
                    "mode": "FIXED",
                    "legacy_version": str(
                        data.get(
                            "version",
                            "",
                        )
                    ),
                    "duration_minutes": (
                        configured_duration(
                            configuration
                        )
                    ),
                    "timer_allowed": (
                        config_boolean(
                            configuration,
                            [
                                "contador_permitido",
                            ],
                            True,
                        )
                    ),
                    "timer_active_by_default": (
                        config_boolean(
                            configuration,
                            [
                                "contador_activo_por_defecto",
                            ],
                            False,
                        )
                    ),
                    "auto_close": (
                        config_boolean(
                            configuration,
                            [
                                "cerrar_automaticamente",
                            ],
                            False,
                        )
                    ),
                    "allow_review": (
                        config_boolean(
                            configuration,
                            [
                                "permitir_revision",
                            ],
                            True,
                        )
                    ),
                    "show_results_by_subject": (
                        config_boolean(
                            configuration,
                            [
                                "mostrar_resultados_por_materia",
                            ],
                            True,
                        )
                    ),
                    "question_count": len(
                        questions
                    ),
                    "positions": positions,
                }
            )

        duplicate_codes = [
            code
            for code, count
            in duplicate_exam_codes.items()
            if count > 1
        ]

        unmapped_positions = (
            total_positions
            - mapped_positions
        )

        review_questions = sum(
            1
            for group in candidate_groups
            if group["needs_review"]
        )

        report = {
            "summary": {
                "json_files_found": (
                    len(files)
                ),
                "json_files_valid": (
                    len(parsed)
                ),
                "json_files_invalid": (
                    len(invalid_json)
                ),
                "exam_templates": (
                    len(exam_reports)
                ),
                "exam_question_positions": (
                    total_positions
                ),
                "mapped_positions": (
                    mapped_positions
                ),
                "unmapped_positions": (
                    unmapped_positions
                ),
                "candidate_unique_questions": (
                    len(candidate_groups)
                ),
                "questions_needing_review": (
                    review_questions
                ),
                "subjects_to_create": (
                    len(subjects_to_create)
                ),
                "catalog_errors": (
                    len(catalog_errors)
                ),
                "duplicate_exam_codes": (
                    len(duplicate_codes)
                ),
            },

            "source_kinds": dict(
                source_counts
            ),

            "subjects_to_create": sorted(
                subjects_to_create
            ),

            "catalog_errors": (
                catalog_errors
            ),

            "duplicate_exam_codes": (
                duplicate_codes
            ),

            "invalid_json": invalid_json,

            "exams": exam_reports,
        }

        REPORT_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with REPORT_PATH.open(
            "w",
            encoding="utf-8",
        ) as file_obj:
            json.dump(
                report,
                file_obj,
                ensure_ascii=False,
                indent=2,
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "SIMULACIÓN DE EXÁMENES COMPLETADA"
            )
        )

        self.stdout.write("")
        self.stdout.write(
            "No se escribió ningún dato "
            "en PostgreSQL."
        )

        self.stdout.write("")
        self.stdout.write(
            f"JSON encontrados: "
            f"{len(files)}"
        )

        self.stdout.write(
            f"JSON válidos: "
            f"{len(parsed)}"
        )

        self.stdout.write(
            f"JSON inválidos: "
            f"{len(invalid_json)}"
        )

        self.stdout.write("")
        self.stdout.write(
            f"ExamTemplate candidatos: "
            f"{len(exam_reports)}"
        )

        self.stdout.write(
            "ExamQuestion candidatos: "
            f"{total_positions}"
        )

        self.stdout.write(
            "Posiciones vinculadas a una "
            "pregunta candidata: "
            f"{mapped_positions}"
        )

        self.stdout.write(
            "Posiciones sin vínculo: "
            f"{unmapped_positions}"
        )

        self.stdout.write("")
        self.stdout.write(
            "Question candidatas únicas: "
            f"{len(candidate_groups)}"
        )

        self.stdout.write(
            "Question que requerirían revisión: "
            f"{review_questions}"
        )

        self.stdout.write("")
        self.stdout.write(
            "Materias canónicas que deberán "
            "crearse: "
            f"{len(subjects_to_create)}"
        )

        self.stdout.write(
            "Errores de catálogo académico: "
            f"{len(catalog_errors)}"
        )

        self.stdout.write(
            "Códigos de examen duplicados: "
            f"{len(duplicate_codes)}"
        )

        self.stdout.write("")
        self.stdout.write(
            "Tipos de simulador:"
        )

        for key, value in sorted(
            source_counts.items()
        ):
            self.stdout.write(
                f"  {key}: {value}"
            )

        self.stdout.write("")
        self.stdout.write(
            f"Reporte completo: "
            f"{REPORT_PATH}"
        )

        if (
            invalid_json
            or unmapped_positions
            or catalog_errors
            or duplicate_codes
        ):
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "La estructura todavía "
                    "requiere revisión."
                )
            )

        else:
            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    "La estructura está lista "
                    "para preparar la importación."
                )
            )