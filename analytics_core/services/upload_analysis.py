import math
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from django.db import transaction

from analytics_core.models import AnalysisDataset, PerformanceRecord


COLUMN_ALIASES = {
    'student_name': [
        'student', 'student name', 'name', 'full name', 'fio', 'student_name', 'full_name',
        '�?���', '�?��� ���', '�������', '������� ���', '��� �?�', '��� ����',
        '���', '���', '���-�?�',
    ],
    'group_name': [
        'group', 'group name', 'class', 'class name', 'group_name', 'experimental group',
        '���', '��� �����', '�����', '������', '�����', '������������� ���', '��?���� ����',
    ],
    'subject_name': [
        'subject', 'course', 'discipline', 'lesson', 'subject_name', 'module',
        '�?�', '����?', '�������', '����������', '����',
    ],
    'lesson_topic': [
        'topic', 'theme', 'unit', 'chapter', 'lesson topic', 'lesson_theme',
        '��?����', '����', '����? ��?�����', '�����',
    ],
    'lesson_date': [
        'date', 'day', 'lesson date', 'lesson_date',
        '�?�', '����', '����? �?�', 'lesson day',
    ],
    'score': [
        'score', 'grade', 'result', 'points', 'point', 'mark', 'score value',
        '����', '��?�', '������', '���������', '?���',
    ],
    'max_score': [
        'max score', 'maximum', 'total', 'max', 'out of', 'possible score',
        '����', '��������', '���� ����', '������������ ����', '�����?�',
    ],
    'percentage': [
        'percent', 'percentage', 'percentage score', 'result percent',
        '�����', '�������', '?���', 'score_percent',
    ],
    'attendance_status': [
        'attendance', 'attendance status', 'presence', 'participation', 'visited',
        '?�����', '?������', '?������', '���������', '�����������', '������',
    ],
}

WEEK_ALIASES = r'(?:week|w|����|������)'
LESSON_ALIASES = r'(?:lesson|les|����?|����)'
TASK_ALIASES = r'(?:task|tsk|��������|�������)'


def _sanitize_column(name):
    cleaned = re.sub(r'[\W_]+', ' ', str(name).strip().lower(), flags=re.UNICODE)
    return re.sub(r'\s+', ' ', cleaned).strip()


def _best_match(columns, aliases, used_columns):
    winner = None
    best_score = 0
    for column in columns:
        if column in used_columns:
            continue
        sanitized = _sanitize_column(column)
        for alias in aliases:
            alias_clean = _sanitize_column(alias)
            score = 0
            if sanitized == alias_clean:
                score = 100
            elif alias_clean and alias_clean in sanitized:
                score = 75
            elif sanitized and sanitized in alias_clean:
                score = 60
            else:
                alias_parts = alias_clean.split()
                if alias_parts and all(part in sanitized for part in alias_parts):
                    score = 50
            if score > best_score:
                best_score = score
                winner = column
    return winner


def detect_column_mapping(columns):
    mapping = {}
    used = set()
    for target, aliases in COLUMN_ALIASES.items():
        match = _best_match(columns, aliases, used)
        if match:
            mapping[target] = match
            used.add(match)
    return mapping


def _flatten_columns(columns):
    flattened = []
    for column in columns:
        if isinstance(column, tuple):
            parts = []
            for level in column:
                text = str(level).strip()
                if not text or text.lower().startswith('unnamed'):
                    continue
                parts.append(text)
            flattened.append(' | '.join(parts) if parts else 'Unnamed')
        else:
            flattened.append(str(column).strip())
    return flattened


def _is_poor_header(columns):
    if not columns:
        return False
    unnamed = sum(1 for column in columns if 'unnamed' in str(column).lower())
    return unnamed / max(len(columns), 1) > 0.25


def _load_excel_sheet(file_path):
    base_sheets = pd.read_excel(file_path, sheet_name=None)
    cleaned_sheets = {
        name: df.dropna(axis=1, how='all').dropna(how='all') for name, df in base_sheets.items()
    }
    non_empty = {name: df for name, df in cleaned_sheets.items() if not df.empty}
    if not non_empty:
        raise ValueError('Excel ����� ��� ������ ������ ������?� ������� ����? ��?.')

    selected_name, selected_df = max(
        non_empty.items(),
        key=lambda item: (len(item[1].index), len(item[1].columns)),
    )
    selected_columns = [str(column) for column in selected_df.columns]

    if _is_poor_header(selected_columns):
        for depth in (3, 2):
            try:
                multi_header = pd.read_excel(file_path, sheet_name=selected_name, header=list(range(depth)))
            except Exception:
                continue
            multi_header = multi_header.dropna(axis=1, how='all').dropna(how='all')
            if multi_header.empty:
                continue
            flat_columns = _flatten_columns(list(multi_header.columns))
            if not _is_poor_header(flat_columns):
                multi_header.columns = flat_columns
                return multi_header.reset_index(drop=True), selected_name

    selected_df.columns = [str(column).strip() for column in selected_df.columns]
    return selected_df.reset_index(drop=True), selected_name


def load_dataframe(file_path):
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()
    if suffix == '.csv':
        for encoding in ('utf-8-sig', 'utf-8', 'cp1251', 'latin1'):
            try:
                frame = pd.read_csv(file_path, encoding=encoding, sep=None, engine='python')
                return frame, {'file_type': 'csv', 'sheet_name': 'CSV'}
            except Exception:
                continue
        raise ValueError('CSV ������ �?� �?��� �������. ����������� ������ ��?�� �������� �������� ����� �?���.')

    if suffix in {'.xlsx', '.xlsm', '.xls'}:
        try:
            frame, sheet_name = _load_excel_sheet(file_path)
            return frame, {'file_type': 'excel', 'sheet_name': sheet_name}
        except Exception as exc:
            raise ValueError(
                'Excel ������ �?� �?��� �������. ���� ??������� ������ .xlsx �������� ������� �?�?��.'
            ) from exc

    raise ValueError('?����� �?���������� ���� �������.')


def _series_or_default(frame, column_name, default_value=''):
    if not column_name:
        return pd.Series([default_value] * len(frame), index=frame.index)
    return frame[column_name].fillna(default_value)


