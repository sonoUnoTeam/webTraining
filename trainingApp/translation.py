from .models import TrainingQuestion, Choice, TrainingBlock, Training, Course
from modeltranslation.translator import translator, TranslationOptions

class TrainingTranslationOptions(TranslationOptions):
    fields = ('name_training',)  # campos para traducir
    
class TrainingBlockTranslationOptions(TranslationOptions):
    fields = ('name_block', 'description',)  # campos para traducir
    
class TrainingQuestionTranslationOptions(TranslationOptions):
    fields = ('question',)  # campos para traducir

class ChoiceTranslationOptions(TranslationOptions):
    fields = ('choice',)

class CourseTranslationOptions(TranslationOptions):
    fields = ('name_course', 'description',)

translator.register(Training, TrainingTranslationOptions)
translator.register(TrainingBlock, TrainingBlockTranslationOptions)
translator.register(TrainingQuestion, TrainingQuestionTranslationOptions)
translator.register(Choice, ChoiceTranslationOptions)
translator.register(Course, CourseTranslationOptions)

