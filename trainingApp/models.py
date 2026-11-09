import datetime

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models, transaction
from django.db.models import Max, Sum
from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _
from modeltranslation.settings import AVAILABLE_LANGUAGES

from userApp.models import Trainee


class AutoOrderMixin(models.Model):
    """
    Campo `order` que se completa solo: al crear un objeto sin orden (0) toma el último + 1
    dentro del padre indicado en `order_scope` (nombre del FK). El orden explícito se respeta, y
    en objetos existentes 0 es un orden válido (al arrastrar filas el admin numera desde 0).
    """

    order_scope = None
    order = models.PositiveIntegerField(_("order"), default=0)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self._state.adding and not self.order:
            scope_id = getattr(self, f"{self.order_scope}_id")
            siblings = (
                type(self)
                .objects.filter(**{f"{self.order_scope}_id": scope_id})
                .exclude(pk=self.pk)
            )
            self.order = (siblings.aggregate(Max("order"))["order__max"] or 0) + 1
        super().save(*args, **kwargs)


class TraineeGroup(models.Model):
    """
    Grupo de trainees: decide qué cursos ve cada uno. Un trainee pertenece a un solo grupo
    (`Trainee.group`) y ve los cursos activos que tienen asignado ese grupo (`Course.groups`).
    El grupo por defecto (`is_default`) recibe a los usuarios nuevos y a los miembros de un
    grupo borrado; se identifica por el campo, no por el nombre, así se puede renombrar.
    """

    # Nombre con que se crea el grupo por defecto si todavía no hay ninguno
    DEFAULT_NAME = "Default group"

    name_group = models.CharField(_("name"), max_length=100)
    description = models.CharField(_("description"), max_length=300, blank=True)
    is_default = models.BooleanField(
        _("default group"),
        default=False,
        help_text=_(
            "New trainees join this group when they sign up. Only one group can be the default."
        ),
    )

    class Meta:
        ordering = ["name_group", "id"]
        verbose_name = _("trainee group")
        verbose_name_plural = _("trainee groups")

    def __str__(self):
        return self.name_group

    def clean(self):
        # Sin grupo por defecto los usuarios nuevos no tendrían a dónde ir: se cambia marcando otro
        if self.pk and not self.is_default:
            was_default = TraineeGroup.objects.filter(
                pk=self.pk, is_default=True
            ).exists()
            if was_default:
                raise ValidationError(
                    {
                        "is_default": _(
                            "To change the default group, mark another group as the default."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        with transaction.atomic():
            super().save(*args, **kwargs)
            if self.is_default:
                TraineeGroup.objects.filter(is_default=True).exclude(pk=self.pk).update(
                    is_default=False
                )

    @classmethod
    def get_default(cls):
        """Grupo por defecto; si no hay ninguno lo crea."""
        group = cls.objects.filter(is_default=True).order_by("id").first()
        if group is None:
            group = cls.objects.create(name_group=cls.DEFAULT_NAME, is_default=True)
        return group


@receiver(pre_delete, sender=TraineeGroup)
def move_members_to_default_group(sender, instance, **kwargs):
    """Al borrar un grupo sus trainees pasan al grupo por defecto en lugar de quedar sin cursos."""
    if instance.is_default:
        return
    Trainee.objects.filter(group=instance).update(group=TraineeGroup.get_default())


class ChoiceSet(models.Model):
    """
    Conjunto reutilizable de opciones (p. ej. "Estrella / Galaxia"). Funciona como plantilla:
    al aplicarlo a una pregunta se copian sus opciones como Choices de esa pregunta.
    """

    name = models.CharField(_("name"), max_length=200)

    class Meta:
        verbose_name = _("option set")
        verbose_name_plural = _("option sets")

    def __str__(self):
        return self.name


class ChoiceSetOption(AutoOrderMixin):
    order_scope = "choice_set"
    choice_set = models.ForeignKey(
        ChoiceSet,
        on_delete=models.CASCADE,
        related_name="options",
        verbose_name=_("option set"),
    )
    text = models.CharField(_("text"), max_length=100)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("set option")
        verbose_name_plural = _("set options")

    def __str__(self):
        return self.text


class Training(models.Model):
    # Enumeracion para el tipo de entrenamiento
    class TrainingType(models.TextChoices):
        Easy = "Easy", _("Easy")
        Intemediate = "Intermediate", _("Intermediate")
        Advanced = "Advanced", _("Advanced")

    class StateTraining(models.TextChoices):
        Active = "Active", _("Active")
        inactive = "Inactive", _("Inactive")

    name_training = models.CharField(_("name"), max_length=200)
    pub_date = models.DateTimeField(_("created"), auto_now_add=True)
    modificationDate = models.DateTimeField(_("modified"), auto_now=True)
    difficulty = models.CharField(
        _("difficulty"),
        max_length=20,
        choices=TrainingType.choices,
        default=TrainingType.Easy,
    )
    estimatedDuration = models.IntegerField(
        _("estimated duration (minutes)"), default=0
    )
    state_training = models.CharField(
        _("status"),
        max_length=20,
        choices=StateTraining.choices,
        default=StateTraining.Active,
    )
    # Atributo que gestiona la cantidad de veces que se puede realizar el training
    attempts_allowed = models.IntegerField(_("attempts allowed"), default=1)
    # Porcentaje mínimo requerido para aprobar este training (por defecto 70%)
    passing_score = models.DecimalField(
        _("passing score (%)"), max_digits=5, decimal_places=2, default=70.00
    )

    class Meta:
        verbose_name = _("training")
        verbose_name_plural = _("trainings")

    def was_published_recently(self):
        return self.pub_date >= timezone.now() - datetime.timedelta(days=1)

    def __str__(self):
        return self.name_training

    def duplicate(self):
        """
        Copia el training con sus bloques, preguntas y opciones en todos los idiomas. Los audios
        e imágenes se reutilizan (misma ruta, sin volver a subirlos). No copia cursos ni intentos.
        """
        blocks = list(
            self.trainingblock_set.prefetch_related("trainingquestion_set__choice_set")
        )
        with transaction.atomic():
            copy = Training.objects.get(pk=self.pk)
            copy.pk = None
            copy._state.adding = True
            for lang in AVAILABLE_LANGUAGES:
                name = getattr(self, f"name_training_{lang}")
                if name:
                    with translation.override(lang):
                        setattr(
                            copy,
                            f"name_training_{lang}",
                            _("%(name)s (copy)") % {"name": name},
                        )
            copy.save()
            for block in blocks:
                questions = list(block.trainingquestion_set.all())
                block.pk, block._state.adding, block.training = None, True, copy
                block.save()
                for question in questions:
                    choices = list(question.choice_set.all())
                    question.pk, question._state.adding, question.block = (
                        None,
                        True,
                        block,
                    )
                    question.save()
                    for choice in choices:
                        choice.pk, choice._state.adding, choice.deploy = (
                            None,
                            True,
                            question,
                        )
                        choice.save()
        return copy

    # Metodo que trae la cantidad de veces que se realizo un training por un trainee especifico
    def get_num_trainee_trainings(self, trainee_id):
        return TraineeTraining.objects.filter(
            training=self, trainee_id=trainee_id
        ).count()

    @property
    def total_estimated_duration(self):
        """
        Calcula y devuelve la suma de los estimatedDuration de todos los bloques asociados a este entrenamiento.
        """
        return (
            self.trainingblock_set.aggregate(
                total_duration=Sum("estimed_duration_block")
            )["total_duration"]
            or 0
        )


class TrainingBlock(AutoOrderMixin):
    class StateBlock(models.TextChoices):
        Active = "Active", _("Active")
        inactive = "Inactive", _("Inactive")

    order_scope = "training"
    name_block = models.CharField(_("name"), max_length=100)
    description = models.CharField(_("description"), max_length=500, blank=True)
    estimed_duration_block = models.IntegerField(
        _("estimated duration (minutes)"), default=0
    )
    state_block = models.CharField(
        _("status"),
        max_length=20,
        choices=StateBlock.choices,
        default=StateBlock.Active,
    )
    training = models.ForeignKey(
        Training, on_delete=models.CASCADE, verbose_name=_("training")
    )
    # Valores que heredan las preguntas nuevas del bloque (consigna y opciones)
    default_question = models.CharField(
        _("default question text"), max_length=255, blank=True
    )
    default_choice_set = models.ForeignKey(
        ChoiceSet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("default option set"),
    )

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("block")
        verbose_name_plural = _("blocks")

    def __str__(self):
        return f"{self.name_block} ({self.training})"


class TrainingQuestion(AutoOrderMixin):
    order_scope = "block"
    block = models.ForeignKey(
        TrainingBlock, on_delete=models.CASCADE, null=True, verbose_name=_("block")
    )
    question = models.CharField(_("question text"), max_length=255, null=True)
    deploy_image = models.ImageField(
        _("image"), upload_to="trainingApp/images", blank=True
    )
    deploy_sound = models.FileField(
        _("sound"),
        upload_to="trainingApp/sound",
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=["mp3", "wav"])],
    )

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("question")
        verbose_name_plural = _("questions")

    def __str__(self):
        return self.question or _("Question %(id)s") % {"id": self.id}

    def fill_from_block_defaults(self):
        """Completa con la consigna por defecto del bloque los idiomas en que la pregunta no tiene texto (no guarda)."""
        if self.block is None:
            return
        for lang in AVAILABLE_LANGUAGES:
            if not getattr(self, f"question_{lang}"):
                setattr(
                    self,
                    f"question_{lang}",
                    getattr(self.block, f"default_question_{lang}"),
                )

    def apply_choice_set(self, choice_set, correct_option=None):
        """
        Reemplaza las opciones de la pregunta por copias de las de `choice_set` (textos en cada
        idioma y orden). `correct_option` es la ChoiceSetOption que queda marcada como correcta.
        No se permite si la pregunta ya tiene respuestas: alteraría lo que eligieron los trainees.
        """
        if self.trainingquestionanswer_set.exists():
            raise ValidationError(
                _(
                    "This question already has answers, so its options cannot be replaced."
                )
            )
        with transaction.atomic():
            self.choice_set.all().delete()
            for option in choice_set.options.all():
                texts = {
                    f"choice_{lang}": getattr(option, f"text_{lang}")
                    for lang in AVAILABLE_LANGUAGES
                }
                Choice.objects.create(
                    deploy=self,
                    order=option.order,
                    correctChoice=correct_option is not None
                    and option.pk == correct_option.pk,
                    **texts,
                )


class Choice(AutoOrderMixin):
    order_scope = "deploy"
    deploy = models.ForeignKey(
        TrainingQuestion, on_delete=models.CASCADE, verbose_name=_("question")
    )
    choice = models.CharField(_("text"), max_length=100, null=True)
    correctChoice = models.BooleanField(_("correct"), default=False)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("option")
        verbose_name_plural = _("options")

    def __str__(self):
        text = self.choice or ""
        return _("%(text)s (correct)") % {"text": text} if self.correctChoice else text


class TraineeTraining(models.Model):
    class StateTraineeTraining(models.TextChoices):
        NOT_STARTED = "not_started", _("Not Started")
        IN_PROGRESS = "in_progress", _("In Progress")
        PASSED = "passed", _("Passed")
        FAILED = "failed", _("Failed")

    # Foreign Key al progreso del trainee en el curso (padre)
    trainee_course = models.ForeignKey(
        "TraineeCourse",
        on_delete=models.CASCADE,
        related_name="trainee_trainings",
        verbose_name=_("progress in the course"),
    )
    # Foreign Key de training
    training = models.ForeignKey(
        Training, on_delete=models.PROTECT, verbose_name=_("training")
    )
    # Foreign Key de trainee
    trainee = models.ForeignKey(
        Trainee, on_delete=models.CASCADE, verbose_name=_("trainee")
    )
    # Foreign Key de course
    course = models.ForeignKey(
        "Course", on_delete=models.CASCADE, verbose_name=_("course")
    )
    pub_date = models.DateTimeField(_("started"))
    state = models.CharField(
        _("result"),
        max_length=20,
        choices=StateTraineeTraining.choices,
        default=StateTraineeTraining.IN_PROGRESS,
    )
    time_spent = models.DurationField(_("time spent"), null=True, blank=True)
    # Indica si este intento corresponde al examen final del curso
    is_final_exam_attempt = models.BooleanField(_("final exam attempt"), default=False)
    # Puntuación obtenida en este intento (porcentaje)
    score_percentage = models.DecimalField(
        _("score (%)"), max_digits=5, decimal_places=2, null=True, blank=True, default=0
    )
    # Mejor puntuación obtenida (se actualiza si el nuevo intento es mejor)
    best_score = models.DecimalField(
        _("best score (%)"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        default=0,
    )
    # Cantidad de respuestas correctas e incorrectas
    correct_answers = models.PositiveIntegerField(_("correct answers"), default=0)
    incorrect_answers = models.PositiveIntegerField(_("incorrect answers"), default=0)

    class Meta:
        verbose_name = _("training attempt")
        verbose_name_plural = _("training attempts")

    def __str__(self):
        return f"{self.trainee} – {self.training} ({self.course})"

    def calculate_score(self):
        """
        Calcula el porcentaje de respuestas correctas del training y devuelve
        un diccionario con el porcentaje, respuestas correctas e incorrectas.

        El total son todas las preguntas de los bloques activos del training: una pregunta
        sin responder cuenta como incorrecta. Si una pregunta se respondió más de una vez
        en el intento, vale la última respuesta.
        """
        question_ids = set(
            TrainingQuestion.objects.filter(
                block__training=self.training,
                block__state_block=TrainingBlock.StateBlock.Active,
            ).values_list("id", flat=True)
        )
        question_answers = (
            TrainingQuestionAnswer.objects.filter(
                block_answer__trainee_Training=self, deploy_id__in=question_ids
            )
            .select_related("selectedChoice")
            .order_by("id")
        )
        is_correct_by_question = {}
        for question_answer in question_answers:
            is_correct_by_question[question_answer.deploy_id] = (
                question_answer.selectedChoice.correctChoice
            )

        total_questions = len(question_ids)
        correct_answers = sum(is_correct_by_question.values())
        incorrect_answers = total_questions - correct_answers

        # Calcular porcentaje
        if total_questions > 0:
            percentage = (correct_answers / total_questions) * 100
            percentage = round(percentage, 2)
        else:
            percentage = 0

        return {
            "percentage": percentage,
            "correct_answers": correct_answers,
            "incorrect_answers": incorrect_answers,
            "total_questions": total_questions,
        }

    def update_score_and_state(self):
        """
        Actualiza el score del intento actual y determina si aprobó o no.
        También actualiza el best_score si este intento es mejor.
        """
        score_data = self.calculate_score()

        self.score_percentage = score_data["percentage"]
        self.correct_answers = score_data["correct_answers"]
        self.incorrect_answers = score_data["incorrect_answers"]

        # Marcar como intento de examen final si corresponde
        if self.course.final_exam == self.training:
            self.is_final_exam_attempt = True

        # Determinar si aprobó o no
        # Si es examen final, usar el passing_score del curso; si no, usar el del training
        passing_score = (
            self.course.final_exam_passing_score
            if self.is_final_exam_attempt
            else self.training.passing_score
        )

        if self.score_percentage >= passing_score:
            self.state = self.StateTraineeTraining.PASSED
        else:
            self.state = self.StateTraineeTraining.FAILED

        self.save()

        # best_score = mejor puntaje entre todos los intentos terminados del mismo training/curso.
        # Solo se propaga best_score: correct/incorrect_answers son propios de cada intento.
        finished_attempts = TraineeTraining.objects.filter(
            trainee=self.trainee, training=self.training, course=self.course
        ).exclude(state=self.StateTraineeTraining.IN_PROGRESS)
        best_score = (
            finished_attempts.aggregate(best=Max("score_percentage"))["best"] or 0
        )
        finished_attempts.update(best_score=best_score)
        self.best_score = best_score

    @property
    def formatted_time_spent(self):
        """
        Returns the time_spent formatted as HH:MM:SS or MM:SS depending on duration.
        """
        if self.time_spent:
            total_seconds = int(self.time_spent.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60

            if hours > 0:
                return f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes}:{seconds:02d}"
        return "0:00"


class TrainingBlockAnswer(models.Model):
    class StateBlockAnswer(models.TextChoices):
        in_progress = "In progress", _("In progress")
        Completed = "Completed", _("Completed")

    state_block = models.CharField(
        _("status"),
        max_length=20,
        choices=StateBlockAnswer.choices,
        default=StateBlockAnswer.in_progress,
    )
    trainee_Training = models.ForeignKey(
        TraineeTraining, on_delete=models.CASCADE, verbose_name=_("attempt")
    )
    # PROTECT: borrar contenido no puede borrar respuestas de los trainees
    block = models.ForeignKey(
        TrainingBlock, on_delete=models.PROTECT, verbose_name=_("block")
    )

    class Meta:
        verbose_name = _("answered block")
        verbose_name_plural = _("answered blocks")

    def __str__(self):
        return f"{self.block.name_block} – {self.trainee_Training.trainee}"


# Clase para guardar la respuesta del usuario de cada deploy
class TrainingQuestionAnswer(models.Model):

    # foreing Key de B.A
    block_answer = models.ForeignKey(
        TrainingBlockAnswer,
        on_delete=models.CASCADE,
        null=True,
        verbose_name=_("answered block"),
    )
    # foreing Key de deploy (PROTECT: borrar contenido no puede borrar respuestas)
    deploy = models.ForeignKey(
        TrainingQuestion, on_delete=models.PROTECT, verbose_name=_("question")
    )
    # foreing Key de choice seleccionada
    selectedChoice = models.ForeignKey(
        Choice, on_delete=models.PROTECT, verbose_name=_("selected option")
    )
    # Copia de selectedChoice.correctChoice al momento de responder: si después se corrige
    # la opción correcta en el admin, queda registrado lo que valía cuando se respondió
    is_correct = models.BooleanField(_("correct"), null=True, blank=True)

    class Meta:
        verbose_name = _("answer")
        verbose_name_plural = _("answers")

    def __str__(self):
        return f"{self.deploy} → {self.selectedChoice.choice}"

    def save(self, *args, **kwargs):
        self.is_correct = self.selectedChoice.correctChoice
        super().save(*args, **kwargs)


class Comment(models.Model):
    # Enumeraciones para la nueva encuesta de opinión
    class CourseRating(models.TextChoices):
        VERY_INTERESTING = "very_interesting", _("Very interesting")
        INTERESTING = "interesting", _("Interesting")
        REPETITIVE = "repetitive", _("Repetitive")

    class TrainingMethod(models.TextChoices):
        NOVEL = "novel", _("Novel")
        INDIFFERENT = "indifferent", _("Indifferent")
        UNNECESSARY = "unnecessary", _("Unnecessary")

    class Explanations(models.TextChoices):
        VERY_USEFUL = "very_useful", _("Very useful and easy to understand")
        USEFUL_CONFUSING = "useful_confusing", _("Useful but confusing")
        USEFUL_EXCESSIVE = "useful_excessive", _("Useful but excessive")
        REPETITIVE = "repetitive", _("Very repetitive")

    # Foreign Key de training
    training = models.ForeignKey(
        Training, on_delete=models.CASCADE, verbose_name=_("training")
    )
    # Foreign Key de trainee
    trainee = models.ForeignKey(
        Trainee, on_delete=models.CASCADE, verbose_name=_("trainee")
    )

    course_rating = models.CharField(
        _("course rating"),
        max_length=30,
        choices=CourseRating.choices,
        blank=False,
        null=False,
        default=CourseRating.INTERESTING,
    )
    training_method = models.CharField(
        _("training method"),
        max_length=30,
        choices=TrainingMethod.choices,
        blank=False,
        null=False,
        default=TrainingMethod.NOVEL,
    )
    explanations = models.CharField(
        _("explanations"),
        max_length=30,
        choices=Explanations.choices,
        blank=False,
        null=False,
        default=Explanations.VERY_USEFUL,
    )
    stars = models.IntegerField(
        _("stars"),
        choices=[(i, i) for i in range(1, 6)],
        blank=False,
        null=False,
    )
    pub_date = models.DateTimeField(_("date"))

    class Meta:
        verbose_name = _("feedback survey")
        verbose_name_plural = _("feedback surveys")

    def __str__(self):
        return f"{self.trainee} – {self.training}"


# Modelo para la tabla intermedia de Course y Training
class CourseTraining(AutoOrderMixin):
    order_scope = "course"  # order = orden del training en el curso
    course = models.ForeignKey(
        "Course", on_delete=models.CASCADE, verbose_name=_("course")
    )
    training = models.ForeignKey(
        Training, on_delete=models.CASCADE, verbose_name=_("training")
    )

    class Meta:
        # Un training no puede repetirse en el mismo curso. order no es único: reordenar
        # intercambia posiciones y MariaDB no admite restricciones únicas diferidas
        unique_together = (("course", "training"),)
        # id desempata: la posición en el curso decide a qué training avanza el trainee
        ordering = ["order", "id"]
        verbose_name = _("training of the course")
        verbose_name_plural = _("trainings of the course")

    def __str__(self):
        # Sin el número de orden: al arrastrar filas el admin lo guarda desde 0 y la posición ya se muestra aparte
        return str(self.training)


# Modelo para Course
class Course(models.Model):
    class StateCourse(models.TextChoices):
        Active = "Active", _("Active")
        Inactive = "Inactive", _("Inactive")

    name_course = models.CharField(_("name"), max_length=200)
    description = models.CharField(_("description"), max_length=500)
    pub_date = models.DateTimeField(_("created"), auto_now_add=True)
    modification_date = models.DateTimeField(_("modified"), auto_now=True)
    state_course = models.CharField(
        _("status"),
        max_length=20,
        choices=StateCourse.choices,
        default=StateCourse.Active,
    )
    # Grupos que pueden acceder al curso (vacío = nadie lo ve, p. ej. mientras se prepara)
    groups = models.ManyToManyField(
        TraineeGroup,
        blank=True,
        related_name="courses",
        verbose_name=_("trainee groups"),
        help_text=_(
            "Only trainees in these groups see the course. "
            "Leave it empty while you prepare the course: nobody will see it."
        ),
    )
    trainings = models.ManyToManyField(
        Training,
        through=CourseTraining,
        related_name="courses",
        verbose_name=_("trainings"),
    )
    final_exam = models.ForeignKey(
        Training,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses_as_final_exam",
        verbose_name=_("final exam"),
        help_text=_(
            "Optional. It is unlocked after completing all the trainings of the course."
        ),
    )
    # Promedio mínimo requerido de los mejores scores de trainings para habilitar el examen final (por defecto 70%)
    required_average_score = models.DecimalField(
        _("average required for the final exam (%)"),
        max_digits=5,
        decimal_places=2,
        default=70.00,
        help_text=_(
            "Minimum average of the best scores in the course trainings to unlock the final exam."
        ),
    )
    # Porcentaje mínimo requerido para aprobar el examen final (por defecto 70%)
    final_exam_passing_score = models.DecimalField(
        _("final exam passing score (%)"),
        max_digits=5,
        decimal_places=2,
        default=70.00,
        help_text=_("Minimum score to pass the final exam."),
    )

    class Meta:
        verbose_name = _("course")
        verbose_name_plural = _("courses")

    def __str__(self):
        return self.name_course


@receiver(post_delete, sender=CourseTraining)
def reorder_course_trainings(sender, instance, **kwargs):
    course = instance.course
    trainings = course.coursetraining_set.order_by("order", "id")
    for i, ct in enumerate(trainings, 1):
        if ct.order != i:
            ct.order = i
            ct.save()


# Modelo para el progreso del trainee en un curso
class TraineeCourse(models.Model):
    class StateTraineeCourse(models.TextChoices):
        Not_Started = "Not Started", _("Not Started")
        In_Progress = "In Progress", _("In Progress")
        Completed = "Completed", _("Completed")
        Failed = "Failed", _("Failed")

    trainee = models.ForeignKey(
        Trainee, on_delete=models.CASCADE, verbose_name=_("trainee")
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, verbose_name=_("course")
    )
    state = models.CharField(
        _("status"),
        max_length=20,
        choices=StateTraineeCourse.choices,
        default=StateTraineeCourse.Not_Started,
    )
    current_training_index = models.PositiveIntegerField(
        _("current training (position)"), default=0
    )  # Índice del training actual habilitado
    exam_passed = models.BooleanField(_("final exam passed"), default=False)
    pub_date = models.DateTimeField(_("started"), auto_now_add=True)
    completion_date = models.DateTimeField(_("completed on"), null=True, blank=True)

    class Meta:
        unique_together = ("trainee", "course")
        verbose_name = _("progress in a course")
        verbose_name_plural = _("progress in courses")

    def __str__(self):
        return f"{self.trainee} – {self.course}"