def _coerce_numeric(series):
    return pd.to_numeric(series, errors='coerce')


def _coerce_date(series):
    if series is None:
        return pd.Series([pd.NaT] * 0)
    return pd.to_datetime(series, errors='coerce', dayfirst=True)


def _normalize_attendance(value):
    if pd.isna(value):
        return 'unknown'
    text = str(value).strip().lower()
    if not text:
        return 'unknown'
    if text in {'1', 'true', 'yes', 'present', '?������', '?����?��', '���', '+'}:
        return 'present'
    if text in {'late', '������', '�������'}:
        return 'late'
    if text in {'0', 'false', 'no', 'absent', '?��������', '��?', '-', '������������'}:
        return 'absent'
    if '?����' in text or 'present' in text or '���������' in text:
        return 'present'
    if '���' in text or 'late' in text or '�����' in text:
        return 'late'
    if '��?' in text or 'absent' in text or '�����' in text:
        return 'absent'
    return 'unknown'


def _derive_percentage(score_series, max_series=None, percent_series=None):
    if percent_series is not None and percent_series.notna().any():
        values = percent_series.astype(float).copy()
        if values.dropna().le(1).all():
            values = values * 100
        return values.clip(lower=0, upper=100)

    scores = score_series.astype(float) if score_series is not None else pd.Series(dtype=float)
    if max_series is not None and max_series.notna().any():
        denominator = max_series.astype(float).replace(0, np.nan)
        result = scores.divide(denominator) * 100
        return result.clip(lower=0, upper=100)

    if scores.empty:
        return scores

    observed_max = scores.dropna().quantile(0.95) if scores.dropna().size else 100
    if observed_max <= 5:
        denominator = 5.0
    elif observed_max <= 10:
        denominator = 10.0
    else:
        denominator = 100.0
    return (scores / denominator * 100).clip(lower=0, upper=100)


def _performance_level(value):
    if value < 50:
        return 'low'
    if value < 75:
        return 'medium'
    return 'high'


def _status_label(value):
    return {'low': '�?���', 'medium': '������', 'high': '��?���'}.get(value, '������')


def _extract_digits(text):
    return [int(item) for item in re.findall(r'\d+', text)]


def _parse_wide_task_column(column_name):
    text = _sanitize_column(column_name)
    if not re.search(TASK_ALIASES, text):
        return None

    week = None
    lesson = None
    task = None

    week_match = re.search(rf'{WEEK_ALIASES}\s*(\d+)', text)
    lesson_match = re.search(rf'{LESSON_ALIASES}\s*(\d+)', text)
    task_match = re.search(rf'{TASK_ALIASES}\s*(\d+)', text)

    if week_match:
        week = int(week_match.group(1))
    if lesson_match:
        lesson = int(lesson_match.group(1))
    if task_match:
        task = int(task_match.group(1))

    digits = _extract_digits(text)
    if task is None and digits:
        task = digits[-1]
    if lesson is None and len(digits) >= 2:
        lesson = digits[-2]
    if week is None:
        if len(digits) >= 3:
            week = digits[0]
        elif lesson is not None:
            week = lesson

    if lesson is None or task is None:
        return None

    return {
        'column': column_name,
        'week_index': week or lesson,
        'lesson_index': lesson,
        'task_index': task,
    }


def detect_wide_task_columns(columns, ignored=None):
    ignored = ignored or set()
    detected = []
    for column in columns:
        if column in ignored:
            continue
        parsed = _parse_wide_task_column(column)
        if parsed:
            detected.append(parsed)
    detected.sort(key=lambda item: (item['week_index'], item['lesson_index'], item['task_index']))
    return detected


def normalize_long_dataset(raw_frame, mapping):
    frame = raw_frame.copy()
    frame.columns = [str(column).strip() for column in frame.columns]
    frame = frame.dropna(axis=1, how='all').dropna(how='all').reset_index(drop=True)
    if frame.empty:
        raise ValueError('������ ������?� ������� ������ ���������.')

    student_series = _series_or_default(frame, mapping.get('student_name'), '').astype(str).str.strip()
    group_series = _series_or_default(frame, mapping.get('group_name'), '������ ���').astype(str).str.strip()
    subject_series = _series_or_default(frame, mapping.get('subject_name'), '����������� �?�').astype(str).str.strip()
    topic_series = _series_or_default(frame, mapping.get('lesson_topic'), '����� ��?����').astype(str).str.strip()
    date_series = _coerce_date(frame[mapping['lesson_date']]) if mapping.get('lesson_date') else pd.Series(
        [pd.NaT] * len(frame), index=frame.index
    )
    score_series = _coerce_numeric(frame[mapping['score']]) if mapping.get('score') else None
    max_series = _coerce_numeric(frame[mapping['max_score']]) if mapping.get('max_score') else None
    percent_series = _coerce_numeric(frame[mapping['percentage']]) if mapping.get('percentage') else None
    percentage_series = _derive_percentage(score_series, max_series, percent_series)
    attendance_source = _series_or_default(frame, mapping.get('attendance_status'), 'unknown')
    attendance_series = attendance_source.map(_normalize_attendance)

    normalized = pd.DataFrame(
        {
            'student_name': student_series.replace('', np.nan),
            'group_name': group_series.replace('', '������ ���'),
            'subject_name': subject_series.replace('', '����������� �?�'),
            'lesson_topic': topic_series.replace('', '����� ��?����'),
            'lesson_date': date_series,
            'session_label': date_series.dt.strftime('%Y-%m-%d').fillna(topic_series.replace('', '����?')),
            'raw_score': score_series if score_series is not None else np.nan,
            'max_score': max_series if max_series is not None else np.nan,
            'percentage': percentage_series,
            'attendance_status': attendance_series,
            'week_index': np.nan,
            'lesson_index': np.nan,
            'task_index': np.nan,
        }
    )
    normalized['source_row_number'] = normalized.index + 2
    normalized = normalized.dropna(subset=['student_name', 'percentage']).reset_index(drop=True)
    if normalized.empty:
        raise ValueError('������� ��� ��� �?���� ��?������� ���?��� �?��� �������.')
    normalized['performance_level'] = normalized['percentage'].apply(_performance_level)
    normalized['date_label'] = normalized['session_label']
    normalized['format_type'] = 'long'
    return normalized


