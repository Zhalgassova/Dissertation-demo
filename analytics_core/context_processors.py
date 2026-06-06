from .models import AnalysisDataset
from .services.demo_seed import REQUIRED_DATASETS, ensure_demo_ready_datasets
from .services.research_analytics import active_dataset_from_session


TEACHER_PRIORITY = {teacher_name: index for index, (teacher_name, _) in enumerate(REQUIRED_DATASETS)}
TEACHER_FALLBACKS = [
    {
        "teacher_name": teacher_name,
        "subject_title": subject_title,
    }
    for teacher_name, subject_title in REQUIRED_DATASETS
]


def latest_analysis_context(request):
    ensure_demo_ready_datasets()
    dataset = active_dataset_from_session(request)

    allowed_pairs = set(REQUIRED_DATASETS)
    teacher_datasets = [
        item
        for item in AnalysisDataset.objects.filter(status="ready").only(
            "id",
            "title",
            "teacher_name",
            "subject_title",
            "cohort_label",
            "created_at",
        )
        if (item.teacher_name or "", item.subject_title or "") in allowed_pairs
    ]
    teacher_datasets.sort(
        key=lambda item: (
            TEACHER_PRIORITY.get(item.teacher_name or "", 99),
            -item.id,
        )
    )

    if len(teacher_datasets) < len(REQUIRED_DATASETS):
        existing_keys = {
            (item.teacher_name or "", item.subject_title or item.title or "")
            for item in teacher_datasets
        }
        for fallback in TEACHER_FALLBACKS:
            key = (fallback["teacher_name"], fallback["subject_title"])
            if key not in existing_keys:
                teacher_datasets.append(
                    type(
                        "TeacherDatasetFallback",
                        (),
                        {
                            "id": 0,
                            "teacher_name": fallback["teacher_name"],
                            "subject_title": fallback["subject_title"],
                            "title": fallback["subject_title"],
                            "cohort_label": "",
                        },
                    )()
                )

    return {
        "active_analysis_dataset": dataset,
        "active_analysis_dataset_id": dataset.id if dataset else None,
        "teacher_datasets": teacher_datasets,
    }
