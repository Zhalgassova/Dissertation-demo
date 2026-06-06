import shutil
import sqlite3
from pathlib import Path

from analytics_core.models import AnalysisDataset, PerformanceRecord


SOURCE_PROJECT_ROOT = Path(r"C:\Users\Admin\Documents\Codex\2026-04-20-new-chat-2-demo")
SOURCE_DB = SOURCE_PROJECT_ROOT / "db.sqlite3"
SOURCE_MEDIA_ROOT = SOURCE_PROJECT_ROOT / "media"
TARGET_MEDIA_ROOT = Path(r"C:\Users\Admin\Documents\Codex\Демо\media")
FALLBACK_SOURCE_PROJECT_ROOT = Path(r"C:\Users\Admin\Documents\Codex\2026-04-20-new-chat-2")
FALLBACK_SOURCE_DB = FALLBACK_SOURCE_PROJECT_ROOT / "db.sqlite3"
FALLBACK_SOURCE_MEDIA_ROOT = FALLBACK_SOURCE_PROJECT_ROOT / "media"

ALSU_DATASET_FALLBACK = {
    "teacher_name": "Алсу Жалгасова",
    "subject_title": "Информатика",
    "cohort_label": "Диссертациялық эксперимент",
    "source_dataset_id": 83,
}

REQUIRED_DATASETS = [
    ("Алсу Жалгасова", "Информатика"),
    ("Аширбекова Жанат", "Автоматизированные информационные системы"),
    ("Бекен Оралбай", "Инструментальные средства визуальной коммуникации и прикладной дизайн"),
    ("Илесбекова Жанар", "Дискреттік және жоғарғы математика"),
]


def _copy_media_file(source_file_value: str) -> str:
    if not source_file_value:
        return ""
    source_path = SOURCE_MEDIA_ROOT / source_file_value
    target_path = TARGET_MEDIA_ROOT / source_file_value
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path.exists() and not target_path.exists():
        shutil.copy2(source_path, target_path)
    return source_file_value.replace("\\", "/")


def _copy_media_file_from_root(source_file_value: str, media_root: Path) -> str:
    if not source_file_value:
        return ""
    source_path = media_root / source_file_value
    target_path = TARGET_MEDIA_ROOT / source_file_value
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path.exists() and not target_path.exists():
        shutil.copy2(source_path, target_path)
    return source_file_value.replace("\\", "/")


def _clone_dataset_from_primary_source(dataset_row, performance_rows):
    (
        _source_dataset_id,
        title,
        teacher_name,
        subject_title,
        cohort_label,
        original_filename,
        source_file,
        file_type,
        sheet_name,
        status,
        row_count,
        detected_columns,
        summary_json,
        notes,
        error_message,
    ) = dataset_row

    target_dataset = AnalysisDataset.objects.create(
        title=title,
        teacher_name=teacher_name,
        subject_title=subject_title,
        cohort_label=cohort_label or "",
        original_filename=original_filename or "",
        source_file=_copy_media_file(source_file or ""),
        file_type=file_type or "",
        sheet_name=sheet_name or "",
        status=status or "ready",
        row_count=row_count or 0,
        detected_columns=detected_columns or {},
        summary_json=summary_json or {},
        notes=notes or "",
        error_message=error_message or "",
    )

    batch = []
    for row in performance_rows:
        batch.append(
            PerformanceRecord(
                dataset=target_dataset,
                student_name=row[0] or "",
                student_email=row[1] or "",
                group_name=row[2] or "",
                subject_name=row[3] or "",
                lesson_topic=row[4] or "",
                lesson_date=row[5] or None,
                raw_score=row[6],
                max_score=row[7],
                percentage=row[8] or 0,
                attendance_status=row[9] or "unknown",
                performance_level=row[10] or "medium",
                source_row_number=row[11] or 0,
            )
        )

    if batch:
        PerformanceRecord.objects.bulk_create(batch, batch_size=500)
    return True


