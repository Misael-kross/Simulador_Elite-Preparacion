import hashlib
import json
import shutil
from pathlib import Path

from django.core.management.base import (
    BaseCommand,
    CommandError,
)


LEGACY_ROOT = Path("/legacy_frontend")

PLAN_PATH = Path(
    "/reports/full_import_plan.json"
)

STAGING_ROOT = Path(
    "/media/import_staging/legacy_media"
)

MANIFEST_PATH = Path(
    "/reports/media_staging_manifest.json"
)


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


class Command(BaseCommand):
    help = (
        "Prepara y verifica las imágenes "
        "heredadas en staging sin modificar "
        "PostgreSQL."
    )

    def handle(self, *args, **options):
        if not PLAN_PATH.is_file():
            raise CommandError(
                "No existe "
                "/reports/full_import_plan.json. "
                "Ejecuta primero "
                "plan_legacy_full_import."
            )

        with PLAN_PATH.open(
            "r",
            encoding="utf-8",
        ) as file_obj:
            plan = json.load(file_obj)

        resources = plan.get(
            "resources",
            [],
        )

        expected_count = (
            plan.get(
                "summary",
                {},
            ).get(
                "unique_media_files"
            )
        )

        if expected_count is None:
            raise CommandError(
                "El plan no contiene "
                "unique_media_files."
            )

        if len(resources) != expected_count:
            raise CommandError(
                "El inventario de recursos "
                "no coincide con el resumen: "
                f"{len(resources)} != "
                f"{expected_count}"
            )

        # -----------------------------------------
        # Limpiar exclusivamente nuestro staging
        # -----------------------------------------

        if STAGING_ROOT.exists():
            shutil.rmtree(
                STAGING_ROOT
            )

        STAGING_ROOT.mkdir(
            parents=True,
            exist_ok=True,
        )

        manifest = []

        missing_sources = []
        hash_errors = []

        copied = 0
        reused = 0

        category_counts = {
            "question": 0,
            "choice": 0,
        }

        for resource in resources:
            expected_sha256 = resource[
                "sha256"
            ]

            suffix = (
                resource.get(
                    "suffix"
                )
                or ""
            ).lower()

            categories = resource.get(
                "categories",
                [],
            )

            source_paths = resource.get(
                "source_paths",
                [],
            )

            selected_source = None

            # -------------------------------------
            # Buscar una copia física válida
            # -------------------------------------

            for relative_path in source_paths:
                candidate = (
                    LEGACY_ROOT
                    / relative_path
                )

                if not candidate.is_file():
                    continue

                actual_hash = sha256_file(
                    candidate
                )

                if (
                    actual_hash
                    == expected_sha256
                ):
                    selected_source = (
                        candidate
                    )
                    break

            if selected_source is None:
                missing_sources.append(
                    {
                        "sha256": (
                            expected_sha256
                        ),
                        "source_paths": (
                            source_paths
                        ),
                    }
                )
                continue

            filename = (
                f"{expected_sha256}"
                f"{suffix}"
            )

            destination = (
                STAGING_ROOT
                / filename
            )

            if destination.exists():
                existing_hash = (
                    sha256_file(
                        destination
                    )
                )

                if (
                    existing_hash
                    == expected_sha256
                ):
                    reused += 1

                else:
                    destination.unlink()

                    shutil.copy2(
                        selected_source,
                        destination,
                    )

                    copied += 1

            else:
                shutil.copy2(
                    selected_source,
                    destination,
                )

                copied += 1

            # -------------------------------------
            # Verificación posterior a copia
            # -------------------------------------

            final_hash = sha256_file(
                destination
            )

            if final_hash != expected_sha256:
                hash_errors.append(
                    {
                        "file": str(
                            destination
                        ),
                        "expected": (
                            expected_sha256
                        ),
                        "actual": (
                            final_hash
                        ),
                    }
                )
                continue

            if "question" in categories:
                category_counts[
                    "question"
                ] += 1

            if "choice" in categories:
                category_counts[
                    "choice"
                ] += 1

            manifest.append(
                {
                    "sha256": (
                        expected_sha256
                    ),
                    "suffix": suffix,
                    "categories": (
                        categories
                    ),
                    "source": str(
                        selected_source.relative_to(
                            LEGACY_ROOT
                        )
                    ),
                    "staged_file": (
                        f"import_staging/"
                        f"legacy_media/"
                        f"{filename}"
                    ),
                    "size_bytes": (
                        destination.stat().st_size
                    ),
                }
            )

        # -----------------------------------------
        # Validaciones finales
        # -----------------------------------------

        staged_files = [
            path
            for path in (
                STAGING_ROOT.iterdir()
            )
            if path.is_file()
        ]

        blocking_errors = []

        if missing_sources:
            blocking_errors.append(
                "Hay recursos sin una "
                "fuente física válida."
            )

        if hash_errors:
            blocking_errors.append(
                "Hay archivos cuyo SHA-256 "
                "no coincide después de copiar."
            )

        if len(manifest) != expected_count:
            blocking_errors.append(
                "El manifiesto no contiene "
                "la cantidad esperada de "
                "recursos."
            )

        if len(staged_files) != expected_count:
            blocking_errors.append(
                "La carpeta staging no contiene "
                "la cantidad esperada de "
                "archivos."
            )

        report = {
            "expected_files": (
                expected_count
            ),
            "manifest_files": (
                len(manifest)
            ),
            "physical_staged_files": (
                len(staged_files)
            ),
            "copied": copied,
            "reused": reused,
            "question_media_files": (
                category_counts[
                    "question"
                ]
            ),
            "choice_media_files": (
                category_counts[
                    "choice"
                ]
            ),
            "missing_sources": (
                missing_sources
            ),
            "hash_errors": (
                hash_errors
            ),
            "blocking_errors": (
                blocking_errors
            ),
            "files": manifest,
        }

        MANIFEST_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with MANIFEST_PATH.open(
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
                "STAGING DE MULTIMEDIA "
                "COMPLETADO"
            )
        )

        self.stdout.write("")
        self.stdout.write(
            "No se modificó PostgreSQL."
        )

        self.stdout.write("")
        self.stdout.write(
            f"Archivos esperados: "
            f"{expected_count}"
        )

        self.stdout.write(
            f"Archivos en manifiesto: "
            f"{len(manifest)}"
        )

        self.stdout.write(
            "Archivos físicos en staging: "
            f"{len(staged_files)}"
        )

        self.stdout.write(
            "Recursos de pregunta: "
            f"{category_counts['question']}"
        )

        self.stdout.write(
            "Recursos de opciones: "
            f"{category_counts['choice']}"
        )

        self.stdout.write(
            "Fuentes no encontradas: "
            f"{len(missing_sources)}"
        )

        self.stdout.write(
            "Errores de integridad SHA-256: "
            f"{len(hash_errors)}"
        )

        self.stdout.write(
            "Errores bloqueantes: "
            f"{len(blocking_errors)}"
        )

        self.stdout.write("")
        self.stdout.write(
            f"Staging: {STAGING_ROOT}"
        )

        self.stdout.write(
            f"Manifiesto: {MANIFEST_PATH}"
        )

        if blocking_errors:
            for error in blocking_errors:
                self.stdout.write(
                    self.style.ERROR(
                        f"  - {error}"
                    )
                )

            raise CommandError(
                "El staging no pasó "
                "las verificaciones."
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Los archivos están listos "
                "para la importación "
                "transaccional."
            )
        )