from __future__ import annotations

import json
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(r"C:\Users\Admin\Documents\Codex\2026-04-20-new-chat-2-demo")
DB_PATH = PROJECT_ROOT / "db.sqlite3"
MEDIA_UPLOAD_DIR = PROJECT_ROOT / "media" / "analysis_uploads"


@dataclass
class DemoDatasetMeta:
    source_path: Path
    title: str
    teacher_name: str
    subject_title: str
    cohort_label: str
    email_prefix: str
    group_suffix: str
    lesson_topics: list[str]
    start_date: str


DATASETS = [
    DemoDatasetMeta(
        source_path=Path(r"C:\Users\Admin\Downloads\ais_dissertation_experiment_dataset.xlsx"),
        title="Автоматизированные информационные системы",
        teacher_name="Аширбекова Жанат",
        subject_title="Автоматизированные информационные системы",
        cohort_label="2 курс, орыс тобы",
        email_prefix="ais",
        group_suffix="группа",
        lesson_topics=[
            "Тема 1. Системы сигнализации на ТфОП",
            "Тема 2. Оконечные устройства телефонного тракта",
            "Тема 3. Принципы восприятия информации",
            "Тема 4. Принципы построения коммутационных полей аналоговых СК",
            "Тема 5. Устройства управления аналоговых АТС",
            "Тема 6. Устройства управления аналоговых АТС",
            "Тема 7. Цифровая передача сигналов",
            "Тема 8. Цифровая передача сигналов",
        ],
        start_date="2026-02-03",
    ),
    DemoDatasetMeta(
        source_path=Path(r"C:\Users\Admin\Downloads\instrumental_visual_communication_design_experiment.xlsx"),
        title="Инструментальные средства визуальной коммуникации и прикладной дизайн",
        teacher_name="Бекен Оралбай",
        subject_title="Инструментальные средства визуальной коммуникации и прикладной дизайн",
        cohort_label="3 курс",
        email_prefix="design",
        group_suffix="группа",
        lesson_topics=[
            "Тақырып 1. Основы визуальной коммуникации в современном дизайне",
            "Тақырып 2. Использование графических редакторов в прикладном дизайне",
            "Тақырып 3. Цвет и композиция как инструменты визуального восприятия",
            "Тақырып 4. Создание фирменного стиля и бренд-айдентики",
            "Тақырып 5. Типографика и её роль в визуальной коммуникации",
            "Тақырып 6. Дизайн цифровых интерфейсов: UX/UI основы",
            "Тақырып 7. Инфографика как средство передачи информации",
            "Тақырып 8. Искусственный интеллект в визуальной коммуникации и дизайне",
        ],
        start_date="2026-02-05",
    ),
    DemoDatasetMeta(
        source_path=Path(r"C:\Users\Admin\Downloads\discrete_higher_math_experiment_kazakh.xlsx"),
        title="Дискреттік және жоғарғы математика",
        teacher_name="Илесбекова Жанар",
        subject_title="Дискреттік және жоғарғы математика",
        cohort_label="2 курс, қазақ тобы",
        email_prefix="math",
        group_suffix="топ",
        lesson_topics=[
            "Тақырып 1. Тізбектің және функцияның шегі. Функцияның үзіліссіздігі, негізгі теоремалары, қасиеттері",
            "Тақырып 2. Бір айнымалыдан тәуелді функцияның туындысы және дифференциалы",
            "Тақырып 3. Дифференциал. Функцияның жоғарғы ретті туындысы мен дифференциалы",
            "Тақырып 4. Логарифм көмегімен дифференциалдау. Лопиталь ережесі",
            "Тақырып 5. Функцияны зерттеу және графигін салу",
            "Тақырып 6. Анықталмаған интеграл. Тікелей интегралдау",
            "Тақырып 7. Рационал бөлшектерді интегралдау",
            "Тақырып 8. Қарапайым иррационалды функцияларды интегралдау",
        ],
        start_date="2026-02-02",
    ),
]


