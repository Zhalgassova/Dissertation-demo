from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path


DEMO_DB = Path(r"C:\Users\Admin\Documents\Codex\2026-04-20-new-chat-2-demo\db.sqlite3")
SOURCE_DB = Path(r"C:\Users\Admin\Documents\Codex\2026-04-20-new-chat-2\db.sqlite3")
SOURCE_MEDIA = Path(r"C:\Users\Admin\Documents\Codex\2026-04-20-new-chat-2\media")
DEMO_MEDIA = Path(r"C:\Users\Admin\Documents\Codex\2026-04-20-new-chat-2-demo\media")

TEACHER_NAME = "Алсу Жалгасова"
SUBJECT_TITLE = "Информатика"
COHORT_LABEL = "Диссертациялық эксперимент"
SOURCE_DATASET_ID = 83


def ensure_demo_dataset() -> int:
    demo_conn = sqlite3.connect(DEMO_DB)
    demo_cur = demo_conn.cursor()

    existing = demo_cur.execute(
        """
        SELECT id
        FROM analytics_core_analysisdataset
        WHERE teacher_name = ? AND subject_title = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (TEACHER_NAME, SUBJECT_TITLE),
    ).fetchone()
    if existing:
        demo_conn.close()
        return int(existing[0])

    src_conn = sqlite3.connect(SOURCE_DB)
    src_cur = src_conn.cursor()
    dataset_row = src_cur.execute(
        """
        SELECT original_filename, source_file, file_type, sheet_name, row_count,
               detected_columns, summary_json, notes
        FROM analytics_core_analysisdataset
        WHERE id = ?
        """,
        (SOURCE_DATASET_ID,),
    ).fetchone()
    if not dataset_row:
        raise RuntimeError("Алсу Жалгасова үшін бастапқы демо датасет табылмады.")

    original_filename, source_file, file_type, sheet_name, row_count, detected_columns, summary_json, notes = dataset_row

    source_path = SOURCE_MEDIA / source_file
    target_rel = Path("analysis_uploads") / f"demo_alsu_{Path(original_filename).name}"
    target_path = DEMO_MEDIA / target_rel
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path.exists() and not target_path.exists():
        shutil.copy2(source_path, target_path)

    demo_cur.execute(
        """
        INSERT INTO analytics_core_analysisdataset (
            created_at, updated_at, title, teacher_name, subject_title, cohort_label,
            original_filename, source_file, file_type, sheet_name, status, row_count,
            detected_columns, summary_json, notes, error_message
        ) VALUES (datetime('now'), datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, 'ready', ?, ?, ?, ?, '')
        """,
        (
            SUBJECT_TITLE,
            TEACHER_NAME,
            SUBJECT_TITLE,
            COHORT_LABEL,
            original_filename,
            str(target_rel).replace("\\", "/"),
            file_type or "excel",
            sheet_name or "",
            row_count or 0,
            detected_columns or "{}",
            summary_json or "{}",
            notes or "",
        ),
    )
    new_dataset_id = int(demo_cur.lastrowid)

    student_rows = src_cur.execute(
        """
        SELECT student_name, student_email, group_name, subject_name, lesson_topic, lesson_date,
               raw_score, max_score, percentage, attendance_status, performance_level, source_row_number
        FROM analytics_core_performancerecord
        WHERE dataset_id = ?
        ORDER BY id
        """,
        (SOURCE_DATASET_ID,),
    ).fetchall()

    email_map: dict[str, str] = {}
    student_counter = 1
    for row in student_rows:
        student_name = row[0]
        if student_name not in email_map:
            email_map[student_name] = row[1] or f"informatics.{student_counter:03d}@demo-college.kz"
            student_counter += 1

        demo_cur.execute(
            """
            INSERT INTO analytics_core_performancerecord (
                created_at, updated_at, dataset_id, student_name, student_email, group_name,
                subject_name, lesson_topic, lesson_date, raw_score, max_score, percentage,
                attendance_status, performance_level, source_row_number
            ) VALUES (datetime('now'), datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_dataset_id,
                student_name,
                email_map[student_name],
                row[2] or "",
                SUBJECT_TITLE,
                row[4] or "",
                row[5],
                row[6],
                row[7],
                row[8],
                row[9] or "unknown",
                row[10] or "medium",
                row[11] or 0,
            ),
        )

    demo_conn.commit()
    src_conn.close()
    demo_conn.close()
    return new_dataset_id


if __name__ == "__main__":
    dataset_id = ensure_demo_dataset()
    print(dataset_id)
