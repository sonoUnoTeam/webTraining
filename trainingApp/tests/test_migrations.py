"""
Migración de datos 0009_trainee_group_default: el grupo "Group Defect", que el signup usaba
para los usuarios nuevos, queda marcado como grupo por defecto.
"""

import contextlib
import io

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

MIGRATE_FROM = [("trainingApp", "0008_course_training_order_tiebreak")]
MIGRATE_TO = [("trainingApp", "0009_trainee_group_default")]


def migrate(targets):
    executor = MigrationExecutor(connection)
    with contextlib.redirect_stdout(io.StringIO()):
        executor.migrate(targets)
    return executor.loader.project_state(targets).apps


class TraineeGroupDefaultMigrationTests(TransactionTestCase):
    def tearDown(self):
        executor = MigrationExecutor(connection)
        with contextlib.redirect_stdout(io.StringIO()):
            executor.migrate(executor.loader.graph.leaf_nodes())

    def test_legacy_group_becomes_the_default(self):
        old_apps = migrate(MIGRATE_FROM)
        OldGroup = old_apps.get_model("trainingApp", "TraineeGroup")
        legacy = OldGroup.objects.create(name_group="Group Defect", description="")
        other = OldGroup.objects.create(name_group="Workshop", description="")

        new_apps = migrate(MIGRATE_TO)
        TraineeGroup = new_apps.get_model("trainingApp", "TraineeGroup")

        self.assertTrue(TraineeGroup.objects.get(pk=legacy.pk).is_default)
        self.assertFalse(TraineeGroup.objects.get(pk=other.pk).is_default)

    def test_without_legacy_group_no_group_is_marked(self):
        old_apps = migrate(MIGRATE_FROM)
        old_apps.get_model("trainingApp", "TraineeGroup").objects.create(
            name_group="Workshop", description=""
        )

        new_apps = migrate(MIGRATE_TO)
        TraineeGroup = new_apps.get_model("trainingApp", "TraineeGroup")

        self.assertFalse(TraineeGroup.objects.filter(is_default=True).exists())