def ensure_schema(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()
    cursor.execute("PRAGMA journal_mode=MEMORY")
    cursor.execute("PRAGMA synchronous=OFF")

    dataset_columns = {row[1] for row in cursor.execute("PRAGMA table_info(analytics_core_analysisdataset)")}
    for column_name, column_sql in [
        ("teacher_name", "ALTER TABLE analytics_core_analysisdataset ADD COLUMN teacher_name varchar(180) NOT NULL DEFAULT ''"),
        ("subject_title", "ALTER TABLE analytics_core_analysisdataset ADD COLUMN subject_title varchar(180) NOT NULL DEFAULT ''"),
        ("cohort_label", "ALTER TABLE analytics_core_analysisdataset ADD COLUMN cohort_label varchar(120) NOT NULL DEFAULT ''"),
    ]:
        if column_name not in dataset_columns:
            cursor.execute(column_sql)

    record_columns = {row[1] for row in cursor.execute("PRAGMA table_info(analytics_core_performancerecord)")}
    if "student_email" not in record_columns:
        cursor.execute(
            "ALTER TABLE analytics_core_performancerecord ADD COLUMN student_email varchar(254) NOT NULL DEFAULT ''"
        )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_core_teacherstudentcomment (
            id integer NOT NULL PRIMARY KEY AUTOINCREMENT,
            created_at datetime NOT NULL,
            updated_at datetime NOT NULL,
            student_name varchar(180) NOT NULL,
            student_email varchar(254) NOT NULL DEFAULT '',
            group_name varchar(120) NOT NULL DEFAULT '',
            comment text NOT NULL DEFAULT '',
            dataset_id bigint NOT NULL REFERENCES analytics_core_analysisdataset (id) DEFERRABLE INITIALLY DEFERRED,
            teacher_id integer NOT NULL REFERENCES auth_user (id) DEFERRABLE INITIALLY DEFERRED
        )
        """
    )
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS analytics_core_teacherstudentcomment_unique "
        "ON analytics_core_teacherstudentcomment (dataset_id, teacher_id, student_name)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS analytics_core_teacherstudentcomment_teacher_idx "
        "ON analytics_core_teacherstudentcomment (teacher_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS analytics_core_teacherstudentcomment_dataset_idx "
        "ON analytics_core_teacherstudentcomment (dataset_id)"
    )

    migration_exists = cursor.execute(
        "SELECT 1 FROM django_migrations WHERE app = ? AND name = ?",
        ("analytics_core", "0003_analysisdataset_context_teacherstudentcomment_and_email"),
    ).fetchone()
    if not migration_exists:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO django_migrations(app, name, applied) VALUES (?, ?, ?)",
            ("analytics_core", "0003_analysisdataset_context_teacherstudentcomment_and_email", now),
        )

    connection.commit()


def performance_level(score: float) -> str:
    if score < 50:
        return "low"
    if score < 75:
        return "medium"
    return "high"


def attendance_status(score: float) -> str:
    if score < 55:
        return "absent"
    if score < 70:
        return "late"
    return "present"


def build_group_name(group_value: str, academic_group: str, suffix: str) -> str:
    normalized = str(group_value or "").strip().lower()
    label = "Эксперимент" if "exp" in normalized else "Control"
    return f"{academic_group}-{suffix} / {label}"


def build_email(prefix: str, academic_group: str, row_id: int) -> str:
    return f"{prefix}.{academic_group}.{int(row_id):02d}@demo-college.kz"


def copy_source_file(source_path: Path) -> str:
    MEDIA_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    target_path = MEDIA_UPLOAD_DIR / source_path.name
    shutil.copy2(source_path, target_path)
    return f"analysis_uploads/{source_path.name}"


def build_detected_columns(frame: pd.DataFrame) -> dict:
    return {
        "mapped": {
            "student_name": "fio",
            "group_name": "group",
        },
        "available_columns": list(frame.columns),
        "file_type": "excel",
        "sheet_name": "Dataset",
    }


def seed_dataset(connection: sqlite3.Connection, meta: DemoDatasetMeta) -> None:
    cursor = connection.cursor()
    dataset_frame = pd.read_excel(meta.source_path, sheet_name="Dataset")
    detected_columns = build_detected_columns(dataset_frame)
    source_file_value = copy_source_file(meta.source_path)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
        INSERT INTO analytics_core_analysisdataset
        (created_at, updated_at, title, teacher_name, subject_title, cohort_label, original_filename,
         source_file, file_type, sheet_name, status, row_count, detected_columns, summary_json, notes, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            now,
            now,
            meta.title,
            meta.teacher_name,
            meta.subject_title,
            meta.cohort_label,
            meta.source_path.name,
            source_file_value,
            "excel",
            "Dataset",
            "ready",
            0,
            json.dumps(detected_columns, ensure_ascii=False),
            json.dumps({"seed_mode": "demo_ready"}, ensure_ascii=False),
            f"Дайын демо нәтижесі: {meta.subject_title}",
            "",
        ),
    )
    dataset_id = cursor.lastrowid

    lesson_dates = [datetime.fromisoformat(meta.start_date) + timedelta(days=7 * index) for index in range(8)]
    inserted_rows = 0
    for row_index, row in dataset_frame.iterrows():
        student_name = str(row["fio"]).strip()
        academic_group = str(row["academic_group"]).strip()
        group_name = build_group_name(str(row["group"]), academic_group, meta.group_suffix)
        student_email = build_email(meta.email_prefix, academic_group, int(row["id"]))
        for lesson_number, lesson_title in enumerate(meta.lesson_topics, start=1):
            lesson_date = lesson_dates[lesson_number - 1].strftime("%Y-%m-%d")
            for task_number in range(1, 4):
                score_value = float(row[f"L{lesson_number}_task{task_number}"])
                cursor.execute(
                    """
                    INSERT INTO analytics_core_performancerecord
                    (created_at, updated_at, dataset_id, student_name, student_email, group_name, subject_name,
                     lesson_topic, lesson_date, raw_score, max_score, percentage, attendance_status,
                     performance_level, source_row_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        now,
                        now,
                        dataset_id,
                        student_name,
                        student_email,
                        group_name,
                        meta.subject_title,
                        f"Сабақ {lesson_number}. {lesson_title} | Тапсырма {task_number}",
                        lesson_date,
                        score_value,
                        100.0,
                        score_value,
                        attendance_status(score_value),
                        performance_level(score_value),
                        row_index + 2,
                    ),
                )
                inserted_rows += 1

    cursor.execute(
        "UPDATE analytics_core_analysisdataset SET row_count = ?, updated_at = ? WHERE id = ?",
        (inserted_rows, now, dataset_id),
    )
    connection.commit()


def main() -> None:
    connection = sqlite3.connect(DB_PATH)
    ensure_schema(connection)
    cursor = connection.cursor()
    cursor.execute("DELETE FROM analytics_core_teacherstudentcomment")
    cursor.execute("DELETE FROM analytics_core_performancerecord")
    cursor.execute("DELETE FROM analytics_core_analysisdataset")
    connection.commit()

    for item in DATASETS:
        seed_dataset(connection, item)

    dataset_rows = cursor.execute(
        "SELECT id, title, teacher_name, subject_title, row_count FROM analytics_core_analysisdataset ORDER BY id"
    ).fetchall()
    print("Seed complete:")
    for row in dataset_rows:
        print(row)
    connection.close()


if __name__ == "__main__":
    main()