def normalize_wide_dataset(raw_frame, mapping, wide_columns):
    frame = raw_frame.copy()
    frame.columns = [str(column).strip() for column in frame.columns]
    frame = frame.dropna(axis=1, how='all').dropna(how='all').reset_index(drop=True)
    if frame.empty:
        raise ValueError('������ ������?� ������� ����� ��?.')

    student_series = _series_or_default(frame, mapping.get('student_name'), '').astype(str).str.strip()
    group_series = _series_or_default(frame, mapping.get('group_name'), '������ ���').astype(str).str.strip()
    subject_series = _series_or_default(frame, mapping.get('subject_name'), '����������� �?�').astype(str).str.strip()
    attendance_source = _series_or_default(frame, mapping.get('attendance_status'), 'unknown')
    attendance_series = attendance_source.map(_normalize_attendance)

    rows = []
    for meta in wide_columns:
        numeric_scores = _coerce_numeric(frame[meta['column']])
        session_label = f"���� {meta['week_index']}, ����? {meta['lesson_index']}"
        lesson_topic = f"���� {meta['week_index']}, ����? {meta['lesson_index']}, �������� {meta['task_index']}"
        chunk = pd.DataFrame(
            {
                'student_name': student_series,
                'group_name': group_series.replace('', '������ ���'),
                'subject_name': subject_series.replace('', '����������� �?�'),
                'lesson_topic': lesson_topic,
                'lesson_date': pd.Series([pd.NaT] * len(frame), index=frame.index),
                'session_label': session_label,
                'raw_score': numeric_scores,
                'max_score': pd.Series([np.nan] * len(frame), index=frame.index),
                'attendance_status': attendance_series,
                'week_index': meta['week_index'],
                'lesson_index': meta['lesson_index'],
                'task_index': meta['task_index'],
            }
        )
        chunk['source_row_number'] = chunk.index + 2
        rows.append(chunk)

    if not rows:
        raise ValueError('��? ��������?� �������� ��?������ ���������.')

    normalized = pd.concat(rows, ignore_index=True)
    normalized = normalized.dropna(subset=['student_name', 'raw_score']).reset_index(drop=True)
    if normalized.empty:
        raise ValueError('�������� ��?��������� �����? ��?���� ���������.')

    normalized['percentage'] = _derive_percentage(normalized['raw_score'])
    normalized['performance_level'] = normalized['percentage'].apply(_performance_level)
    normalized['date_label'] = normalized['session_label']
    normalized['format_type'] = 'wide'
    return normalized


def normalize_dataset_frame(raw_frame, mapping):
    ignored = set(mapping.values())
    wide_columns = detect_wide_task_columns(list(raw_frame.columns), ignored=ignored)
    if len(wide_columns) >= 6 and not mapping.get('score') and not mapping.get('percentage'):
        normalized = normalize_wide_dataset(raw_frame, mapping, wide_columns)
        return normalized, 'wide'
    normalized = normalize_long_dataset(raw_frame, mapping)
    return normalized, 'long'


def _clamp(value, lower=0, upper=100):
    return max(lower, min(upper, round(float(value), 2)))