def _clone_alsu_from_fallback_source() -> bool:
    if not FALLBACK_SOURCE_DB.exists():
        return False

    connection = sqlite3.connect(FALLBACK_SOURCE_DB)
    cursor = connection.cursor()
    source_dataset_id = ALSU_DATASET_FALLBACK["source_dataset_id"]

    dataset_row = cursor.execute(
        """
        SELECT id, ?, ?, ?, original_filename, source_file, file_type, sheet_name,
               'ready', row_count, detected_columns, summary_json, notes, ''
        FROM analytics_core_analysisdataset
        WHERE id = ?
        """,
        (
            ALSU_DATASET_FALLBACK["subject_title"],
            ALSU_DATASET_FALLBACK["teacher_name"],
            ALSU_DATASET_FALLBACK["subject_title"],
            ALSU_DATASET_FALLBACK["cohort_label"],
            source_dataset_id,
        ),
    ).fetchone()

    if not dataset_row:
        connection.close()
        return False

    performance_rows = cursor.execute(
        """
        SELECT student_name, student_email, group_name, subject_name, lesson_topic, lesson_date,
               raw_score, max_score, percentage, attendance_status, performance_level, source_row_number
        FROM analytics_core_performancerecord
        WHERE dataset_id = ?
        ORDER BY id
        """,
        (source_dataset_id,),
    ).fetchall()

    (
        _source_dataset_id,
        title,
        teacher_name,
        subject_title,
        cohort_label,
        original_filename,
        source_file,
        file_type,
        sheet_name,
        status,
        row_count,
        detected_columns,
        summary_json,
        notes,
        error_message,
    ) = dataset_row

    target_dataset = AnalysisDataset.objects.create(
        title=title,
        teacher_name=teacher_name,
        subject_title=subject_title,
        cohort_label=cohort_label or "",
        original_filename=original_filename or "",
        source_file=_copy_media_file_from_root(source_file or "", FALLBACK_SOURCE_MEDIA_ROOT),
        file_type=file_type or "",
        sheet_name=sheet_name or "",
        status=status or "ready",
        row_count=row_count or 0,
        detected_columns=detected_columns or {},
        summary_json=summary_json or {},
        notes=notes or "",
        error_message=error_message or "",
    )

    email_map = {}
    student_counter = 1
    batch = []
    for row in performance_rows:
        student_name = row[0] or ""
        if student_name not in email_map:
            email_map[student_name] = row[1] or f"informatics.{student_counter:03d}@demo-college.kz"
            student_counter += 1
        batch.append(
            PerformanceRecord(
                dataset=target_dataset,
                student_name=student_name,
                student_email=email_map[student_name],
                group_name=row[2] or "",
                subject_name=subject_title,
                lesson_topic=row[4] or "",
                lesson_date=row[5] or None,
                raw_score=row[6],
                max_score=row[7],
                percentage=row[8] or 0,
                attendance_status=row[9] or "unknown",
                performance_level=row[10] or "medium",
                source_row_number=row[11] or 0,
            )
        )

    if batch:
        PerformanceRecord.objects.bulk_create(batch, batch_size=500)

    connection.close()
    return True


def _clone_dataset_from_source(teacher_name: str, subject_title: str) -> bool:
    if not SOURCE_DB.exists():
        return False

    connection = sqlite3.connect(SOURCE_DB)
    cursor = connection.cursor()

    dataset_row = cursor.execute(
        """
        SELECT id, title, teacher_name, subject_title, cohort_label, original_filename,
               source_file, file_type, sheet_name, status, row_count, detected_columns,
               summary_json, notes, error_message
        FROM analytics_core_analysisdataset
        WHERE teacher_name = ? AND subject_title = ? AND status = 'ready'
        ORDER BY id DESC
        LIMIT 1
        """,
        (teacher_name, subject_title),
    ).fetchone()

    if not dataset_row:
        connection.close()
        if (
            teacher_name == ALSU_DATASET_FALLBACK["teacher_name"]
            and subject_title == ALSU_DATASET_FALLBACK["subject_title"]
        ):
            return _clone_alsu_from_fallback_source()
        return False

    performance_rows = cursor.execute(
        """
        SELECT student_name, student_email, group_name, subject_name, lesson_topic, lesson_date,
               raw_score, max_score, percentage, attendance_status, performance_level, source_row_number
        FROM analytics_core_performancerecord
        WHERE dataset_id = ?
        ORDER BY id
        """,
        (source_dataset_id,),
    ).fetchall()
    _clone_dataset_from_primary_source(dataset_row, performance_rows)
    connection.close()
    return True


def ensure_demo_ready_datasets():
    existing = set(
        AnalysisDataset.objects.filter(status="ready").values_list("teacher_name", "subject_title")
    )
    for teacher_name, subject_title in REQUIRED_DATASETS:
        if (teacher_name, subject_title) not in existing:
            created = _clone_dataset_from_source(teacher_name, subject_title)
            if created:
                existing.add((teacher_name, subject_title))
