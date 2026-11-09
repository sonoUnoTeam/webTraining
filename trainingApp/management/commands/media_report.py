from django.core.management.base import BaseCommand

from trainingApp.media_audit import audit_media


class Command(BaseCommand):
    help = (
        "Read-only report of question images and sounds in MEDIA_ROOT: orphan files, "
        "copies with identical content and used paths missing on disk. Changes nothing."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            metavar="DIR",
            help="Also write the per-file detail (media_files.csv, media_missing.csv) to DIR.",
        )
        parser.add_argument(
            "--top", type=int, default=10, help="Most repeated contents to list."
        )

    def handle(self, *args, **options):
        audit = audit_media()
        for line in audit.summary_lines(top=options["top"]):
            self.stdout.write(line)
        if options["csv"]:
            for path in audit.write_csv(options["csv"]):
                self.stdout.write(f"Written: {path}")
