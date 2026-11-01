# Completa los datos de la estructura de contenido agregada en 0004:
# 1. order de bloques, preguntas y opciones = orden de creación (id), que es como se mostraban.
# 2. is_correct de las respuestas existentes, copiado de selectedChoice.correctChoice.
# 3. ChoiceSets a partir de los conjuntos de opciones que ya se repiten entre preguntas
#    (misma lista de textos EN/ES en el mismo orden, usada por al menos 2 preguntas y
#    sin opciones vacías en todos los idiomas).
# 4. Consigna y conjunto por defecto de cada bloque cuando todas sus preguntas los comparten.
#
# No modifica Choices ni respuestas existentes: los ChoiceSets son plantillas para el contenido nuevo.
# Idempotente: solo completa lo que está vacío y reutiliza los ChoiceSets equivalentes; reverse no hace nada.

from django.db import migrations

LANGUAGES = ('en', 'es')
DEFAULT_LANGUAGE = 'en'
NAME_MAX_LENGTH = 200


def fill_order(model, scope_field):
    """order = 1..n por padre según id, solo en padres donde ningún elemento tiene orden asignado."""
    updated = 0
    scope_ids = model.objects.order_by().values_list(scope_field, flat=True).distinct()
    for scope_id in scope_ids:
        siblings = model.objects.filter(**{scope_field: scope_id}).order_by('id')
        if siblings.exclude(order=0).exists():
            continue
        for position, pk in enumerate(siblings.values_list('pk', flat=True), 1):
            model.objects.filter(pk=pk).update(order=position)
            updated += 1
    return updated


def choices_signature(choices):
    return tuple(tuple(getattr(choice, f'choice_{lang}') or '' for lang in LANGUAGES) for choice in choices)


def options_signature(options):
    return tuple(tuple(getattr(option, f'text_{lang}') or '' for lang in LANGUAGES) for option in options)


def set_name(signature, lang_index):
    # Si una opción no tiene texto en ese idioma se usa el primero que tenga, como el fallback de modeltranslation
    name = ' / '.join(texts[lang_index] or next(text for text in texts if text) for texts in signature)
    return name if len(name) <= NAME_MAX_LENGTH else name[:NAME_MAX_LENGTH - 1] + '…'


def has_empty_option(signature):
    return any(not any(texts) for texts in signature)


def backfill(apps, schema_editor):
    TrainingBlock = apps.get_model('trainingApp', 'TrainingBlock')
    TrainingQuestion = apps.get_model('trainingApp', 'TrainingQuestion')
    Choice = apps.get_model('trainingApp', 'Choice')
    TrainingQuestionAnswer = apps.get_model('trainingApp', 'TrainingQuestionAnswer')
    ChoiceSet = apps.get_model('trainingApp', 'ChoiceSet')
    ChoiceSetOption = apps.get_model('trainingApp', 'ChoiceSetOption')

    # 1. Orden
    for model, scope_field in ((TrainingBlock, 'training_id'), (TrainingQuestion, 'block_id'), (Choice, 'deploy_id')):
        updated = fill_order(model, scope_field)
        if updated:
            print(f'  {model.__name__}.order: {updated}')

    # 2. is_correct
    pending = TrainingQuestionAnswer.objects.filter(is_correct__isnull=True)
    correct = pending.filter(selectedChoice__correctChoice=True).update(is_correct=True)
    incorrect = pending.filter(selectedChoice__correctChoice=False).update(is_correct=False)
    if correct or incorrect:
        print(f'  TrainingQuestionAnswer.is_correct: {correct} correct, {incorrect} incorrect')

    # 3. ChoiceSets
    signature_by_question = {}
    for question in TrainingQuestion.objects.prefetch_related('choice_set'):
        choices = sorted(question.choice_set.all(), key=lambda choice: (choice.order, choice.id))
        if len(choices) >= 2:
            signature_by_question[question.id] = choices_signature(choices)

    usages = {}
    for signature in signature_by_question.values():
        usages[signature] = usages.get(signature, 0) + 1

    set_by_signature = {}
    for choice_set in ChoiceSet.objects.prefetch_related('options'):
        options = sorted(choice_set.options.all(), key=lambda option: (option.order, option.id))
        set_by_signature.setdefault(options_signature(options), choice_set)

    created_sets = 0
    for signature, count in usages.items():
        if count < 2 or signature in set_by_signature or has_empty_option(signature):
            continue
        names = {f'name_{lang}': set_name(signature, i) for i, lang in enumerate(LANGUAGES)}
        choice_set = ChoiceSet.objects.create(name=names[f'name_{DEFAULT_LANGUAGE}'], **names)
        for position, texts in enumerate(signature, 1):
            option_texts = {f'text_{lang}': texts[i] for i, lang in enumerate(LANGUAGES)}
            ChoiceSetOption.objects.create(
                choice_set=choice_set,
                order=position,
                text=option_texts[f'text_{DEFAULT_LANGUAGE}'],
                **option_texts,
            )
        set_by_signature[signature] = choice_set
        created_sets += 1
    if created_sets:
        print(f'  ChoiceSet: {created_sets} created')

    # 4. Defaults de cada bloque
    updated_blocks = 0
    for block in TrainingBlock.objects.all():
        questions = list(TrainingQuestion.objects.filter(block=block))
        if not questions:
            continue
        changed = False

        if block.default_choice_set_id is None:
            signatures = {signature_by_question.get(question.id) for question in questions}
            if len(signatures) == 1:
                choice_set = set_by_signature.get(signatures.pop())
                if choice_set is not None:
                    block.default_choice_set = choice_set
                    changed = True

        for lang in LANGUAGES:
            field = f'default_question_{lang}'
            texts = {getattr(question, f'question_{lang}') or '' for question in questions}
            if not getattr(block, field) and len(texts) == 1 and '' not in texts:
                setattr(block, field, texts.pop())
                changed = True
        if changed:
            block.default_question = getattr(block, f'default_question_{DEFAULT_LANGUAGE}')
            block.save()
            updated_blocks += 1
    if updated_blocks:
        print(f'  TrainingBlock defaults: {updated_blocks} blocks')


class Migration(migrations.Migration):

    dependencies = [
        ('trainingApp', '0004_content_structure'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
