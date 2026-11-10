from django.db import models

from question_bank.models import (
    Area,
    EducationLevel,
    Institution,
    Question,
    Subject,
)


class ExamTemplate(models.Model):
    class SourceKind(models.TextChoices):
        GENERAL = "GENERAL", "Simulador general"
        SUBJECT = "SUBJECT", "Simulador por materia"
        UNIVERSITY = "UNIVERSITY", "Simulador universitario"
        OTHER = "OTHER", "Otro"

    class Mode(models.TextChoices):
        FIXED = "FIXED", "Fijo"
        RANDOM = "RANDOM", "Aleatorio"
        HYBRID = "HYBRID", "Híbrido"

    code = models.CharField(
        max_length=200,
        unique=True,
    )

    name = models.CharField(
        max_length=250,
    )

    level = models.ForeignKey(
        EducationLevel,
        on_delete=models.PROTECT,
        related_name="exams",
    )

    institution = models.ForeignKey(
        Institution,
        on_delete=models.PROTECT,
        related_name="exams",
    )

    area = models.ForeignKey(
        Area,
        on_delete=models.PROTECT,
        related_name="exams",
        null=True,
        blank=True,
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name="exams",
        null=True,
        blank=True,
    )

    source_kind = models.CharField(
        max_length=20,
        choices=SourceKind.choices,
        default=SourceKind.GENERAL,
    )

    mode = models.CharField(
        max_length=20,
        choices=Mode.choices,
        default=Mode.FIXED,
    )

    legacy_source_file = models.CharField(
        max_length=500,
        unique=True,
        null=True,
        blank=True,
    )

    legacy_version = models.CharField(
        max_length=100,
        blank=True,
    )

    legacy_configuration = models.JSONField(
        default=dict,
        blank=True,
    )

    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    timer_allowed = models.BooleanField(
        default=True,
    )

    timer_active_by_default = models.BooleanField(
        default=False,
    )

    auto_close = models.BooleanField(
        default=False,
    )

    allow_review = models.BooleanField(
        default=True,
    )

    show_results_by_subject = models.BooleanField(
        default=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "level__name",
            "institution__name",
            "name",
        ]

    def __str__(self):
        return self.name


class ExamQuestion(models.Model):
    exam = models.ForeignKey(
        ExamTemplate,
        on_delete=models.CASCADE,
        related_name="exam_questions",
    )

    question = models.ForeignKey(
        Question,
        on_delete=models.PROTECT,
        related_name="exam_occurrences",
    )

    position = models.PositiveIntegerField()

    legacy_question_id = models.CharField(
        max_length=50,
        blank=True,
    )

    legacy_subject_name = models.CharField(
        max_length=200,
        blank=True,
    )

    class Meta:
        ordering = [
            "exam_id",
            "position",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "exam",
                    "position",
                ],
                name="unique_question_position_per_exam",
            )
        ]

        indexes = [
            models.Index(
                fields=[
                    "exam",
                    "position",
                ],
            ),
            models.Index(
                fields=[
                    "question",
                ],
            ),
        ]

    def __str__(self):
        return (
            f"{self.exam.name} - "
            f"{self.position}"
        )