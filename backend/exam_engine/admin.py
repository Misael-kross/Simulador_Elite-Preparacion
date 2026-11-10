from django.contrib import admin

from .models import (
    ExamQuestion,
    ExamTemplate,
)


class ExamQuestionInline(admin.TabularInline):
    model = ExamQuestion
    extra = 0

    fields = (
        "position",
        "question",
        "legacy_question_id",
        "legacy_subject_name",
    )

    ordering = (
        "position",
    )

    autocomplete_fields = (
        "question",
    )


@admin.register(ExamTemplate)
class ExamTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "level",
        "institution",
        "area",
        "subject",
        "source_kind",
        "mode",
        "is_active",
    )

    list_filter = (
        "level",
        "institution",
        "source_kind",
        "mode",
        "is_active",
    )

    search_fields = (
        "code",
        "name",
        "legacy_source_file",
    )

    autocomplete_fields = (
        "level",
        "institution",
        "area",
        "subject",
    )

    inlines = (
        ExamQuestionInline,
    )


@admin.register(ExamQuestion)
class ExamQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "exam",
        "position",
        "question",
        "legacy_question_id",
        "legacy_subject_name",
    )

    list_filter = (
        "exam",
    )

    search_fields = (
        "exam__name",
        "legacy_question_id",
        "legacy_subject_name",
    )

    autocomplete_fields = (
        "exam",
        "question",
    )

    ordering = (
        "exam",
        "position",
    )