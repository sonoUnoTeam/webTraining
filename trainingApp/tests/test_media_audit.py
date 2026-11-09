"""Diagnóstico de solo lectura de las imágenes y sonidos de las preguntas (comando media_report)."""

import csv
import os
import shutil
import tempfile
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from trainingApp.media_audit import audit_media
from trainingApp.models import TrainingQuestion
from trainingApp.tests.factories import add_block, make_training


class MediaAuditTests(TestCase):

    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)
        media_override = override_settings(MEDIA_ROOT=self.media_root)
        media_override.enable()
        self.addCleanup(media_override.disable)
        self.block = add_block(make_training("T", blocks=0), "B", questions=0)

        self.write("trainingApp/sound/a.mp3", b"sound-a")
        self.write(
            "trainingApp/sound/a_X1y2Z3w.mp3", b"sound-a"
        )  # misma subida, otro nombre
        self.write("trainingApp/sound/b.mp3", b"sound-b")
        self.write("trainingApp/images/a.png", b"image-a")
        self.write(
            "trainingApp/images/old.png", b"image-old"
        )  # reemplazada, nadie la usa
        self.write("trainingApp/images/tutorial/seno.png", b"tutorial")

        # Dos preguntas comparten el sonido (como tras duplicar un training)
        self.first = self.question(
            "trainingApp/sound/a.mp3", "trainingApp/images/a.png"
        )
        self.second = self.question("trainingApp/sound/a.mp3")
        self.third = self.question("trainingApp/sound/missing.mp3")

    def write(self, relative, content):
        path = os.path.join(self.media_root, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(content)

    def question(self, sound, image=""):
        return TrainingQuestion.objects.create(
            block=self.block, question="Q", deploy_sound=sound, deploy_image=image
        )

    def test_orphans_exclude_used_and_tutorial_files(self):
        audit = audit_media()
        self.assertEqual(
            audit.orphans,
            [
                "trainingApp/images/old.png",
                "trainingApp/sound/a_X1y2Z3w.mp3",
                "trainingApp/sound/b.mp3",
            ],
        )
        self.assertNotIn("trainingApp/images/tutorial/seno.png", audit.sizes)

    def test_shared_paths_list_every_question(self):
        audit = audit_media()
        self.assertEqual(
            audit.shared, {"trainingApp/sound/a.mp3": [self.first.pk, self.second.pk]}
        )

    def test_identical_content_is_grouped_regardless_of_name(self):
        audit = audit_media()
        self.assertEqual(
            audit.duplicate_groups,
            [["trainingApp/sound/a.mp3", "trainingApp/sound/a_X1y2Z3w.mp3"]],
        )
        self.assertEqual(audit.redundant_copies(), 1)
        self.assertEqual(audit.redundant_bytes(), len(b"sound-a"))

    def test_missing_files_are_reported(self):
        self.assertEqual(audit_media().broken, ["trainingApp/sound/missing.mp3"])

    def test_size_after_cleanup_keeps_one_copy_of_used_content(self):
        self.assertEqual(
            audit_media().bytes_after_cleanup(), len(b"sound-a") + len(b"image-a")
        )

    def test_command_changes_nothing_and_writes_csv(self):
        csv_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, csv_dir, ignore_errors=True)
        before = sorted(
            os.path.join(dirpath, name)
            for dirpath, _dirs, names in os.walk(self.media_root)
            for name in names
        )
        out = StringIO()
        call_command("media_report", csv=csv_dir, stdout=out)

        output = out.getvalue()
        self.assertIn("Orphan files (no question uses them): 3", output)
        self.assertIn("Used paths missing on disk: 1", output)
        after = sorted(
            os.path.join(dirpath, name)
            for dirpath, _dirs, names in os.walk(self.media_root)
            for name in names
        )
        self.assertEqual(before, after)
        self.assertEqual(TrainingQuestion.objects.count(), 3)

        with open(os.path.join(csv_dir, "media_files.csv"), encoding="utf-8") as handle:
            rows = {row["path"]: row for row in csv.DictReader(handle)}
        self.assertEqual(rows["trainingApp/sound/a.mp3"]["same_content_copies"], "2")
        self.assertEqual(
            rows["trainingApp/sound/a.mp3"]["questions"],
            f"{self.first.pk} {self.second.pk}",
        )
        self.assertEqual(rows["trainingApp/images/old.png"]["questions"], "")
