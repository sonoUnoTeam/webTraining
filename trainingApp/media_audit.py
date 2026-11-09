"""
Diagnóstico de los archivos subidos para las preguntas (imágenes y sonidos en MEDIA_ROOT).

Solo lee la base y el disco: no borra, no mueve ni modifica nada. Detecta archivos huérfanos
(ninguna pregunta los usa), copias con el mismo contenido y rutas usadas que no existen en disco.
Un mismo archivo puede estar en varias preguntas (por ejemplo, tras duplicar un training).
"""

import csv
import hashlib
import os
from collections import defaultdict
from dataclasses import dataclass, field

from django.conf import settings

from .models import TrainingQuestion

MEDIA_FOLDERS = ("trainingApp/images", "trainingApp/sound")
# Archivos de la página del tutorial: los usan las plantillas, no las preguntas
EXCLUDED_FOLDERS = ("trainingApp/images/tutorial", "trainingApp/sound/tutorial")


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def human_size(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def is_excluded(relative_dir):
    return any(
        relative_dir == folder or relative_dir.startswith(folder + "/")
        for folder in EXCLUDED_FOLDERS
    )


@dataclass
class MediaAudit:
    question_count: int = 0
    # ruta relativa a MEDIA_ROOT -> ids de las preguntas que la usan
    references: dict = field(default_factory=dict)
    # ruta relativa -> tamaño en bytes
    sizes: dict = field(default_factory=dict)
    # sha256 -> rutas con ese contenido
    by_hash: dict = field(default_factory=dict)

    @property
    def orphans(self):
        return sorted(set(self.sizes) - set(self.references))

    @property
    def broken(self):
        """Rutas que usa alguna pregunta pero no existen en disco."""
        root = settings.MEDIA_ROOT
        return sorted(
            path
            for path in self.references
            if not os.path.isfile(os.path.join(root, path))
        )

    @property
    def shared(self):
        """Rutas que ya usan varias preguntas (no deben borrarse al borrar una de ellas)."""
        return {path: ids for path, ids in self.references.items() if len(ids) > 1}

    @property
    def duplicate_groups(self):
        """Grupos de archivos con el mismo contenido, de mayor a menor cantidad de copias."""
        groups = [sorted(paths) for paths in self.by_hash.values() if len(paths) > 1]
        return sorted(groups, key=lambda paths: (-len(paths), paths[0]))

    def redundant_copies(self):
        return sum(len(paths) - 1 for paths in self.duplicate_groups)

    def redundant_bytes(self):
        return sum(
            self.sizes[paths[0]] * (len(paths) - 1) for paths in self.duplicate_groups
        )

    def orphan_bytes(self):
        return sum(self.sizes[path] for path in self.orphans)

    def total_bytes(self):
        return sum(self.sizes.values())

    def bytes_after_cleanup(self):
        """Lo que ocuparía el disco con un solo archivo por contenido usado y sin huérfanos."""
        return sum(
            self.sizes[paths[0]]
            for paths in self.by_hash.values()
            if any(path in self.references for path in paths)
        )

    def summary_lines(self, top=10):
        lines = [
            f"Questions: {self.question_count}",
            f"Files on disk (excluding tutorial/): {len(self.sizes)} ({human_size(self.total_bytes())})",
            f"Distinct paths used by questions: {len(self.references)}",
            f"  used by more than one question: {len(self.shared)}",
            f"Orphan files (no question uses them): {len(self.orphans)} ({human_size(self.orphan_bytes())})",
            (
                f"Groups of identical content: {len(self.duplicate_groups)}"
                f" -> redundant copies: {self.redundant_copies()}"
                f" ({human_size(self.redundant_bytes())})"
            ),
            f"Used paths missing on disk: {len(self.broken)}",
            f"Size after deduplicating and removing orphans: {human_size(self.bytes_after_cleanup())}",
        ]
        if self.duplicate_groups:
            lines.append("")
            lines.append(
                f"Top {top} most repeated contents (copies / used / first path):"
            )
            for paths in self.duplicate_groups[:top]:
                used = sum(path in self.references for path in paths)
                lines.append(f"  {len(paths):5d} {used:5d}  {paths[0]}")
        return lines

    def write_csv(self, directory):
        """Escribe el detalle por archivo y las rutas rotas; devuelve las rutas creadas."""
        os.makedirs(directory, exist_ok=True)
        hash_of = {
            path: digest for digest, paths in self.by_hash.items() for path in paths
        }
        files_path = os.path.join(directory, "media_files.csv")
        with open(files_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                ["path", "bytes", "sha256", "same_content_copies", "questions"]
            )
            for path in sorted(self.sizes):
                digest = hash_of[path]
                writer.writerow(
                    [
                        path,
                        self.sizes[path],
                        digest,
                        len(self.by_hash[digest]),
                        " ".join(map(str, self.references.get(path, []))),
                    ]
                )
        broken_path = os.path.join(directory, "media_missing.csv")
        with open(broken_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["path", "questions"])
            for path in self.broken:
                writer.writerow([path, " ".join(map(str, self.references[path]))])
        return [files_path, broken_path]


def question_references():
    references = defaultdict(list)
    for pk, image, sound in TrainingQuestion.objects.values_list(
        "pk", "deploy_image", "deploy_sound"
    ).order_by("pk"):
        for name in (image, sound):
            if name:
                references[name.replace("\\", "/")].append(pk)
    return dict(references)


def audit_media():
    root = settings.MEDIA_ROOT
    audit = MediaAudit(
        question_count=TrainingQuestion.objects.count(),
        references=question_references(),
    )
    by_hash = defaultdict(list)
    for folder in MEDIA_FOLDERS:
        for dirpath, _dirnames, filenames in os.walk(os.path.join(root, folder)):
            relative_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
            if is_excluded(relative_dir):
                continue
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                relative = f"{relative_dir}/{filename}"
                audit.sizes[relative] = os.path.getsize(full_path)
                by_hash[file_sha256(full_path)].append(relative)
    audit.by_hash = dict(by_hash)
    return audit
