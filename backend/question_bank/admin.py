from django.contrib import admin

from .models import (
    Area,
    Choice,
    EducationLevel,
    Institution,
    Question,
    QuestionContext,
    QuestionVersion,
    Subject,
    Unit,
)


@admin.register(EducationLevel)
class EducationLevelAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "is_active",
    )

    search_fields = (
        "code",
        "name",
    )


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "is_active",
    )

    search_fields = (
        "code",
        "name",
    )


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = (
        "institution",
        "level",
        "code",
        "name",
        "is_active",
    )

    list_filter = (
        "level",
        "institution",
        "is_active",
    )

    search_fields = (
        "code",
        "name",
    )


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "is_active",
    )

    search_fields = (
        "code",
        "name",
    )


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "code",
        "name",
        "is_active",
    )

    list_filter = (
        "subject",
        "is_active",
    )

    search_fields = (
        "code",
        "name",
    )


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4


@admin.register(QuestionVersion)
class QuestionVersionAdmin(admin.ModelAdmin):
    list_display = (
        "question",
        "version",
        "question_type",
        "created_at",
    )

    inlines = (
        ChoiceInline,
    )


class QuestionContextInline(admin.TabularInline):
    model = QuestionContext
    extra = 1


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "status",
    )

    inlines = (
        QuestionContextInline,
    )


@admin.register(QuestionContext)
class QuestionContextAdmin(admin.ModelAdmin):
    list_display = (
        "question",
        "level",
        "institution",
        "area",
        "subject",
        "unit",
    )

    list_filter = (
        "level",
        "institution",
        "area",
        "subject",
    )