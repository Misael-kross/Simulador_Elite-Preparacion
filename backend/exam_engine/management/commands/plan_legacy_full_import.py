import json
from collections import Counter, defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand

from exam_engine.models import (
    ExamQuestion,
    ExamTemplate,
)
from question_bank.models import (
    Choice,
    Question,
    QuestionContext,
    QuestionVersion,
    Subject,
)

from exam_engine.management.commands.simulate_legacy_exam_import import (
    LEGACY_ROOT,
    JSON_ROOTS,
    build_exam_code,
    canonical_institution,
    canonical_level,
    infer_area_code,
    source_kind,
)

from question_bank.management.commands.import_legacy_questions import (
    canonical_subject,
    content_fingerprint,
    file_info,
    visual_resource_profile,
)


REPORT_PATH = Path(
    "/reports/full_import_plan.json"
)


def subject_code(name):
    value = (
        name.upper()
        .replace("Á", "A")
        .replace("É", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ú", "U")
        .replace("Ü", "U")
        .replace("Ñ", "N")
    )

    result = []

    previous_underscore = False

    for char in value:
        if char.isalnum():
            result.append(char)
            previous_underscore = False

        elif not previous_underscore:
            result.append("_")
            previous_underscore = True

    return "".join(result).strip("_")


def select_representative(occurrences):
    """
    Prefiere una aparición cuyos recursos
    visuales estén completos.

    Si ninguna está completa, conserva la
    primera y la pregunta quedará marcada
    para revisión.
    """

    for occurrence in occurrences:
        if occurrence["visual_complete"]:
            return occurrence

    return occurrences[0]


def register_resource(
    inventory,
    category,
    relative_path,
):
    if not relative_path:
        return None

    info = file_info(relative_path)

    if not info["exists"]:
        return {
            "exists": False,
            "path": relative_path,
            "sha256": None,
        }

    sha256 = info["sha256"]

    path = LEGACY_ROOT / relative_path
    suffix = path.suffix.lower()

    if sha256 not in inventory:
        inventory[sha256] = {
            "sha256": sha256,
            "suffix": suffix,
            "categories": set(),
            "source_paths": set(),
        }

    inventory[sha256][
        "categories"
    ].add(category)

    inventory[sha256][
        "source_paths"
    ].add(relative_path)

    return {
        "exists": True,
        "path": relative_path,
        "sha256": sha256,
    }


class Command(BaseCommand):
    help = (
        "Genera el plan final exacto de "
        "migración del banco V1 sin escribir "
        "en PostgreSQL ni copiar imágenes."
    )

    def handle(self, *args, **options):
        files = []

        for root in JSON_ROOTS:
            if root.exists():
                files.extend(
                    sorted(root.rglob("*.json"))
                )

        if not files:
            self.stderr.write(
                self.style.ERROR(
                    "No se encontraron JSON heredados."
                )
            )
            return

        parsed_exams = []
        exam_by_file = {}

        content_groups = defaultdict(list)

        invalid_json = []

        total_records = 0

        # =====================================================
        # 1. Leer los 16 JSON
        # =====================================================

        for path in files:
            relative_path = path.relative_to(
                LEGACY_ROOT
            )

            relative_file = str(
                relative_path
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
                        "file": relative_file,
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
                        "file": relative_file,
                        "error": (
                            "preguntas no es una lista"
                        ),
                    }
                )
                continue

            level_code = canonical_level(
                data.get("nivel")
            )

            institution_code = (
                canonical_institution(
                    data.get("institucion"),
                    relative_path,
                )
            )

            area_code = infer_area_code(
                relative_path,
                institution_code,
            )

            exam = {
                "file": relative_file,
                "code": build_exam_code(
                    relative_path
                ),
                "name": (
                    data.get("nombre")
                    or relative_path.stem
                ),
                "level": level_code,
                "institution": (
                    institution_code
                ),
                "area": area_code,
                "source_kind": source_kind(
                    relative_path
                ),
                "version": str(
                    data.get(
                        "version",
                        "",
                    )
                ),
                "configuration": (
                    data.get(
                        "configuracion"
                    )
                    or {}
                ),
                "questions": questions,
            }

            parsed_exams.append(exam)

            exam_by_file[
                relative_file
            ] = exam

            for position, question in enumerate(
                questions,
                start=1,
            ):
                total_records += 1

                fingerprint = (
                    content_fingerprint(
                        question
                    )
                )

                visual_profile = (
                    visual_resource_profile(
                        question
                    )
                )

                occurrence = {
                    "file": relative_file,
                    "position": position,
                    "legacy_question_id": (
                        question.get("id")
                    ),
                    "raw_subject": (
                        question.get("materia")
                    ),
                    "subject": (
                        canonical_subject(
                            question.get(
                                "materia"
                            )
                        )
                    ),
                    "question": question,
                    "visual_signature": (
                        visual_profile[
                            "signature"
                        ]
                    ),
                    "visual_complete": (
                        visual_profile[
                            "complete"
                        ]
                    ),
                }

                content_groups[
                    fingerprint
                ].append(
                    occurrence
                )

        # =====================================================
        # 2. Refinar preguntas únicas usando identidad visual
        # =====================================================

        candidate_groups = []
        occurrence_mapping = {}

        for fingerprint, occurrences in (
            content_groups.items()
        ):
            complete_visual_groups = (
                defaultdict(list)
            )

            incomplete_occurrences = []

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

                    complete_visual_groups[
                        visual_key
                    ].append(
                        occurrence
                    )

                else:
                    incomplete_occurrences.append(
                        occurrence
                    )

            # ---------------------------------------------
            # Un único perfil visual válido,
            # o ninguno.
            # ---------------------------------------------

            if len(
                complete_visual_groups
            ) <= 1:
                candidate_key = fingerprint

                group = {
                    "key": candidate_key,
                    "occurrences": occurrences,
                    "needs_review": (
                        bool(
                            incomplete_occurrences
                        )
                        and not (
                            complete_visual_groups
                        )
                    ),
                }

                candidate_groups.append(
                    group
                )

                for occurrence in occurrences:
                    occurrence_mapping[
                        (
                            occurrence["file"],
                            occurrence["position"],
                        )
                    ] = candidate_key

                continue

            # ---------------------------------------------
            # Mismo texto pero perfiles visuales
            # diferentes: preguntas distintas.
            # ---------------------------------------------

            for index, visual_occurrences in (
                enumerate(
                    complete_visual_groups.values(),
                    start=1,
                )
            ):
                candidate_key = (
                    f"{fingerprint}:"
                    f"visual:{index}"
                )

                group = {
                    "key": candidate_key,
                    "occurrences": (
                        visual_occurrences
                    ),
                    "needs_review": False,
                }

                candidate_groups.append(
                    group
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

            if incomplete_occurrences:
                candidate_key = (
                    f"{fingerprint}:"
                    "unresolved-visual"
                )

                group = {
                    "key": candidate_key,
                    "occurrences": (
                        incomplete_occurrences
                    ),
                    "needs_review": True,
                }

                candidate_groups.append(
                    group
                )

                for occurrence in (
                    incomplete_occurrences
                ):
                    occurrence_mapping[
                        (
                            occurrence["file"],
                            occurrence["position"],
                        )
                    ] = candidate_key

        # =====================================================
        # 3. Elegir representante de cada Question
        # =====================================================

        candidate_by_key = {}

        resource_inventory = {}

        unresolved_resources = []

        recovered_question_images = 0
        recovered_option_images = 0

        exact_choice_count = 0

        subjects = set()

        candidate_reports = []

        answer_errors = []

        for group in candidate_groups:
            key = group["key"]

            occurrences = group[
                "occurrences"
            ]

            representative = (
                select_representative(
                    occurrences
                )
            )

            question = representative[
                "question"
            ]

            question_data = (
                question.get("pregunta")
                or {}
            )

            options_list = (
                question.get("opciones")
                or []
            )

            exact_choice_count += len(
                options_list
            )

            subject = representative[
                "subject"
            ]

            if subject:
                subjects.add(subject)

            correct_answer = str(
                question.get(
                    "respuesta_correcta",
                    "",
                )
            )

            option_labels = [
                str(
                    option.get(
                        "inciso",
                        "",
                    )
                )
                for option in options_list
            ]

            if (
                not correct_answer
                or correct_answer
                not in option_labels
            ):
                answer_errors.append(
                    {
                        "candidate": key,
                        "file": representative[
                            "file"
                        ],
                        "position": (
                            representative[
                                "position"
                            ]
                        ),
                        "correct_answer": (
                            correct_answer
                        ),
                        "labels": (
                            option_labels
                        ),
                    }
                )

            question_image = (
                question_data.get(
                    "imagen"
                )
            )

            question_resource = (
                register_resource(
                    resource_inventory,
                    "question",
                    question_image,
                )
            )

            if (
                question_image
                and question_resource
                and not question_resource[
                    "exists"
                ]
            ):
                unresolved_resources.append(
                    {
                        "candidate": key,
                        "type": (
                            "question_image"
                        ),
                        "file": (
                            representative[
                                "file"
                            ]
                        ),
                        "position": (
                            representative[
                                "position"
                            ]
                        ),
                        "path": question_image,
                    }
                )

            option_reports = []

            for option in options_list:
                option_image = option.get(
                    "imagen"
                )

                option_resource = (
                    register_resource(
                        resource_inventory,
                        "choice",
                        option_image,
                    )
                )

                if (
                    option_image
                    and option_resource
                    and not option_resource[
                        "exists"
                    ]
                ):
                    unresolved_resources.append(
                        {
                            "candidate": key,
                            "type": (
                                "choice_image"
                            ),
                            "file": (
                                representative[
                                    "file"
                                ]
                            ),
                            "position": (
                                representative[
                                    "position"
                                ]
                            ),
                            "label": (
                                option.get(
                                    "inciso"
                                )
                            ),
                            "path": (
                                option_image
                            ),
                        }
                    )

                option_reports.append(
                    {
                        "label": (
                            option.get(
                                "inciso"
                            )
                        ),
                        "has_text": bool(
                            option.get(
                                "texto"
                            )
                        ),
                        "image": (
                            option_resource
                        ),
                        "is_correct": (
                            str(
                                option.get(
                                    "inciso",
                                    "",
                                )
                            )
                            == correct_answer
                        ),
                    }
                )

            # ---------------------------------------------
            # Contar recursos recuperados gracias
            # a otra aparición del mismo candidato.
            # ---------------------------------------------

            representative_question_image = (
                question_data.get(
                    "imagen"
                )
            )

            representative_question_info = (
                file_info(
                    representative_question_image
                )
            )

            for occurrence in occurrences:
                original_question = (
                    occurrence[
                        "question"
                    ]
                )

                original_question_data = (
                    original_question.get(
                        "pregunta"
                    )
                    or {}
                )

                original_image = (
                    original_question_data.get(
                        "imagen"
                    )
                )

                if original_image:
                    original_info = file_info(
                        original_image
                    )

                    if (
                        not original_info[
                            "exists"
                        ]
                        and representative_question_info[
                            "exists"
                        ]
                    ):
                        recovered_question_images += 1

                original_options = (
                    original_question.get(
                        "opciones"
                    )
                    or []
                )

                for original_option in (
                    original_options
                ):
                    original_option_image = (
                        original_option.get(
                            "imagen"
                        )
                    )

                    if not original_option_image:
                        continue

                    original_option_info = (
                        file_info(
                            original_option_image
                        )
                    )

                    if (
                        original_option_info[
                            "exists"
                        ]
                    ):
                        continue

                    label = str(
                        original_option.get(
                            "inciso",
                            "",
                        )
                    )

                    matching_option = next(
                        (
                            option
                            for option in options_list
                            if str(
                                option.get(
                                    "inciso",
                                    "",
                                )
                            )
                            == label
                        ),
                        None,
                    )

                    if not matching_option:
                        continue

                    replacement_image = (
                        matching_option.get(
                            "imagen"
                        )
                    )

                    replacement_info = (
                        file_info(
                            replacement_image
                        )
                    )

                    if replacement_info[
                        "exists"
                    ]:
                        recovered_option_images += 1

            candidate_report = {
                "key": key,
                "needs_review": (
                    group[
                        "needs_review"
                    ]
                ),
                "representative": {
                    "file": representative[
                        "file"
                    ],
                    "position": (
                        representative[
                            "position"
                        ]
                    ),
                    "legacy_question_id": (
                        representative[
                            "legacy_question_id"
                        ]
                    ),
                },
                "subject": subject,
                "choice_count": len(
                    options_list
                ),
                "question_image": (
                    question_resource
                ),
                "choices": option_reports,
                "occurrence_count": len(
                    occurrences
                ),
            }

            candidate_by_key[key] = {
                "group": group,
                "representative": (
                    representative
                ),
            }

            candidate_reports.append(
                candidate_report
            )

        # =====================================================
        # 4. Construir QuestionContext únicos
        # =====================================================

        context_keys = set()
        context_errors = []

        for candidate_key, candidate in (
            candidate_by_key.items()
        ):
            group = candidate["group"]

            for occurrence in group[
                "occurrences"
            ]:
                exam = exam_by_file.get(
                    occurrence["file"]
                )

                if not exam:
                    context_errors.append(
                        {
                            "candidate": (
                                candidate_key
                            ),
                            "file": (
                                occurrence[
                                    "file"
                                ]
                            ),
                            "error": (
                                "No se encontró "
                                "el examen de origen."
                            ),
                        }
                    )
                    continue

                subject = occurrence[
                    "subject"
                ]

                context_key = (
                    candidate_key,
                    exam["level"],
                    exam["institution"],
                    exam["area"],
                    subject,
                    None,
                )

                context_keys.add(
                    context_key
                )

        # =====================================================
        # 5. Validar los 16 ExamTemplate y
        #    sus 1152 ExamQuestion
        # =====================================================

        exam_question_count = 0
        unmapped_exam_questions = []

        duplicate_exam_codes = Counter()

        exam_reports = []

        for exam in parsed_exams:
            duplicate_exam_codes[
                exam["code"]
            ] += 1

            positions = []

            for position, question in enumerate(
                exam["questions"],
                start=1,
            ):
                exam_question_count += 1

                candidate_key = (
                    occurrence_mapping.get(
                        (
                            exam["file"],
                            position,
                        )
                    )
                )

                if not candidate_key:
                    unmapped_exam_questions.append(
                        {
                            "file": exam[
                                "file"
                            ],
                            "position": (
                                position
                            ),
                            "legacy_question_id": (
                                question.get(
                                    "id"
                                )
                            ),
                        }
                    )

                positions.append(
                    {
                        "position": position,
                        "legacy_question_id": (
                            question.get(
                                "id"
                            )
                        ),
                        "subject": (
                            canonical_subject(
                                question.get(
                                    "materia"
                                )
                            )
                        ),
                        "candidate": (
                            candidate_key
                        ),
                    }
                )

            exam_reports.append(
                {
                    "code": exam["code"],
                    "name": exam["name"],
                    "file": exam["file"],
                    "level": exam[
                        "level"
                    ],
                    "institution": exam[
                        "institution"
                    ],
                    "area": exam[
                        "area"
                    ],
                    "source_kind": exam[
                        "source_kind"
                    ],
                    "version": exam[
                        "version"
                    ],
                    "question_count": len(
                        exam["questions"]
                    ),
                    "positions": positions,
                }
            )

        duplicate_exam_code_list = [
            code
            for code, count
            in duplicate_exam_codes.items()
            if count > 1
        ]

        # =====================================================
        # 6. Preparar inventario de recursos
        # =====================================================

        resource_report = []

        question_resource_count = 0
        choice_resource_count = 0

        for resource in (
            resource_inventory.values()
        ):
            categories = sorted(
                resource[
                    "categories"
                ]
            )

            if "question" in categories:
                question_resource_count += 1

            if "choice" in categories:
                choice_resource_count += 1

            resource_report.append(
                {
                    "sha256": resource[
                        "sha256"
                    ],
                    "suffix": resource[
                        "suffix"
                    ],
                    "categories": categories,
                    "source_paths": sorted(
                        resource[
                            "source_paths"
                        ]
                    ),
                }
            )

        # =====================================================
        # 7. Estado actual de PostgreSQL
        # =====================================================

        database_state = {
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
            "exam_templates": (
                ExamTemplate.objects.count()
            ),
            "exam_questions": (
                ExamQuestion.objects.count()
            ),
        }

        # =====================================================
        # 8. Resumen y condiciones de seguridad
        # =====================================================

        questions_needing_review = sum(
            1
            for group in candidate_groups
            if group["needs_review"]
        )

        expected_counts = {
            "subjects": len(subjects),
            "questions": len(
                candidate_groups
            ),
            "question_versions": len(
                candidate_groups
            ),
            "choices": (
                exact_choice_count
            ),
            "question_contexts": len(
                context_keys
            ),
            "exam_templates": len(
                parsed_exams
            ),
            "exam_questions": (
                exam_question_count
            ),
            "questions_needing_review": (
                questions_needing_review
            ),
        }

        blocking_errors = []

        if invalid_json:
            blocking_errors.append(
                "Existen JSON inválidos."
            )

        if unmapped_exam_questions:
            blocking_errors.append(
                "Existen posiciones de examen "
                "sin Question candidata."
            )

        if duplicate_exam_code_list:
            blocking_errors.append(
                "Existen códigos de examen "
                "duplicados."
            )

        if answer_errors:
            blocking_errors.append(
                "Existen respuestas correctas "
                "que no coinciden con opciones."
            )

        if context_errors:
            blocking_errors.append(
                "Existen errores al construir "
                "QuestionContext."
            )

        if len(parsed_exams) != 16:
            blocking_errors.append(
                "El número de ExamTemplate "
                "no es 16."
            )

        if exam_question_count != 1152:
            blocking_errors.append(
                "El número de ExamQuestion "
                "no es 1152."
            )

        if len(candidate_groups) != 951:
            blocking_errors.append(
                "El número de Question "
                "candidatas no es 951."
            )

        if questions_needing_review != 14:
            blocking_errors.append(
                "El número de preguntas "
                "en revisión no es 14."
            )

        if (
            database_state["questions"] != 0
            or database_state["versions"] != 0
            or database_state["choices"] != 0
            or database_state[
                "exam_templates"
            ] != 0
            or database_state[
                "exam_questions"
            ] != 0
        ):
            blocking_errors.append(
                "La base no está vacía en las "
                "tablas que deben importarse."
            )

        # =====================================================
        # 9. Guardar plan
        # =====================================================

        report = {
            "summary": {
                "json_files": len(
                    parsed_exams
                ),
                "legacy_question_records": (
                    total_records
                ),
                "unique_questions": len(
                    candidate_groups
                ),
                "duplicate_occurrences": (
                    total_records
                    - len(
                        candidate_groups
                    )
                ),
                "subjects": len(
                    subjects
                ),
                "choices": (
                    exact_choice_count
                ),
                "question_contexts": len(
                    context_keys
                ),
                "exam_templates": len(
                    parsed_exams
                ),
                "exam_questions": (
                    exam_question_count
                ),
                "questions_needing_review": (
                    questions_needing_review
                ),
                "unresolved_resources": len(
                    unresolved_resources
                ),
                "recovered_question_images": (
                    recovered_question_images
                ),
                "recovered_option_images": (
                    recovered_option_images
                ),
                "unique_media_files": len(
                    resource_inventory
                ),
                "unique_question_media_files": (
                    question_resource_count
                ),
                "unique_choice_media_files": (
                    choice_resource_count
                ),
                "blocking_errors": len(
                    blocking_errors
                ),
            },

            "expected_database_counts": (
                expected_counts
            ),

            "database_before_import": (
                database_state
            ),

            "subjects": [
                {
                    "code": (
                        subject_code(name)
                    ),
                    "name": name,
                }
                for name in sorted(
                    subjects
                )
            ],

            "blocking_errors": (
                blocking_errors
            ),

            "invalid_json": (
                invalid_json
            ),

            "answer_errors": (
                answer_errors
            ),

            "context_errors": (
                context_errors
            ),

            "unmapped_exam_questions": (
                unmapped_exam_questions
            ),

            "duplicate_exam_codes": (
                duplicate_exam_code_list
            ),

            "unresolved_resources": (
                unresolved_resources
            ),

            "resources": (
                resource_report
            ),

            "candidates": (
                candidate_reports
            ),

            "exams": (
                exam_reports
            ),
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

        # =====================================================
        # 10. Salida
        # =====================================================

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "PLAN FINAL DE IMPORTACIÓN GENERADO"
            )
        )

        self.stdout.write("")
        self.stdout.write(
            "No se escribió ningún dato "
            "en PostgreSQL."
        )

        self.stdout.write(
            "No se copió ninguna imagen."
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "CONTENIDO"
            )
        )

        self.stdout.write(
            f"JSON: {len(parsed_exams)}"
        )

        self.stdout.write(
            "Registros heredados: "
            f"{total_records}"
        )

        self.stdout.write(
            "Question únicas: "
            f"{len(candidate_groups)}"
        )

        self.stdout.write(
            "Reutilizaciones: "
            f"{total_records - len(candidate_groups)}"
        )

        self.stdout.write(
            f"Subject: {len(subjects)}"
        )

        self.stdout.write(
            f"Choice exactas: "
            f"{exact_choice_count}"
        )

        self.stdout.write(
            "QuestionContext exactos: "
            f"{len(context_keys)}"
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "EXÁMENES"
            )
        )

        self.stdout.write(
            "ExamTemplate: "
            f"{len(parsed_exams)}"
        )

        self.stdout.write(
            "ExamQuestion: "
            f"{exam_question_count}"
        )

        self.stdout.write(
            "Posiciones sin mapear: "
            f"{len(unmapped_exam_questions)}"
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "REVISIÓN"
            )
        )

        self.stdout.write(
            "Question con needs_review: "
            f"{questions_needing_review}"
        )

        self.stdout.write(
            "Recursos todavía no resueltos: "
            f"{len(unresolved_resources)}"
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "IMÁGENES"
            )
        )

        self.stdout.write(
            "Referencias de pregunta "
            "recuperadas desde duplicados: "
            f"{recovered_question_images}"
        )

        self.stdout.write(
            "Referencias de opción "
            "recuperadas desde duplicados: "
            f"{recovered_option_images}"
        )

        self.stdout.write(
            "Archivos multimedia únicos "
            "a copiar: "
            f"{len(resource_inventory)}"
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "SEGURIDAD"
            )
        )

        self.stdout.write(
            "Errores bloqueantes: "
            f"{len(blocking_errors)}"
        )

        if blocking_errors:
            for error in blocking_errors:
                self.stdout.write(
                    self.style.ERROR(
                        f"  - {error}"
                    )
                )

        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "Plan apto para preparar "
                    "la importación transaccional."
                )
            )

        self.stdout.write("")
        self.stdout.write(
            f"Reporte: {REPORT_PATH}"
        )