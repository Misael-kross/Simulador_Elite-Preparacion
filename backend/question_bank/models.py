from django.core.exceptions import ValidationError
from django.db import models


class EducationLevel(models.Model):
    code = models.CharField(
        max_length=30,
        unique=True,
    )

    name = models.CharField(
        max_length=100,
    )

    is_active = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return self.name


class Institution(models.Model):
    code = models.CharField(
        max_length=50,
        unique=True,
    )

    name = models.CharField(
        max_length=150,
    )

    is_active = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return self.name


class Area(models.Model):
    level = models.ForeignKey(
        EducationLevel,
        on_delete=models.PROTECT,
        related_name="areas",
    )

    institution = models.ForeignKey(
        Institution,
        on_delete=models.PROTECT,
        related_name="areas",
    )

    code = models.CharField(
        max_length=80,
    )

    name = models.CharField(
        max_length=200,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "level",
                    "institution",
                    "code",
                ],
                name="unique_area_per_level_institution",
            ),
        ]

    def __str__(self):
        return f"{self.institution.name} - {self.name}"


class Subject(models.Model):
    code = models.CharField(
        max_length=80,
        unique=True,
    )

    name = models.CharField(
        max_length=150,
    )

    is_active = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return self.name


class Unit(models.Model):
    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name="units",
    )

    code = models.CharField(
        max_length=80,
    )

    name = models.CharField(
        max_length=200,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "subject",
                    "code",
                ],
                name="unique_unit_per_subject",
            ),
        ]

    def __str__(self):
        return f"{self.subject.name} - {self.name}"


class Question(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Borrador"
        PUBLISHED = "PUBLISHED", "Publicada"
        RETIRED = "RETIRED", "Retirada"

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"Pregunta {self.pk}"


class QuestionContext(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="contexts",
    )

    level = models.ForeignKey(
        EducationLevel,
        on_delete=models.PROTECT,
        related_name="question_contexts",
    )

    institution = models.ForeignKey(
        Institution,
        on_delete=models.PROTECT,
        related_name="question_contexts",
    )

    area = models.ForeignKey(
        Area,
        on_delete=models.PROTECT,
        related_name="question_contexts",
        null=True,
        blank=True,
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name="question_contexts",
    )

    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="question_contexts",
        null=True,
        blank=True,
    )

    def clean(self):
        if self.area:
            if self.area.institution_id != self.institution_id:
                raise ValidationError(
                    "El área no pertenece a la institución seleccionada."
                )

            if self.area.level_id != self.level_id:
                raise ValidationError(
                    "El área no pertenece al nivel seleccionado."
                )

        if self.unit:
            if self.unit.subject_id != self.subject_id:
                raise ValidationError(
                    "La unidad no pertenece a la materia seleccionada."
                )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "question",
                    "level",
                    "institution",
                    "area",
                    "subject",
                    "unit",
                ],
                 name="unique_question_academic_context",
                 nulls_distinct=False,
            ),
        ]

    def __str__(self):
        return (
            f"{self.question} - "
            f"{self.institution} - "
            f"{self.subject}"
        )


class QuestionVersion(models.Model):
    class QuestionType(models.TextChoices):
        TEXT = "TEXT", "Texto"
        MIXED = "MIXED", "Texto e imagen"

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="versions",
    )

    version = models.PositiveIntegerField(
        default=1
    )

    question_type = models.CharField(
        max_length=20,
        choices=QuestionType.choices,
        default=QuestionType.TEXT,
    )

    content = models.TextField()

    image = models.FileField(
        upload_to="questions/",
        null=True,
        blank=True,
    )

    explanation = models.TextField(
        blank=True
    )

    observations = models.TextField(
        blank=True
    )

    needs_review = models.BooleanField(
        default=False
    )

    review_notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = [
            "question_id",
            "version",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "question",
                    "version",
                ],
                name="unique_question_version",
            )
        ]

    def __str__(self):
        return (
            f"Pregunta {self.question_id} "
            f"v{self.version}"
        )


class Choice(models.Model):
    question_version = models.ForeignKey(
        QuestionVersion,
        on_delete=models.CASCADE,
        related_name="choices",
    )

    label = models.CharField(
        max_length=10,
    )

    text = models.TextField(
        blank=True,
    )

    image = models.FileField(
        upload_to="questions/choices/",
        null=True,
        blank=True,
    )

    position = models.PositiveIntegerField()

    is_correct = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = [
            "position",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "question_version",
                    "label",
                ],
                name="unique_choice_label_per_version",
            ),

            models.UniqueConstraint(
                fields=[
                    "question_version",
                    "position",
                ],
                name="unique_choice_position_per_version",
            ),
        ]

    def __str__(self):
        return (
            f"{self.question_version} - "
            f"{self.label}"
        )