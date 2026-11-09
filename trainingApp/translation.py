from modeltranslation.translator import TranslationOptions, translator

from .models import (
    Choice,
    ChoiceSet,
    ChoiceSetOption,
    Course,
    Training,
    TrainingBlock,
    TrainingQuestion,
)


class TrainingTranslationOptions(TranslationOptions):
    fields = ("name_training",)  # campos para traducir


class TrainingBlockTranslationOptions(TranslationOptions):
    fields = (
        "name_block",
        "description",
        "default_question",
    )  # campos para traducir


class TrainingQuestionTranslationOptions(TranslationOptions):
    fields = ("question",)  # campos para traducir


class ChoiceTranslationOptions(TranslationOptions):
    fields = ("choice",)


class ChoiceSetTranslationOptions(TranslationOptions):
    fields = ("name",)


class ChoiceSetOptionTranslationOptions(TranslationOptions):
    fields = ("text",)


class CourseTranslationOptions(TranslationOptions):
    fields = (
        "name_course",
        "description",
    )


translator.register(Training, TrainingTranslationOptions)
translator.register(TrainingBlock, TrainingBlockTranslationOptions)
translator.register(TrainingQuestion, TrainingQuestionTranslationOptions)
translator.register(Choice, ChoiceTranslationOptions)
translator.register(ChoiceSet, ChoiceSetTranslationOptions)
translator.register(ChoiceSetOption, ChoiceSetOptionTranslationOptions)
translator.register(Course, CourseTranslationOptions)