def _safe_float(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return 0.0
    return round(float(value), 2)


def _json_safe(value):
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return _safe_float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _welch_comparison(left_values, right_values, left_label, right_label):
    if len(left_values) < 2 or len(right_values) < 2:
        return {
            'left_label': left_label,
            'right_label': right_label,
            'left_mean': _safe_float(np.mean(left_values) if len(left_values) else 0),
            'right_mean': _safe_float(np.mean(right_values) if len(right_values) else 0),
            'p_value': None,
            'effect_size': None,
            'interpretation': '��������� ?��� ����� ��������.',
        }

    left = np.array(left_values, dtype=float)
    right = np.array(right_values, dtype=float)
    observed = abs(left.mean() - right.mean())
    pooled = np.concatenate([left, right])
    left_size = len(left)
    rng = np.random.default_rng(42)
    exceed_count = 0
    iterations = 2000
    for _ in range(iterations):
        shuffled = rng.permutation(pooled)
        diff = abs(shuffled[:left_size].mean() - shuffled[left_size:].mean())
        if diff >= observed:
            exceed_count += 1
    p_value = (exceed_count + 1) / (iterations + 1)

    left_var = left.var(ddof=1)
    right_var = right.var(ddof=1)
    pooled_std = math.sqrt(
        ((len(left) - 1) * left_var + (len(right) - 1) * right_var) / (len(left) + len(right) - 2)
    )
    effect_size = 0.0 if pooled_std == 0 else (left.mean() - right.mean()) / pooled_std
    effect_abs = abs(effect_size)
    if effect_abs >= 0.8:
        interpretation = '����������? ?���� �?�� ������������? �?�?���� ��?����.'
    elif effect_abs >= 0.5:
        interpretation = '����������? ������ ��?����� ���?�����.'
    elif effect_abs >= 0.2:
        interpretation = '����������? ��?��, ���? ����� ������?� ������.'
    else:
        interpretation = '����������? ?���, ������ ��-���� ��?��.'

    return {
        'left_label': left_label,
        'right_label': right_label,
        'left_mean': _safe_float(left.mean()),
        'right_mean': _safe_float(right.mean()),
        'p_value': round(p_value, 4),
        'effect_size': round(effect_size, 3),
        'interpretation': interpretation,
    }


def _build_group_comparison(frame):
    grouped = frame.groupby('group_name')['percentage'].agg(['mean', 'count']).sort_values(
        by=['count', 'mean'], ascending=[False, False]
    )
    if len(grouped.index) >= 2:
        left_label, right_label = grouped.index[0], grouped.index[1]
        left_values = frame.loc[frame['group_name'] == left_label, 'percentage'].tolist()
        right_values = frame.loc[frame['group_name'] == right_label, 'percentage'].tolist()
        comparison = _welch_comparison(left_values, right_values, left_label, right_label)
        comparison['basis'] = '�� �����? ������ �?������ ���������'
        return comparison

    lessons = frame.groupby('session_label')['percentage'].agg(['mean', 'count']).sort_values(
        by=['count', 'mean'], ascending=[False, False]
    )
    if len(lessons.index) >= 2:
        left_label, right_label = lessons.index[0], lessons.index[1]
        left_values = frame.loc[frame['session_label'] == left_label, 'percentage'].tolist()
        right_values = frame.loc[frame['session_label'] == right_label, 'percentage'].tolist()
        comparison = _welch_comparison(left_values, right_values, left_label, right_label)
        comparison['basis'] = '�� ����?/������ �?������ ���������'
        return comparison

    comparison = _welch_comparison([], [], '1-���', '2-���')
    comparison['basis'] = '��������� �?��� �������'
    return comparison


def _level_counts(frame):
    counts = Counter(frame['performance_level'])
    return [counts.get('low', 0), counts.get('medium', 0), counts.get('high', 0)]


def _student_risk_table(frame):
    attendance_numeric = frame['attendance_status'].map(
        {'present': 100, 'late': 75, 'absent': 0, 'unknown': np.nan}
    )
    enriched = frame.copy()
    enriched['attendance_numeric'] = attendance_numeric
    grouped = (
        enriched.groupby(['student_name', 'group_name'])
        .agg(
            avg_score=('percentage', 'mean'),
            score_std=('percentage', 'std'),
            task_count=('percentage', 'count'),
            attendance_rate=('attendance_numeric', 'mean'),
        )
        .reset_index()
    )
    grouped['score_std'] = grouped['score_std'].fillna(0)
    grouped['attendance_rate'] = grouped['attendance_rate'].fillna(70)
    grouped['risk_score'] = grouped.apply(
        lambda row: _clamp(
            (100 - row['avg_score']) * 0.62
            + row['score_std'] * 0.18
            + (100 - row['attendance_rate']) * 0.20
        ),
        axis=1,
    )
    grouped['status_label'] = grouped['avg_score'].apply(
        lambda value: '�?���' if value < 50 else '������' if value < 75 else '��?���'
    )

    weakest_sessions = (
        enriched.groupby(['student_name', 'session_label'])['percentage']
        .mean()
        .reset_index()
        .sort_values(by=['student_name', 'percentage'])
        .drop_duplicates(subset=['student_name'], keep='first')
    )
    weakest_topics = (
        enriched.groupby(['student_name', 'lesson_topic'])['percentage']
        .mean()
        .reset_index()
        .sort_values(by=['student_name', 'percentage'])
        .drop_duplicates(subset=['student_name'], keep='first')
    )
    grouped = grouped.merge(weakest_sessions[['student_name', 'session_label']], on='student_name', how='left')
    grouped = grouped.merge(weakest_topics[['student_name', 'lesson_topic']], on='student_name', how='left')
    return grouped.sort_values(by=['risk_score', 'avg_score'], ascending=[False, True]).reset_index(drop=True)


def _chart_record(chart_id, title, chart_type, subtitle, **payload):
    data = {'id': chart_id, 'title': title, 'type': chart_type, 'subtitle': subtitle}
    data.update(payload)
    return data


def _build_charts(frame, student_risk, comparison, prepost_metrics):
    histogram_bins = pd.cut(
        frame['percentage'],
        bins=[0, 20, 40, 60, 80, 100],
        labels=['0-20', '21-40', '41-60', '61-80', '81-100'],
        include_lowest=True,
    )
    histogram = histogram_bins.value_counts().sort_index()

    group_mean = frame.groupby('group_name')['percentage'].mean().sort_values(ascending=False).head(8)
    session_mean = frame.groupby('session_label')['percentage'].mean().sort_values(ascending=False)
    weak_topics = frame.groupby('lesson_topic')['percentage'].mean().sort_values().head(8)
    strong_topics = frame.groupby('lesson_topic')['percentage'].mean().sort_values(ascending=False).head(8)
    top_risk = student_risk.head(8)
    group_level = frame.groupby('group_name')['performance_level'].value_counts().unstack(fill_value=0)
    mean_std = (
        frame.groupby(['student_name', 'group_name'])['percentage']
        .agg(['mean', 'std'])
        .fillna(0)
        .sort_values('mean')
        .tail(12)
    )

    task_stats = frame.groupby('task_index')['percentage'].mean().dropna().sort_index()
    if task_stats.empty:
        task_stats = pd.Series([frame['percentage'].mean()], index=['�����? ��������'])

    if 'task_index' in frame.columns:
        task_heatmap = frame.pivot_table(
            index='group_name',
            columns='task_index',
            values='percentage',
            aggfunc='mean',
            fill_value=0,
        )
    else:
        task_heatmap = pd.DataFrame()
    if task_heatmap.empty:
        task_heatmap = pd.DataFrame([[frame['percentage'].mean()]], index=['�����? ���'], columns=['�����? ��������'])

    lesson_progress = frame.groupby('session_label')['percentage'].mean()
    if 'lesson_index' in frame.columns and frame['lesson_index'].notna().any():
        lesson_progress = (
            frame.groupby(['week_index', 'lesson_index', 'session_label'])['percentage']
            .mean()
            .reset_index()
            .sort_values(by=['week_index', 'lesson_index'])
            .set_index('session_label')['percentage']
        )

    heatmap_table = frame.pivot_table(
        index='group_name',
        columns='session_label',
        values='percentage',
        aggfunc='mean',
        fill_value=0,
    )
    if heatmap_table.shape[1] > 8:
        heatmap_table = heatmap_table.iloc[:, :8]

    prepost_pairs = prepost_metrics.get('group_pairs', [])
    prepost_labels = [pair['group_name'] for pair in prepost_pairs]
    pre_values = [pair['pre_value'] for pair in prepost_pairs]
    post_values = [pair['post_value'] for pair in prepost_pairs]
    gain_values = [pair['gain'] for pair in prepost_pairs]

    session_risk = (
        frame.assign(is_low=frame['performance_level'].eq('low').astype(int))
        .groupby('session_label')['is_low']
        .sum()
    )
    if 'lesson_index' in frame.columns and frame['lesson_index'].notna().any():
        session_risk = (
            frame.assign(is_low=frame['performance_level'].eq('low').astype(int))
            .groupby(['week_index', 'lesson_index', 'session_label'])['is_low']
            .sum()
            .reset_index()
            .sort_values(by=['week_index', 'lesson_index'])
            .set_index('session_label')['is_low']
        )

    group_topic_gap = (
        frame.groupby(['group_name', 'lesson_topic'])['percentage']
        .mean()
        .reset_index()
        .sort_values(by=['group_name', 'percentage'])
        .groupby('group_name')
        .head(1)
    )

    by_student = frame.groupby(['student_name', 'group_name', 'session_label'])['percentage'].mean().reset_index()
    if prepost_pairs:
        pre_label = prepost_metrics.get('pre_label')
        post_label = prepost_metrics.get('post_label')
        pre_students = by_student[by_student['session_label'] == pre_label][['student_name', 'group_name', 'percentage']].rename(
            columns={'percentage': 'pre_score'}
        )
        post_students = by_student[by_student['session_label'] == post_label][['student_name', 'group_name', 'percentage']].rename(
            columns={'percentage': 'post_score'}
        )
        gain_scatter = pre_students.merge(post_students, on=['student_name', 'group_name'], how='inner')
        gain_scatter['gain'] = gain_scatter['post_score'] - gain_scatter['pre_score']
    else:
        gain_scatter = pd.DataFrame(columns=['student_name', 'group_name', 'pre_score', 'gain'])

    charts = [
        _chart_record(
            'score-distribution',
            '�?��������? �������',
            'bar',
            '��?������? �������� ������� �?���',
            labels=list(histogram.index.astype(str)),
            values=[int(value) for value in histogram.tolist()],
        ),
        _chart_record(
            'performance-levels',
            '?����� ��?������',
            'doughnut',
            '�?���, ������ �?�� ��?��� ��?������ ����������? ?���',
            labels=['�?���', '������', '��?���'],
            values=_level_counts(frame),
        ),
        _chart_record(
            'group-mean',
            '�� �����? ������ �?�������',
            'bar',
            '����������� �?�� ��?���� ������? �?�����',
            labels=list(group_mean.index),
            values=[_safe_float(value) for value in group_mean.tolist()],
        ),
        _chart_record(
            'prepost-groups',
            'Pre-test �?�� Post-test',
            'multibar',
            f"{prepost_metrics.get('pre_label', '������?�')} ��� {prepost_metrics.get('post_label', '��??�')} �?�������� ���������",
            labels=prepost_labels,
            series=[
                {'name': 'Pre-test', 'values': pre_values},
                {'name': 'Post-test', 'values': post_values},
            ],
        ),
        _chart_record(
            'lesson-progress',
            '8 ����? ������� ��������',
            'line',
            '?� ����?/���� ������� ������ �?����',
            labels=list(lesson_progress.index),
            values=[_safe_float(value) for value in lesson_progress.tolist()],
        ),
        _chart_record(
            'task-average',
            '3 �������� ������� ������ �?����',
            'bar',
            '?� ����? ������� �������������? ������ �?������',
            labels=[f'�������� {int(label)}' if isinstance(label, (int, float, np.integer)) else str(label) for label in task_stats.index.tolist()],
            values=[_safe_float(value) for value in task_stats.tolist()],
        ),
        _chart_record(
            'group-gain',
            '��������? ?��',
            'bar',
            '?� �����? ������?� �?�� ��??� �?���� ��������',
            labels=prepost_labels,
            values=gain_values,
        ),
        _chart_record(
            'weak-topics',
            '�? ?��� �?�����',
            'hbar',
            '?�� ����?/������������� �?���� �?���',
            labels=list(weak_topics.index),
            values=[_safe_float(value) for value in weak_topics.tolist()],
        ),
        _chart_record(
            'strong-topics',
            '�? ��?�� �?�����',
            'bar',
            '?�� ����������� ��?�� ���������',
            labels=list(strong_topics.index),
            values=[_safe_float(value) for value in strong_topics.tolist()],
        ),
        _chart_record(
            'risk-students',
            '�?����� ��?��� �?������',
            'hbar',
            '?�� �?������?� �??�� ?����� ?����',
            labels=list(top_risk['student_name']),
            values=[_safe_float(value) for value in top_risk['risk_score'].tolist()],
        ),
        _chart_record(
            'group-levels',
            '��� ������� ?����� ??������',
            'stackedbar',
            '?� �����?� �?���, ������, ��?��� ��?������ ����������� ����',
            labels=list(group_level.index),
            series=[
                {'name': '�?���', 'values': [int(group_level.get('low', pd.Series(index=group_level.index, data=0)).get(group, 0)) for group in group_level.index]},
                {'name': '������', 'values': [int(group_level.get('medium', pd.Series(index=group_level.index, data=0)).get(group, 0)) for group in group_level.index]},
                {'name': '��?���', 'values': [int(group_level.get('high', pd.Series(index=group_level.index, data=0)).get(group, 0)) for group in group_level.index]},
            ],
        ),
        _chart_record(
            'student-scatter',
            '������ ���� �?�� �?��?����?',
            'scatter',
            '?� �?�����? ������ �?������� ��� ����?��',
            points=[
                {
                    'x': _safe_float(row['mean']),
                    'y': _safe_float(row['std']),
                    'label': str(index[0]),
                    'group': str(index[1]),
                }
                for index, row in mean_std.iterrows()
            ],
        ),
        _chart_record(
            'group-session-heatmap',
            '��� x ����? ���� �������',
            'heatmap',
            '?� �����? ?� ����? ������� ������ �?�����',
            xLabels=[str(label) for label in heatmap_table.columns.tolist()],
            yLabels=[str(label) for label in heatmap_table.index.tolist()],
            matrix=[[_safe_float(value) for value in row] for row in heatmap_table.values.tolist()],
        ),
        _chart_record(
            'comparison-means',
            '�����? ���������',
            'bar',
            f"{comparison['basis']}. ����� ������������? ?�������� �?����� �?�������.",
            labels=[comparison['left_label'], comparison['right_label']],
            values=[comparison['left_mean'], comparison['right_mean']],
        ),
        _chart_record(
            'session-risk-density',
            '����?��� ������� �?����� ��?����?�',
            'bar',
            '?� ����?��?� �?��� ��?������ �������� ����',
            labels=[str(label) for label in session_risk.index.tolist()],
            values=[int(value) for value in session_risk.tolist()],
        ),
        _chart_record(
            'task-heatmap',
            '��� x �������� ���� �������',
            'heatmap',
            '?� �����? 1-3 ����������� ������� ������ �?�����',
            xLabels=[f'�������� {int(label)}' if isinstance(label, (int, float, np.integer)) else str(label) for label in task_heatmap.columns.tolist()],
            yLabels=[str(label) for label in task_heatmap.index.tolist()],
            matrix=[[_safe_float(value) for value in row] for row in task_heatmap.values.tolist()],
        ),
        _chart_record(
            'group-topic-gap',
            '?� �����? �? ?��� ��?�����',
            'hbar',
            '��� ������� �? �?��� ������ �?���� ������ �?�����',
            labels=[f"{row['group_name']} � {row['lesson_topic']}" for _, row in group_topic_gap.iterrows()],
            values=[_safe_float(row['percentage']) for _, row in group_topic_gap.iterrows()],
        ),
        _chart_record(
            'growth-scatter',
            '������?� ��?��� ��� ?�� ���������',
            'scatter',
            'Pre-test �?������� ��� post-test ?���? �������',
            points=[
                {
                    'x': _safe_float(row['pre_score']),
                    'y': _safe_float(row['gain']),
                    'label': str(row['student_name']),
                    'group': str(row['group_name']),
                }
                for _, row in gain_scatter.head(18).iterrows()
            ],
        ),
    ]
    return charts


def _build_tables(frame, student_risk):
    weakest_students = []
    for _, row in student_risk.head(12).iterrows():
        subset = frame[frame['student_name'] == row['student_name']]
        weakest_subject = (
            subset.groupby('subject_name')['percentage'].mean().sort_values().index[0]
            if not subset.empty
            else '����������� �?�'
        )
        weakest_students.append(
            {
                'student_name': row['student_name'],
                'group_name': row['group_name'],
                'avg_score': _safe_float(row['avg_score']),
                'risk_score': _safe_float(row['risk_score']),
                'weakest_subject': weakest_subject,
                'weakest_session': row.get('session_label', ''),
                'weakest_topic': row.get('lesson_topic', ''),
                'status': row['status_label'],
            }
        )

    lesson_status = (
        frame.groupby(['session_label', 'group_name', 'subject_name'])
        .agg(
            avg_score=('percentage', 'mean'),
            student_count=('student_name', 'nunique'),
            weak_task=('lesson_topic', lambda values: pd.Series(values).mode().iloc[0] if len(values) else ''),
        )
        .reset_index()
        .sort_values(by='avg_score')
    )
    weak_lessons = []
    for _, row in lesson_status.head(15).iterrows():
        avg_score = _safe_float(row['avg_score'])
        weak_lessons.append(
            {
                'session_label': row['session_label'],
                'group_name': row['group_name'],
                'subject_name': row['subject_name'],
                'lesson_topic': row['weak_task'],
                'avg_score': avg_score,
                'status': _status_label(_performance_level(avg_score)),
                'student_count': int(row['student_count']),
            }
        )

    top_students = (
        frame.groupby(['student_name', 'group_name'])['percentage']
        .mean()
        .reset_index()
        .sort_values(by='percentage', ascending=False)
        .head(10)
    )
    top_rows = [
        {
            'student_name': row['student_name'],
            'group_name': row['group_name'],
            'avg_score': _safe_float(row['percentage']),
            'status': '��?���',
        }
        for _, row in top_students.iterrows()
    ]

    preview_columns = [
        ('student_name', '���'),
        ('group_name', '���'),
        ('session_label', '����?'),
        ('lesson_topic', '��?����'),
        ('task_index', '��������'),
        ('percentage', '�?���� %'),
        ('performance_level', '��?���'),
    ]
    existing_preview_columns = [(key, label) for key, label in preview_columns if key in frame.columns]
    preview_headers = [label for _, label in existing_preview_columns]
    preview_rows = []
    if existing_preview_columns:
        preview_frame = frame[[key for key, _ in existing_preview_columns]].head(12).copy()
        if 'percentage' in preview_frame.columns:
            preview_frame['percentage'] = preview_frame['percentage'].apply(_safe_float)
        preview_rows = preview_frame.values.tolist()

    return {
        'weakest_students': weakest_students,
        'weak_lessons': weak_lessons,
        'top_students': top_rows,
        'preview_headers': preview_headers,
        'preview_rows': preview_rows,
    }


def _build_recommendations(frame, student_risk, comparison):
    recommendations = []
    for _, row in student_risk.head(5).iterrows():
        student_rows = frame[frame['student_name'] == row['student_name']]
        weakest_session = row.get('session_label') or '��?�� ����? �?����������'
        weakest_topic = row.get('lesson_topic') or '?��� �������� ���?�������'
        weak_subject = (
            student_rows.groupby('subject_name')['percentage'].mean().sort_values().index[0]
            if not student_rows.empty
            else '����������� �?�'
        )
        recommendations.append(
            f"{row['student_name']} ({row['group_name']}) ?��� ����� �?����� ����?�: {weak_subject}. "
            f"�? ?��� �������� {weakest_session}, �� ?�����? ���?��?�� �?�� {weakest_topic}. "
            f"��� ����??� ?���� �?�����, ?��?� �������������? �������� �?�� ���� ��� �������� ���� ?��������."
        )

    weak_group_subjects = (
        frame.groupby(['group_name', 'session_label'])['percentage']
        .mean()
        .reset_index()
        .sort_values(by='percentage')
        .head(3)
    )
    for _, row in weak_group_subjects.iterrows():
        recommendations.append(
            f"{row['group_name']} ���� {row['session_label']} ������� ������ {_safe_float(row['percentage'])}% ?��� �?�����. "
            f"�?� ������?� ?������ �?������, �?���? �?��� �?�� ����� ����? ������� ?��?� ?������� ���� �����."
        )

    if comparison.get('p_value') is not None and comparison.get('effect_size') is not None:
        recommendations.append(
            f"{comparison['left_label']} �?�� {comparison['right_label']} ��������?� ����������� "
            f"p-value = {comparison['p_value']}, effect size = {comparison['effect_size']}. "
            f"{comparison['interpretation']}"
        )

    recommendations.append(
        '�� �?������ �?��� ��?������ �?������?� ?��� ����?��� ������� �����-�?������, '
        '������ ��?����������� ����� ������������, ��?��� ��?����������� �?������������ �������� ?������ �?� �?���.'
    )
    return recommendations


def _ordered_sessions(frame):
    if 'lesson_index' in frame.columns and frame['lesson_index'].notna().any():
        ordered = (
            frame[['session_label', 'week_index', 'lesson_index']]
            .drop_duplicates()
            .sort_values(by=['week_index', 'lesson_index', 'session_label'])
        )
        return ordered['session_label'].tolist()
    return (
        frame[['session_label']]
        .drop_duplicates()
        .sort_values(by=['session_label'])
        ['session_label']
        .tolist()
    )


def _build_prepost_metrics(frame):
    sessions = _ordered_sessions(frame)
    if not sessions:
        return {
            'pre_label': '������?�',
            'post_label': '��??�',
            'group_pairs': [],
            'gain_leaders': [],
            'overall_gain': 0.0,
        }

    pre_label = sessions[0]
    post_label = sessions[-1]
    pre_data = frame[frame['session_label'] == pre_label]
    post_data = frame[frame['session_label'] == post_label]

    pre_group = pre_data.groupby('group_name')['percentage'].mean()
    post_group = post_data.groupby('group_name')['percentage'].mean()
    all_groups = sorted(set(pre_group.index).union(set(post_group.index)))
    group_pairs = []
    for group_name in all_groups:
        pre_value = _safe_float(pre_group.get(group_name, 0))
        post_value = _safe_float(post_group.get(group_name, 0))
        group_pairs.append(
            {
                'group_name': group_name,
                'pre_value': pre_value,
                'post_value': post_value,
                'gain': _safe_float(post_value - pre_value),
            }
        )

    by_student = frame.groupby(['student_name', 'group_name', 'session_label'])['percentage'].mean().reset_index()
    pre_students = by_student[by_student['session_label'] == pre_label][['student_name', 'group_name', 'percentage']].rename(
        columns={'percentage': 'pre_score'}
    )
    post_students = by_student[by_student['session_label'] == post_label][['student_name', 'group_name', 'percentage']].rename(
        columns={'percentage': 'post_score'}
    )
    merged = pre_students.merge(post_students, on=['student_name', 'group_name'], how='inner')
    merged['gain'] = merged['post_score'] - merged['pre_score']
    gain_leaders = [
        {
            'student_name': row['student_name'],
            'group_name': row['group_name'],
            'pre_score': _safe_float(row['pre_score']),
            'post_score': _safe_float(row['post_score']),
            'gain': _safe_float(row['gain']),
        }
        for _, row in merged.sort_values(by='gain', ascending=False).head(8).iterrows()
    ]

    overall_gain = 0.0
    if group_pairs:
        overall_gain = _safe_float(np.mean([pair['gain'] for pair in group_pairs]))

    return {
        'pre_label': pre_label,
        'post_label': post_label,
        'group_pairs': group_pairs,
        'gain_leaders': gain_leaders,
        'overall_gain': overall_gain,
    }


def _build_topic_deficits(frame):
    topic_table = (
        frame.groupby(['group_name', 'lesson_topic'])
        .agg(
            avg_score=('percentage', 'mean'),
            student_count=('student_name', 'nunique'),
            session_label=('session_label', lambda values: pd.Series(values).mode().iloc[0] if len(values) else ''),
        )
        .reset_index()
        .sort_values(by='avg_score')
    )
    deficits = []
    for _, row in topic_table.head(12).iterrows():
        deficits.append(
            {
                'group_name': row['group_name'],
                'lesson_topic': row['lesson_topic'],
                'session_label': row['session_label'],
                'avg_score': _safe_float(row['avg_score']),
                'student_count': int(row['student_count']),
                'status': _status_label(_performance_level(row['avg_score'])),
            }
        )
    return deficits


def _build_risk_zones(frame, student_risk):
    high = int((student_risk['risk_score'] >= 65).sum())
    medium = int(((student_risk['risk_score'] >= 40) & (student_risk['risk_score'] < 65)).sum())
    low = int((student_risk['risk_score'] < 40).sum())
    return {
        'high': high,
        'medium': medium,
        'low': low,
        'high_students': student_risk.loc[student_risk['risk_score'] >= 65, 'student_name'].head(8).tolist(),
    }


def build_summary(frame, mapping, meta, source_columns=None):
    student_risk = _student_risk_table(frame)
    comparison = _build_group_comparison(frame)
    prepost_metrics = _build_prepost_metrics(frame)
    topic_deficits = _build_topic_deficits(frame)
    risk_zones = _build_risk_zones(frame, student_risk)
    tables = _build_tables(frame, student_risk)
    recommendations = _build_recommendations(frame, student_risk, comparison)
    charts = _build_charts(frame, student_risk, comparison, prepost_metrics)

    metrics = {
        'rows': int(len(frame)),
        'students': int(frame['student_name'].nunique()),
        'groups': int(frame['group_name'].nunique()),
        'subjects': int(frame['subject_name'].nunique()),
        'topics': int(frame['lesson_topic'].nunique()),
        'sessions': int(frame['session_label'].nunique()),
        'average_score': _safe_float(frame['percentage'].mean()),
        'median_score': _safe_float(frame['percentage'].median()),
        'min_score': _safe_float(frame['percentage'].min()),
        'max_score': _safe_float(frame['percentage'].max()),
        'low_count': int((frame['performance_level'] == 'low').sum()),
        'medium_count': int((frame['performance_level'] == 'medium').sum()),
        'high_count': int((frame['performance_level'] == 'high').sum()),
        'format_type': str(frame['format_type'].iloc[0]) if not frame.empty else 'long',
    }

    detected = {
        'mapped': mapping,
        'available_columns': [str(column) for column in (source_columns or frame.columns.tolist())],
        'file_type': meta.get('file_type', ''),
        'sheet_name': meta.get('sheet_name', ''),
    }

    return _json_safe({
        'metrics': metrics,
        'comparison': comparison,
        'prepost': prepost_metrics,
        'topic_deficits': topic_deficits,
        'risk_zones': risk_zones,
        'charts': charts,
        'tables': tables,
        'recommendations': recommendations,
        'detected_columns': detected,
    })


def build_uploaded_student_profile(dataset, student_name):
    records = list(dataset.records.filter(student_name=student_name).order_by('lesson_date', 'lesson_topic', 'id'))
    if not records:
        return None

    frame = pd.DataFrame(
        [
            {
                'student_name': record.student_name,
                'group_name': record.group_name,
                'subject_name': record.subject_name,
                'lesson_topic': record.lesson_topic,
                'session_label': record.lesson_date.strftime('%Y-%m-%d') if record.lesson_date else record.lesson_topic,
                'percentage': float(record.percentage),
                'attendance_status': record.attendance_status,
            }
            for record in records
        ]
    )

    avg_score = _safe_float(frame['percentage'].mean())
    weak_topics = (
        frame.groupby('lesson_topic')['percentage'].mean().sort_values().head(5).reset_index()
    )
    session_progress = (
        frame.groupby('session_label')['percentage'].mean().sort_index().reset_index()
    )
    subject_stats = (
        frame.groupby('subject_name')['percentage'].mean().sort_values().reset_index()
    )

    risk_score = _clamp((100 - avg_score) * 0.75 + frame['percentage'].std(ddof=0 if len(frame) == 1 else 1) * 0.25 if len(frame) > 1 else (100 - avg_score))
    recommendations = []
    if avg_score < 50:
        recommendations.append('�?���?� ���� �?�����, ?��?� ?���� �?��� �?�� ?������? ������� ?����.')
    elif avg_score < 75:
        recommendations.append('�?���?� ����� ������������ ��� ?��?� ��� �������� ?����.')
    else:
        recommendations.append('�?���?� �?������������ �������� �?�� �?��������? �?� ������ ������.')

    if not weak_topics.empty:
        weakest = ', '.join(weak_topics['lesson_topic'].head(3).tolist())
        recommendations.append(f'�? ?��� �?�����: {weakest}.')

    chart_pack = [
        _chart_record(
            'student-progress',
            '�?��� ����������',
            'line',
            '����?��� ������� ������ �?����',
            labels=session_progress['session_label'].tolist(),
            values=[_safe_float(value) for value in session_progress['percentage'].tolist()],
        ),
        _chart_record(
            'student-subjects',
            '�?���� ������� �?����',
            'bar',
            '?�� �?���� ?����?���� �?��',
            labels=subject_stats['subject_name'].tolist(),
            values=[_safe_float(value) for value in subject_stats['percentage'].tolist()],
        ),
        _chart_record(
            'student-weak-topics',
            '?��� ��?�������',
            'hbar',
            '�? �?��� �?���� �?������� ����������� ��� �?�����',
            labels=weak_topics['lesson_topic'].tolist(),
            values=[_safe_float(value) for value in weak_topics['percentage'].tolist()],
        ),
    ]

    return {
        'student_name': student_name,
        'group_name': records[0].group_name,
        'avg_score': avg_score,
        'risk_score': risk_score,
        'record_count': len(records),
        'records': records,
        'weak_topics': [
            {'lesson_topic': row['lesson_topic'], 'avg_score': _safe_float(row['percentage'])}
            for _, row in weak_topics.iterrows()
        ],
        'recommendations': recommendations,
        'charts': chart_pack,
    }


@transaction.atomic
def analyze_uploaded_dataset(dataset_id):
    dataset = AnalysisDataset.objects.select_for_update().get(pk=dataset_id)
    dataset.status = 'processing'
    dataset.error_message = ''
    dataset.save(update_fields=['status', 'error_message', 'updated_at'])

    frame, meta = load_dataframe(dataset.source_file.path)
    mapping = detect_column_mapping(list(frame.columns))
    normalized, format_type = normalize_dataset_frame(frame, mapping)

    dataset.records.all().delete()
    records = []
    for _, row in normalized.iterrows():
        lesson_date = None
        if pd.notna(row['lesson_date']):
            lesson_date = row['lesson_date'].date()
        records.append(
            PerformanceRecord(
                dataset=dataset,
                student_name=str(row['student_name']),
                group_name=str(row['group_name']),
                subject_name=str(row['subject_name']),
                lesson_topic=str(row['lesson_topic']),
                lesson_date=lesson_date,
                raw_score=None if pd.isna(row['raw_score']) else round(float(row['raw_score']), 2),
                max_score=None if pd.isna(row['max_score']) else round(float(row['max_score']), 2),
                percentage=round(float(row['percentage']), 2),
                attendance_status=str(row['attendance_status']),
                performance_level=str(row['performance_level']),
                source_row_number=int(row['source_row_number']),
            )
        )
    PerformanceRecord.objects.bulk_create(records, batch_size=500)

    summary = build_summary(normalized, mapping, meta, source_columns=list(frame.columns))
    summary['metrics']['format_type'] = format_type
    dataset.original_filename = dataset.original_filename or Path(dataset.source_file.name).name
    dataset.file_type = meta.get('file_type', '')
    dataset.sheet_name = meta.get('sheet_name', '')
    dataset.status = 'ready'
    dataset.row_count = len(records)
    dataset.detected_columns = summary['detected_columns']
    dataset.summary_json = summary
    dataset.save(
        update_fields=[
            'original_filename',
            'file_type',
            'sheet_name',
            'status',
            'row_count',
            'detected_columns',
            'summary_json',
            'updated_at',
        ]
    )
    return dataset
