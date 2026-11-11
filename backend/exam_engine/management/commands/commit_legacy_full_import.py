import hashlib
import json
import shutil
from collections import defaultdict
from pathlib import Path

from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from django.db import transaction

from exam_engine.models import (
    ExamQuestion,
    ExamTemplate,
)
from question_bank.models import (
    Area,
    Choice,
    EducationLevel,
    Institution,
    Question,
    QuestionContext,
    QuestionVersion,
    Subject,
)

from exam_engine.management.commands.simulate_legacy_exam_import import (
    config_boolean,
    configured_duration,
)
from exam_engine.management.commands.plan_legacy_full_import import (
    LEGACY_ROOT,
    subject_code,
)


PLAN_PATH = Path(
    "/reports/full_import_plan.json"
)

MANIFEST_PATH = Path(
    "/reports/media_staging_manifest.json"
)

MEDIA_ROOT = Path("/media")

FINAL_MEDIA_ROOT = (
    MEDIA_ROOT
    / "questions"
    / "legacy"
)

CONFIRMATION_PHRASE = (
    "IMPORTAR-ELITE-V2"
)


EXPECTED_COUNTS = {
    "subjects": 22,
    "questions": 951,
    "question_versions": 951,
    "choices": 3824,
    "question_contexts": 977,
    "exam_templates": 16,
    "exam_questions": 1152,
    "questions_needing_review": 14,
}


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as file_obj:
        for chunk in iter(
            lambda: file_obj.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path):
    with path.open(
        "r",
        encoding="utf-8",
    ) as file_obj:
        return json.load(file_obj)


class Command(BaseCommand):
    help = (
        "Ejecuta la importación transaccional "
        "del banco V1 hacia PostgreSQL."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--commit",
            action="store_true",
            help=(
                "Autoriza escritura real "
                "en PostgreSQL."
            ),
        )

        parser.add_argument(
            "--confirm",
            type=str,
            default="",
            help=(
                "Debe ser exactamente "
                "IMPORTAR-ELITE-V2."
            ),
        )

    def handle(self, *args, **options):
        # =====================================================
        # 1. Barreras de autorización
        # =====================================================

        if not options["commit"]:
            raise CommandError(
                "Importación bloqueada. "
                "Falta --commit."
            )

        if (
            options["confirm"]
            != CONFIRMATION_PHRASE
        ):
            raise CommandError(
                "Importación bloqueada. "
                "La frase de confirmación "
                "no coincide."
            )

        if not PLAN_PATH.is_file():
            raise CommandError(
                "No existe el plan final."
            )

        if not MANIFEST_PATH.is_file():
            raise CommandError(
                "No existe el manifiesto "
                "de multimedia."
            )

        plan = load_json(
            PLAN_PATH
        )

        manifest = load_json(
            MANIFEST_PATH
        )

        summary = plan.get(
            "summary",
            {},
        )

        expected = plan.get(
            "expected_database_counts",
            {},
        )

        # =====================================================
        # 2. Validar plan
        # =====================================================

        if summary.get(
            "blocking_errors"
        ) != 0:
            raise CommandError(
                "El plan contiene "
                "errores bloqueantes."
            )

        plan_errors = plan.get(
            "blocking_errors",
            [],
        )

        if plan_errors:
            raise CommandError(
                "El plan todavía contiene "
                "errores bloqueantes."
            )

        for key, required_value in (
            EXPECTED_COUNTS.items()
        ):
            actual_value = expected.get(
                key
            )

            if (
                actual_value
                != required_value
            ):
                raise CommandError(
                    "Conteo inesperado en "
                    f"{key}: "
                    f"{actual_value} != "
                    f"{required_value}"
                )

        if (
            summary.get(
                "unique_media_files"
            )
            != 177
        ):
            raise CommandError(
                "El plan no contiene "
                "177 archivos multimedia."
            )

        # =====================================================
        # 3. Validar staging
        # =====================================================

        if manifest.get(
            "blocking_errors"
        ):
            raise CommandError(
                "El staging de multimedia "
                "contiene errores."
            )

        if manifest.get(
            "expected_files"
        ) != 177:
            raise CommandError(
                "El staging no espera "
                "177 archivos."
            )

        if manifest.get(
            "manifest_files"
        ) != 177:
            raise CommandError(
                "El manifiesto no contiene "
                "177 archivos."
            )

        if manifest.get(
            "physical_staged_files"
        ) != 177:
            raise CommandError(
                "El staging físico no "
                "contiene 177 archivos."
            )

        if manifest.get(
            "missing_sources"
        ):
            raise CommandError(
                "Existen fuentes multimedia "
                "faltantes."
            )

        if manifest.get(
            "hash_errors"
        ):
            raise CommandError(
                "Existen errores SHA-256 "
                "en staging."
            )

        # =====================================================
        # 4. La base objetivo debe seguir vacía
        # =====================================================

        database_counts = {
            "subjects": (
                Subject.objects.count()
            ),
            "questions": (
                Question.objects.count()
            ),
            "versions": (
                QuestionVersion.objects.count()
            ),
            "choices": (
                Choice.objects.count()
            ),
            "contexts": (
                QuestionContext.objects.count()
            ),
            "exams": (
                ExamTemplate.objects.count()
            ),
            "exam_questions": (
                ExamQuestion.objects.count()
            ),
        }

        non_empty = {
            key: value
            for key, value
            in database_counts.items()
            if value != 0
        }

        if non_empty:
            raise CommandError(
                "La base objetivo ya contiene "
                "datos de importación: "
                f"{non_empty}"
            )

        # =====================================================
        # 5. Cargar catálogo académico existente
        # =====================================================

        levels = {
            obj.code: obj
            for obj in (
                EducationLevel.objects.all()
            )
        }

        institutions = {
            obj.code: obj
            for obj in (
                Institution.objects.all()
            )
        }

        areas = {
            (
                obj.level.code,
                obj.institution.code,
                obj.code,
            ): obj
            for obj in (
                Area.objects.select_related(
                    "level",
                    "institution",
                )
            )
        }

        # =====================================================
        # 6. Cargar los JSON originales
        # =====================================================

        source_json = {}

        for exam in plan.get(
            "exams",
            [],
        ):
            relative_file = exam[
                "file"
            ]

            path = (
                LEGACY_ROOT
                / relative_file
            )

            if not path.is_file():
                raise CommandError(
                    "No existe el JSON "
                    f"original: {relative_file}"
                )

            with path.open(
                "r",
                encoding="utf-8-sig",
            ) as file_obj:
                source_json[
                    relative_file
                ] = json.load(
                    file_obj
                )

        # =====================================================
        # 7. Validar multimedia staged y preparar rutas finales
        # =====================================================

        resource_final_paths = {}

        new_files = []

        FINAL_MEDIA_ROOT.mkdir(
            parents=True,
            exist_ok=True,
        )

        for resource in manifest[
            "files"
        ]:
            sha256 = resource[
                "sha256"
            ]

            suffix = (
                resource.get(
                    "suffix"
                )
                or ""
            )

            staged_relative = resource[
                "staged_file"
            ]

            staged_path = (
                MEDIA_ROOT
                / staged_relative
            )

            if not staged_path.is_file():
                raise CommandError(
                    "Falta archivo staged: "
                    f"{staged_relative}"
                )

            actual_sha256 = sha256_file(
                staged_path
            )

            if actual_sha256 != sha256:
                raise CommandError(
                    "SHA-256 inválido en "
                    f"{staged_relative}"
                )

            filename = (
                f"{sha256}{suffix}"
            )

            final_path = (
                FINAL_MEDIA_ROOT
                / filename
            )

            final_relative = (
                f"questions/legacy/"
                f"{filename}"
            )

            if final_path.exists():
                existing_sha = (
                    sha256_file(
                        final_path
                    )
                )

                if existing_sha != sha256:
                    raise CommandError(
                        "Existe un archivo final "
                        "con hash incorrecto: "
                        f"{final_path}"
                    )

            else:
                shutil.copy2(
                    staged_path,
                    final_path,
                )

                new_files.append(
                    final_path
                )

            resource_final_paths[
                sha256
            ] = final_relative

        # =====================================================
        # 8. Preparar recursos pendientes para review_notes
        # =====================================================

        unresolved_by_candidate = (
            defaultdict(list)
        )

        for resource in plan.get(
            "unresolved_resources",
            [],
        ):
            unresolved_by_candidate[
                resource["candidate"]
            ].append(
                resource
            )

        question_by_candidate = {}

        subject_by_name = {}

        exam_by_code = {}

        try:
            # =================================================
            # 9. TRANSACCIÓN DE POSTGRESQL
            # =================================================

            with transaction.atomic():
                # ---------------------------------------------
                # SUBJECT
                # ---------------------------------------------

                for subject_data in plan[
                    "subjects"
                ]:
                    obj = Subject.objects.create(
                        code=subject_data[
                            "code"
                        ],
                        name=subject_data[
                            "name"
                        ],
                        is_active=True,
                    )

                    subject_by_name[
                        obj.name
                    ] = obj

                if (
                    Subject.objects.count()
                    != EXPECTED_COUNTS[
                        "subjects"
                    ]
                ):
                    raise RuntimeError(
                        "Conteo Subject "
                        "incorrecto."
                    )

                # ---------------------------------------------
                # QUESTION + VERSION + CHOICE
                # ---------------------------------------------

                for candidate in plan[
                    "candidates"
                ]:
                    candidate_key = candidate[
                        "key"
                    ]

                    representative = candidate[
                        "representative"
                    ]

                    relative_file = (
                        representative[
                            "file"
                        ]
                    )

                    position = (
                        representative[
                            "position"
                        ]
                    )

                    data = source_json[
                        relative_file
                    ]

                    questions = data[
                        "preguntas"
                    ]

                    if (
                        position < 1
                        or position
                        > len(questions)
                    ):
                        raise RuntimeError(
                            "Posición inválida "
                            "para candidato "
                            f"{candidate_key}"
                        )

                    legacy_question = (
                        questions[
                            position - 1
                        ]
                    )

                    question_data = (
                        legacy_question.get(
                            "pregunta"
                        )
                        or {}
                    )

                    options_list = (
                        legacy_question.get(
                            "opciones"
                        )
                        or []
                    )

                    correct_answer = str(
                        legacy_question.get(
                            "respuesta_correcta",
                            "",
                        )
                    )

                    question = (
                        Question.objects.create(
                            status=(
                                Question.Status.PUBLISHED
                            )
                        )
                    )

                    question_by_candidate[
                        candidate_key
                    ] = question

                    # -----------------------------------------
                    # Imagen de pregunta
                    # -----------------------------------------

                    question_image_path = None

                    question_image = (
                        candidate.get(
                            "question_image"
                        )
                    )

                    if (
                        question_image
                        and question_image.get(
                            "exists"
                        )
                        and question_image.get(
                            "sha256"
                        )
                    ):
                        question_image_path = (
                            resource_final_paths[
                                question_image[
                                    "sha256"
                                ]
                            ]
                        )

                    # -----------------------------------------
                    # Tipo TEXT / MIXED
                    # -----------------------------------------

                    has_visual_reference = bool(
                        question_data.get(
                            "imagen"
                        )
                    )

                    if not has_visual_reference:
                        has_visual_reference = any(
                            bool(
                                option.get(
                                    "imagen"
                                )
                            )
                            for option in (
                                options_list
                            )
                        )

                    question_type = (
                        QuestionVersion
                        .QuestionType
                        .MIXED
                        if has_visual_reference
                        else QuestionVersion
                        .QuestionType
                        .TEXT
                    )

                    unresolved = (
                        unresolved_by_candidate.get(
                            candidate_key,
                            [],
                        )
                    )

                    review_notes = ""

                    if unresolved:
                        missing_paths = [
                            str(
                                item.get(
                                    "path",
                                    "",
                                )
                            )
                            for item in unresolved
                        ]

                        review_notes = (
                            "Importada desde V1. "
                            "Recursos heredados "
                            "no resueltos: "
                            + "; ".join(
                                missing_paths
                            )
                        )

                    explanation = (
                        legacy_question.get(
                            "explicacion"
                        )
                        or question_data.get(
                            "explicacion"
                        )
                        or ""
                    )

                    observations = (
                        legacy_question.get(
                            "observaciones"
                        )
                        or question_data.get(
                            "observaciones"
                        )
                        or ""
                    )

                    version = (
                        QuestionVersion.objects.create(
                            question=question,
                            version=1,
                            question_type=(
                                question_type
                            ),
                            content=(
                                question_data.get(
                                    "contenido"
                                )
                                or ""
                            ),
                            image=(
                                question_image_path
                            ),
                            explanation=(
                                explanation
                            ),
                            observations=(
                                observations
                            ),
                            needs_review=(
                                candidate[
                                    "needs_review"
                                ]
                            ),
                            review_notes=(
                                review_notes
                            ),
                        )
                    )

                    # -----------------------------------------
                    # CHOICES
                    # -----------------------------------------

                    candidate_choices = (
                        candidate.get(
                            "choices",
                            [],
                        )
                    )

                    if (
                        len(candidate_choices)
                        != len(options_list)
                    ):
                        raise RuntimeError(
                            "Número de opciones "
                            "inconsistente en "
                            f"{candidate_key}"
                        )

                    correct_count = 0

                    for index, option in enumerate(
                        options_list,
                        start=1,
                    ):
                        label = str(
                            option.get(
                                "inciso",
                                "",
                            )
                        )

                        is_correct = (
                            label
                            == correct_answer
                        )

                        if is_correct:
                            correct_count += 1

                        image_path = None

                        planned_choice = (
                            candidate_choices[
                                index - 1
                            ]
                        )

                        planned_image = (
                            planned_choice.get(
                                "image"
                            )
                        )

                        if (
                            planned_image
                            and planned_image.get(
                                "exists"
                            )
                            and planned_image.get(
                                "sha256"
                            )
                        ):
                            image_path = (
                                resource_final_paths[
                                    planned_image[
                                        "sha256"
                                    ]
                                ]
                            )

                        Choice.objects.create(
                            question_version=(
                                version
                            ),
                            label=label,
                            text=(
                                option.get(
                                    "texto"
                                )
                                or ""
                            ),
                            image=image_path,
                            position=index,
                            is_correct=(
                                is_correct
                            ),
                        )

                    if correct_count != 1:
                        raise RuntimeError(
                            "La pregunta "
                            f"{candidate_key} "
                            "no tiene exactamente "
                            "una respuesta correcta."
                        )

                # ---------------------------------------------
                # QUESTION CONTEXT
                # ---------------------------------------------

                context_keys = set()

                for exam_plan in plan[
                    "exams"
                ]:
                    level_code = (
                        exam_plan["level"]
                    )

                    institution_code = (
                        exam_plan[
                            "institution"
                        ]
                    )

                    area_code = (
                        exam_plan.get(
                            "area"
                        )
                    )

                    level = levels.get(
                        level_code
                    )

                    institution = (
                        institutions.get(
                            institution_code
                        )
                    )

                    if not level:
                        raise RuntimeError(
                            "Nivel inexistente: "
                            f"{level_code}"
                        )

                    if not institution:
                        raise RuntimeError(
                            "Institución "
                            "inexistente: "
                            f"{institution_code}"
                        )

                    area = None

                    if area_code:
                        area = areas.get(
                            (
                                level_code,
                                institution_code,
                                area_code,
                            )
                        )

                        if not area:
                            raise RuntimeError(
                                "Área inexistente: "
                                f"{area_code}"
                            )

                    for position_data in (
                        exam_plan[
                            "positions"
                        ]
                    ):
                        candidate_key = (
                            position_data[
                                "candidate"
                            ]
                        )

                        subject_name = (
                            position_data[
                                "subject"
                            ]
                        )

                        context_key = (
                            candidate_key,
                            level_code,
                            institution_code,
                            area_code,
                            subject_name,
                        )

                        if (
                            context_key
                            in context_keys
                        ):
                            continue

                        context_keys.add(
                            context_key
                        )

                        subject = (
                            subject_by_name.get(
                                subject_name
                            )
                        )

                        if not subject:
                            raise RuntimeError(
                                "Materia inexistente: "
                                f"{subject_name}"
                            )

                        QuestionContext.objects.create(
                            question=(
                                question_by_candidate[
                                    candidate_key
                                ]
                            ),
                            level=level,
                            institution=(
                                institution
                            ),
                            area=area,
                            subject=subject,
                            unit=None,
                        )

                # ---------------------------------------------
                # EXAM TEMPLATE + EXAM QUESTION
                # ---------------------------------------------

                for exam_plan in plan[
                    "exams"
                ]:
                    level_code = (
                        exam_plan["level"]
                    )

                    institution_code = (
                        exam_plan[
                            "institution"
                        ]
                    )

                    area_code = (
                        exam_plan.get(
                            "area"
                        )
                    )

                    level = levels[
                        level_code
                    ]

                    institution = (
                        institutions[
                            institution_code
                        ]
                    )

                    area = None

                    if area_code:
                        area = areas[
                            (
                                level_code,
                                institution_code,
                                area_code,
                            )
                        ]

                    # -----------------------------------------
                    # JSON original para configuración
                    # -----------------------------------------

                    legacy_data = source_json[
                        exam_plan["file"]
                    ]

                    configuration = (
                        legacy_data.get(
                            "configuracion"
                        )
                        or {}
                    )

                    template_subject = None

                    if (
                        exam_plan[
                            "source_kind"
                        ]
                        == "SUBJECT"
                    ):
                        exam_subjects = {
                            item["subject"]
                            for item in (
                                exam_plan[
                                    "positions"
                                ]
                            )
                            if item.get(
                                "subject"
                            )
                        }

                        if len(
                            exam_subjects
                        ) == 1:
                            template_subject = (
                                subject_by_name[
                                    next(
                                        iter(
                                            exam_subjects
                                        )
                                    )
                                ]
                            )

                    exam = (
                        ExamTemplate.objects.create(
                            code=(
                                exam_plan[
                                    "code"
                                ]
                            ),
                            name=(
                                exam_plan[
                                    "name"
                                ]
                            ),
                            level=level,
                            institution=(
                                institution
                            ),
                            area=area,
                            subject=(
                                template_subject
                            ),
                            source_kind=(
                                exam_plan[
                                    "source_kind"
                                ]
                            ),
                            mode=(
                                ExamTemplate
                                .Mode
                                .FIXED
                            ),
                            legacy_source_file=(
                                exam_plan[
                                    "file"
                                ]
                            ),
                            legacy_version=(
                                exam_plan[
                                    "version"
                                ]
                            ),
                            legacy_configuration=(
                                configuration
                            ),
                            duration_minutes=(
                                configured_duration(
                                    configuration
                                )
                            ),
                            timer_allowed=(
                                config_boolean(
                                    configuration,
                                    [
                                        "contador_permitido"
                                    ],
                                    True,
                                )
                            ),
                            timer_active_by_default=(
                                config_boolean(
                                    configuration,
                                    [
                                        "contador_activo_por_defecto"
                                    ],
                                    False,
                                )
                            ),
                            auto_close=(
                                config_boolean(
                                    configuration,
                                    [
                                        "cerrar_automaticamente"
                                    ],
                                    False,
                                )
                            ),
                            allow_review=(
                                config_boolean(
                                    configuration,
                                    [
                                        "permitir_revision"
                                    ],
                                    True,
                                )
                            ),
                            show_results_by_subject=(
                                config_boolean(
                                    configuration,
                                    [
                                        "mostrar_resultados_por_materia"
                                    ],
                                    True,
                                )
                            ),
                            is_active=True,
                        )
                    )

                    exam_by_code[
                        exam.code
                    ] = exam

                    for position_data in (
                        exam_plan[
                            "positions"
                        ]
                    ):
                        candidate_key = (
                            position_data[
                                "candidate"
                            ]
                        )

                        ExamQuestion.objects.create(
                            exam=exam,
                            question=(
                                question_by_candidate[
                                    candidate_key
                                ]
                            ),
                            position=(
                                position_data[
                                    "position"
                                ]
                            ),
                            legacy_question_id=(
                                str(
                                    position_data.get(
                                        "legacy_question_id",
                                        "",
                                    )
                                    or ""
                                )
                            ),
                            legacy_subject_name=(
                                position_data.get(
                                    "subject"
                                )
                                or ""
                            ),
                        )

                # ---------------------------------------------
                # 10. VALIDACIONES FINALES
                # ---------------------------------------------

                final_counts = {
                    "subjects": (
                        Subject.objects.count()
                    ),
                    "questions": (
                        Question.objects.count()
                    ),
                    "question_versions": (
                        QuestionVersion.objects.count()
                    ),
                    "choices": (
                        Choice.objects.count()
                    ),
                    "question_contexts": (
                        QuestionContext.objects.count()
                    ),
                    "exam_templates": (
                        ExamTemplate.objects.count()
                    ),
                    "exam_questions": (
                        ExamQuestion.objects.count()
                    ),
                    "questions_needing_review": (
                        QuestionVersion.objects.filter(
                            needs_review=True
                        ).count()
                    ),
                }

                for key, expected_value in (
                    EXPECTED_COUNTS.items()
                ):
                    actual_value = (
                        final_counts[key]
                    )

                    if (
                        actual_value
                        != expected_value
                    ):
                        raise RuntimeError(
                            "Validación final "
                            f"fallida para {key}: "
                            f"{actual_value} != "
                            f"{expected_value}"
                        )

                correct_choices = (
                    Choice.objects.filter(
                        is_correct=True
                    ).count()
                )

                if (
                    correct_choices
                    != EXPECTED_COUNTS[
                        "questions"
                    ]
                ):
                    raise RuntimeError(
                        "El número de respuestas "
                        "correctas no es 951: "
                        f"{correct_choices}"
                    )

                if len(
                    question_by_candidate
                ) != 951:
                    raise RuntimeError(
                        "El mapa interno de "
                        "preguntas no contiene "
                        "951 elementos."
                    )

            # =================================================
            # La transacción llegó a COMMIT
            # =================================================

        except Exception:
            # PostgreSQL hace rollback automáticamente.
            # Retiramos únicamente archivos finales
            # creados por esta ejecución.

            for path in reversed(
                new_files
            ):
                try:
                    if path.exists():
                        path.unlink()
                except OSError:
                    pass

            raise

        # =====================================================
        # 11. ÉXITO
        # =====================================================

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "IMPORTACIÓN V1 → V2 "
                "COMPLETADA CORRECTAMENTE"
            )
        )

        self.stdout.write("")
        self.stdout.write(
            "PostgreSQL confirmó la "
            "transacción."
        )

        self.stdout.write("")
        self.stdout.write(
            "Subject: 22"
        )

        self.stdout.write(
            "Question: 951"
        )

        self.stdout.write(
            "QuestionVersion: 951"
        )

        self.stdout.write(
            "Choice: 3824"
        )

        self.stdout.write(
            "QuestionContext: 977"
        )

        self.stdout.write(
            "ExamTemplate: 16"
        )

        self.stdout.write(
            "ExamQuestion: 1152"
        )

        self.stdout.write(
            "QuestionVersion "
            "needs_review=True: 14"
        )

        self.stdout.write(
            "Choice correctas: 951"
        )

        self.stdout.write(
            "Multimedia final verificada: "
            "177 archivos"
        )