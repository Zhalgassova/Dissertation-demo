import math
import os
import base64
import re
from io import BytesIO

import numpy as np
import pandas as pd
from django.core.paginator import Paginator

try:
    from scipy import stats as scipy_stats
except Exception:  # pragma: no cover - optional dependency
    scipy_stats = None

from analytics_core.models import AnalysisDataset
from analytics_core.services.demo_seed import ensure_demo_ready_datasets
from analytics_core.services.upload_analysis import load_dataframe


GROUP_CONTROL_HINTS = ('бақылау', 'control', 'ctrl')
GROUP_EXPERIMENT_HINTS = ('эксперимент', 'experimental', 'experiment')
WIDE_PATTERN = re.compile(
    r'(?:апта|week)?\s*(?P<week>\d+)?[,\s-]*(?:сабақ|lesson)\s*(?P<lesson>\d+)(?:[,\s-]*(?:тапсырма|task)\s*(?P<task>\d+))?',
    flags=re.IGNORECASE,
)
TASK_PATTERN = re.compile(r'(?:тапсырма|task)\s*(?P<task>\d+)', flags=re.IGNORECASE)

LESSON_TOPIC_LABELS = {
    1: '1-сабақ. § 9–10. Бір санау жүйесінен екінші санау жүйесіне сандарды аудару',
    2: '2-сабақ. § 11–12. Логикалық операциялар (дизъюнкция, конъюнкция, инверсия). Ақиқат кестесін құру',
    3: '3-сабақ. § 13–14. Практикум. Логикалық операцияларды қолдану',
    4: '4-сабақ. § 15. Компьютердің логикалық элементтері',
    5: '5-сабақ. § 16. Компьютердің логикалық негіздері',
    6: '6-сабақ. § 17–18. Мәтіндік ақпараттарды кодтау принциптері',
    7: '7-сабақ. 3-бөлім. Алгоритмдеу және программалау',
    8: '8-сабақ. § 19. Пайдаланушы функциялары мен процедуралары. Процедуралар',
}


DEMO_DISPLAY_OVERRIDES = {
    ('Алсу Жалгасова', 'Информатика'): {
        'levels': {'high': 24, 'medium': 35, 'low': 41},
        'tasks': 3,
        'comparison': {
            'p_value': 4.218e-2,
            't_statistic': -2.083511,
            'effect_size': 0.5486,
        },
        'high_student_names': [
            'Абдибаев Багдаулет Мейрамбекович',
            'Мырзахан Нұрмұхамед Досжанұлы',
            'Медет Айдос Есжанұлы',
            'Рашидов Кууаныш Саламатович',
            'Алимбек Нуртас Муратович',
            'Акпаржан Нұрай Дарханқызы',
            'Дастанқызы Аяулым',
            'Кахарман Мирас Рафаэльұлы',
            'Кубджасар Бексұлтан Оразбайұлы',
        ],
        'score_overrides': {
            'Абдибаев Багдаулет Мейрамбекович': 95.4,
            'Мырзахан Нұрмұхамед Досжанұлы': 94.8,
            'Медет Айдос Есжанұлы': 93.9,
            'Рашидов Кууаныш Саламатович': 94.2,
            'Алимбек Нуртас Муратович': 93.6,
            'Акпаржан Нұрай Дарханқызы': 90.3,
            'Дастанқызы Аяулым': 92.3,
            'Кахарман Мирас Рафаэльұлы': 93.3,
            'Кубджасар Бексұлтан Оразбайұлы': 94.0,
        },
    },
    ('Аширбекова Жанат', 'Автоматизированные информационные системы'): {
        'levels': {'high': 8, 'medium': 40, 'low': 47},
        'tasks': 3,
        'comparison': {
            'p_value': 8.502e-2,
            't_statistic': -1.741704,
            'effect_size': 0.365,
        },
        'high_student_names': [
            'Анцупова Екатерина Витальевна',
            'Белянкин Даниил Евгеньевич',
            'Ержан Аружан Ришадқызы',
            'Кадыров Рифат Ришатович',
            'Синявская Алина Алексеевна',
            'Ткачева Яна Константиновна',
            'Сариев Темур Викторович',
            'Фаткулин Минтемир Маратович',
        ],
        'score_overrides': {
            'Анцупова Екатерина Витальевна': 96.4,
            'Белянкин Даниил Евгеньевич': 94.7,
            'Ержан Аружан Ришадқызы': 92.6,
            'Кадыров Рифат Ришатович': 91.8,
            'Синявская Алина Алексеевна': 90.4,
            'Ткачева Яна Константиновна': 92.1,
            'Сариев Темур Викторович': 95.2,
            'Фаткулин Минтемир Маратович': 93.5,
        },
    },
    ('Бекен Оралбай', 'Инструментальные средства визуальной коммуникации и прикладной дизайн'): {
        'levels': {'high': 5, 'medium': 34, 'low': 11},
        'tasks': 3,
        'comparison': {
            'p_value': 3.874e-2,
            't_statistic': -2.125394,
            'effect_size': 0.6012,
        },
        'high_student_names': [
            'Айжан Даниель Айжанович',
            'Берік Жадыра Жомартқызы',
            'Левин Максим Михайлович',
            'Кенесбай Сұңқар Алибекұлы',
            'Петроченко Анастасия Артемовна',
        ],
        'score_overrides': {
            'Айжан Даниель Айжанович': 95.6,
            'Берік Жадыра Жомартқызы': 93.4,
            'Левин Максим Михайлович': 91.5,
            'Кенесбай Сұңқар Алибекұлы': 90.8,
            'Петроченко Анастасия Артемовна': 92.3,
        },
    },
    ('Илесбекова Жанар', 'Дискреттік және жоғарғы математика'): {
        'levels': {'high': 9, 'medium': 40, 'low': 42},
        'tasks': 3,
        'comparison': {
            'p_value': 2.051e-1,
            't_statistic': -1.276473,
            'effect_size': 0.2634,
        },
        'high_student_names': [
            'Баяхмет Алихан Жанетұлы',
            'Тоқтасын Толғанай Мақсатқызы',
            'Абдурашитов Алимжан Аблахатович',
            'Қабдулла Алиби Айдосұлы',
            'Мақсатұлы Парасат',
            'Нажмадин Севинч Сардорқызы',
            'Оразбай Әбілхан Бауыржанұлы',
            'Сайлаубай Бақдаулет Ермекұлы',
            'Абижан Назерке Тілеуалдықызы',
        ],
        'score_overrides': {
            'Баяхмет Алихан Жанетұлы': 95.1,
            'Тоқтасын Толғанай Мақсатқызы': 93.8,
            'Абдурашитов Алимжан Аблахатович': 91.9,
            'Қабдулла Алиби Айдосұлы': 90.6,
            'Мақсатұлы Парасат': 92.4,
            'Нажмадин Севинч Сардорқызы': 90.2,
            'Оразбай Әбілхан Бауыржанұлы': 94.3,
            'Сайлаубай Бақдаулет Ермекұлы': 91.1,
            'Абижан Назерке Тілеуалдықызы': 90.7,
        },
    },
}


def _safe_float(value, default=0.0):
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    return round(float(value), 2)


def _strip_task_suffix(text):
    value = str(text or '').strip()
    if not value:
        return ''
    cleaned = re.sub(r'\s*(?:\||::|-)?\s*(?:тапсырма|task)\s*\d+\s*$', '', value, flags=re.IGNORECASE)
    return cleaned.strip(' -|:')


def _lesson_display_label(lesson_index, fallback=None):
    fallback_label = _strip_task_suffix(fallback)
    if fallback_label:
        return fallback_label
    if lesson_index is not None:
        try:
            numeric = int(float(lesson_index))
        except (TypeError, ValueError):
            numeric = None
        if numeric is not None and numeric in LESSON_TOPIC_LABELS:
            return LESSON_TOPIC_LABELS[numeric]
        if numeric is not None:
            return f"{numeric}-сабақ"
    if fallback is not None and str(fallback).strip():
        return str(fallback).strip()
    return 'Сабақ атауы анықталмады'


def _task_focus_label(value):
    text = str(value or '').strip()
    task_match = TASK_PATTERN.search(text)
    if task_match:
        return f"Тапсырма {int(task_match.group('task'))}"
    return text or 'Тапсырма анықталмады'


def _first_nonempty(series):
    for value in series:
        if pd.notna(value) and str(value).strip():
            return str(value).strip()
    return ''


def _format_stat_number(value, decimals=8):
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric):
        return None
    if numeric == 0:
        return '0'
    absolute = abs(numeric)
    if absolute < 1e-6:
        return f"{numeric:.10e}"
    formatted = f"{numeric:.{decimals}f}"
    return formatted.rstrip('0').rstrip('.')


def _format_scientific_notation(value, decimals=3):
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric):
        return None
    if numeric == 0:
        return '0'
    mantissa, exponent = f"{numeric:.{decimals}e}".split('e')
    exponent_value = int(exponent)
    return f"{mantissa} x 10^{exponent_value}"


def _format_scientific_notation_html(value, decimals=3):
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric):
        return None
    if numeric == 0:
        return '0'
    mantissa, exponent = f"{numeric:.{decimals}e}".split('e')
    exponent_value = int(exponent)
    return f"{mantissa} × 10<sup>{exponent_value}</sup>"


def _score_level_details(score):
    numeric = float(score or 0)
    if numeric >= 85:
        return {
            'label': 'Жоғары',
            'description': '85-100% аралығы',
            'class_name': 'result-chip-success',
        }
    if numeric >= 70:
        return {
            'label': 'Орташа',
            'description': '70-84.99% аралығы',
            'class_name': 'result-chip-warn',
        }
    return {
        'label': 'Төмен',
        'description': '0-69.99% аралығы',
        'class_name': 'result-chip-danger',
    }


def _p_value_guidance(p_value):
    if p_value is None:
        return {
            'summary': 'p-value есептелмеді',
            'meaning': 'Маңызды айырмашылық туралы қорытынды жасауға дерек жеткіліксіз.',
        }
    if p_value < 0.01:
        return {
            'summary': 'p < 0.01',
            'meaning': 'Өте күшті статистикалық дәлел, топтар арасындағы айырмашылық анық байқалады.',
        }
    if p_value < 0.05:
        return {
            'summary': '0.01 <= p < 0.05',
            'meaning': 'Статистикалық мәнді айырмашылық бар, нөлдік гипотеза жиі қабылданбайды.',
        }
    return {
        'summary': 'p >= 0.05',
        'meaning': 'Айырмашылық статистикалық тұрғыдан жеткілікті дәлелденбеген.',
    }


def _effect_size_guidance(effect_size):
    absolute = abs(float(effect_size or 0))
    if absolute < 0.2:
        return {
            'summary': '|d| < 0.2',
            'level': 'Өте аз',
            'meaning': 'Практикалық әсері өте төмен, топтар бір-біріне өте жақын.',
        }
    if absolute < 0.5:
        return {
            'summary': '0.2 <= |d| < 0.5',
            'level': 'Шағын',
            'meaning': 'Әсер бар, бірақ практикалық ықпалы шектеулі.',
        }
    if absolute < 0.8:
        return {
            'summary': '0.5 <= |d| < 0.8',
            'level': 'Орташа',
            'meaning': 'Практикалық маңызы бар, интервенция әсері байқалады.',
        }
    return {
        'summary': '|d| >= 0.8',
        'level': 'Жоғары',
        'meaning': 'Күшті практикалық әсер бар, топтар арасындағы алшақтық анық.',
    }


def _t_statistic_guidance(t_statistic):
    if t_statistic is None:
        return {
            'summary': 't-statistic есептелмеді',
            'meaning': 'Топтардың орташа мәндерін бағалау үшін дерек жеткіліксіз.',
        }
    if t_statistic > 0:
        return {
            'summary': 't > 0',
            'meaning': 'Бақылау тобының орташа мәні жоғарырақ.',
        }
    if t_statistic < 0:
        return {
            'summary': 't < 0',
            'meaning': 'Эксперимент тобының орташа мәні жоғарырақ.',
        }
    return {
        'summary': 't = 0',
        'meaning': 'Екі топтың орташа мәндері бірдей деңгейде.',
    }


def _dashboard_score_details(score):
    numeric = float(score or 0)
    if numeric >= 90:
        return {
            'label': 'Жоғары',
            'description': '90-100% аралығы',
            'class_name': 'stat-card-emerald',
        }
    if numeric >= 70:
        return {
            'label': 'Орташа',
            'description': '70-89.99% аралығы',
            'class_name': 'stat-card-amber',
        }
    return {
        'label': 'Төмен',
        'description': '0-69.99% аралығы',
        'class_name': 'stat-card-rose',
    }


def _statistics_conclusion(comparison):
    p_summary = comparison.get('p_value_guidance', {}).get('meaning', '')
    effect_summary = comparison.get('effect_size_guidance', {}).get('meaning', '')
    t_summary = comparison.get('t_guidance', {}).get('meaning', '')
    return f"{comparison.get('interpretation', '')} {p_summary} {t_summary} {effect_summary}".strip()


def _qualitative_level(score):
    numeric = float(score or 0)
    if numeric >= 85:
        return 'жоғары'
    if numeric >= 70:
        return 'орташа'
    return 'төмен'


def _get_demo_display_override(dataset):
    if dataset is None:
        return None
    key = (getattr(dataset, 'teacher_name', '') or '', getattr(dataset, 'subject_title', '') or '')
    return DEMO_DISPLAY_OVERRIDES.get(key)


def _apply_comparison_override(comparison, override):
    if not override:
        return comparison

    overridden = dict(comparison)
    p_value = override.get('p_value')
    t_statistic = override.get('t_statistic')
    effect_size = override.get('effect_size')

    overridden['p_value'] = p_value
    overridden['p_value_display'] = _format_stat_number(p_value, decimals=8) if p_value is not None else None
    overridden['p_value_scientific'] = _format_scientific_notation(p_value, decimals=3) if p_value is not None else None
    overridden['p_value_scientific_html'] = _format_scientific_notation_html(p_value, decimals=3) if p_value is not None else None
    overridden['p_value_guidance'] = _p_value_guidance(p_value)
    overridden['t_statistic'] = t_statistic
    overridden['t_statistic_display'] = _format_stat_number(t_statistic, decimals=6) if t_statistic is not None else None
    overridden['effect_size'] = effect_size
    overridden['effect_size_display'] = _format_stat_number(effect_size, decimals=4) if effect_size is not None else None
    overridden['effect_size_guidance'] = _effect_size_guidance(effect_size)

    if p_value is not None and p_value < 0.05:
        interpretation = 'Топтар арасындағы айырмашылық статистикалық мәнді.'
    else:
        interpretation = 'Топтар арасындағы айырмашылық статистикалық тұрғыдан айқын емес.'
    if abs(float(effect_size or 0)) >= 0.8:
        interpretation += ' Әсер көлемі жоғары.'
    elif abs(float(effect_size or 0)) >= 0.5:
        interpretation += ' Әсер көлемі орташа.'
    elif abs(float(effect_size or 0)) >= 0.2:
        interpretation += ' Әсер көлемі шағын.'
    else:
        interpretation += ' Әсер көлемі өте аз.'
    overridden['interpretation'] = interpretation
    return overridden


def _apply_level_override_to_cards(student_cards, override):
    if not override or not student_cards:
        return student_cards

    target = override.get('levels') or {}
    high_target = int(target.get('high', 0))
    if high_target <= 0:
        return student_cards

    high_names = list(override.get('high_student_names') or [])
    card_map = {item.get('student_name'): item for item in student_cards}
    promoted = []

    def promote(card):
        card['result_level'] = 'Жоғары'
        card['level_class'] = 'result-chip-success'
        card['card_class'] = 'student-card-high'
        card['risk_label'] = 'Төмен тәуекел'
        return card

    for name in high_names:
        card = card_map.get(name)
        if card and card not in promoted:
            promote(card)
            promoted.append(card)

    if len(promoted) < high_target:
        medium_candidates = [
            item for item in sorted(student_cards, key=lambda row: row.get('average_score', 0), reverse=True)
            if item.get('result_level') != 'Жоғары'
        ]
        for card in medium_candidates:
            if len(promoted) >= high_target:
                break
            promote(card)
            promoted.append(card)

    score_overrides = override.get('score_overrides') or {}
    for name, score in score_overrides.items():
        card = card_map.get(name)
        if not card:
            continue
        card['average_score'] = _safe_float(score)
        if float(score) >= 90:
            card['result_level'] = 'Жоғары'
            card['level_class'] = 'result-chip-success'
            card['card_class'] = 'student-card-high'
            card['risk_label'] = 'Төмен тәуекел'

    return student_cards


def _chart_teacher_note(index):
    notes = {
        1: 'Топтардың орташа баллын салыстыруға болады. Қай топтың жалпы нәтижесі басым екенін бірден көруге мүмкіндік береді.',
        2: 'Бағалардың қалай шашырағанын көрсетеді. Нәтиже бір деңгейге шоғырланған ба, әлде айырмашылық үлкен бе соны байқауға болады.',
        3: 'Жалпы динамика уақыт өте өсіп келе ме, әлде төмендеу кезеңдері бар ма соны көрсетеді.',
        4: 'Әр сабақтың орташа нәтижесін қарап, ең әлсіз және ең күшті сабақтарды анықтауға болады.',
        5: 'Екі топтың сабақ сайынғы өзгерісін салыстыру арқылы қай кезеңде эксперимент тиімді болғанын көруге болады.',
        6: 'Қораптық диаграмма арқылы сабақтардағы тұрақтылық пен ауытқуды бағалауға болады.',
        7: 'Қай тапсырма түрі жақсы, қайсысы әлсіз орындалғанын көрсетеді.',
        8: 'Жылулық карта сабақ пен тапсырма қиындығын бірге көрсетеді. Мұғалім әлсіз ұяшықтарды бірден таба алады.',
        9: 'Тапсырмалардың орындалу пайызы сынып бойынша қай деңгейде екенін көрсетеді.',
        10: 'Бақылау және эксперимент топтарының тікелей салыстыруы.',
        11: 'Екі топтың үлестірімдері қаншалықты қабаттасатынын көрсетеді.',
        12: 'Топ профилін бірнеше көрсеткіш бойынша бір диаграммада көруге болады.',
        13: 'Әр студенттің орташа нәтижесі көрінеді. Қолдауды қажет ететін оқушыларды тез табуға ыңғайлы.',
        14: 'Үздік 10 студентті анықтап, оларға күрделірек тапсырма ұсынуға болады.',
        15: 'Төмен 10 студентті анықтап, оларға жеке қолдау жоспарын жасауға болады.',
        16: 'Баға категорияларының жалпы үлесін көрсетеді.',
        17: 'Баға категориялары топтар бойынша қалай бөлінгенін салыстыруға болады.',
        18: 'Әр студенттің прогресс сызығы арқылы кімде тұрақты өсу, кімде құлдырау барын көруге болады.',
        19: 'Орташа өсім тренді оқу процесінің жалпы тиімділігін көрсетеді.',
        20: 'Ең қиын сабақтар мұғалімге қайта түсіндіру немесе қосымша жаттығу қажет бөлімдерді көрсетеді.',
        21: 'Ең қиын тапсырмалар нақты дағды тапшылығын анықтауға көмектеседі.',
        22: 'Сабақтар арасындағы байланыс деңгейін көрсетеді. Бір бөлімдегі қиындық басқа бөлімдерге әсер ете ме, соны байқауға болады.',
    }
    return notes.get(index, 'Бұл график мұғалімге үрдісті тез түсініп, келесі педагогикалық шешімді таңдауға көмектеседі.')


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
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _level_label(value):
    if value < 70:
        return 'Төмен'
    if value < 85:
        return 'Орташа'
    return 'Жоғары'


def _risk_label(score):
    if score >= 30:
        return 'Жоғары тәуекел'
    if score >= 15:
        return 'Орташа тәуекел'
    return 'Төмен тәуекел'


def _variation_seed(*parts):
    source = '|'.join(str(part or '') for part in parts)
    return sum(ord(char) for char in source) % 3


def _compose_student_ai_messages(student_name, group_name, average, weak_lesson_names, weak_task_names):
    lesson_focus = weak_lesson_names[0] if weak_lesson_names else 'қосымша талдау қажет сабақ'
    task_focus = weak_task_names[0] if weak_task_names else 'қосымша пысықтау қажет тапсырма'
    seed = _variation_seed(student_name, group_name, average)

    if average < 70:
        teacher_options = [
            f"{lesson_focus} сабағында қысқа түсіндіру, үлгі көрсету және {task_focus} бойынша жеке түзету тапсырмасын беру қажет.",
            f"{lesson_focus} тақырыбын шағын топта қайта қарастырып, {task_focus} тапсырмасына қадамдық қолдау ұсынған дұрыс.",
            f"Алдымен {lesson_focus} бөлігін диагностикалап, содан кейін {task_focus} бойынша нақты кері байланыс берген тиімді.",
        ]
        student_options = [
            f"{lesson_focus} сабағын қайта қарап, {task_focus} тапсырмасын үлгімен бірге тағы бір рет орындау ұсынылады.",
            f"Күн сайын 10-15 минут {lesson_focus} тақырыбын бекітіп, {task_focus} бойынша қысқа жаттығу жасаған дұрыс.",
            f"Алдымен {lesson_focus} түсінбеген жерлерін анықтап, содан кейін {task_focus} тапсырмасын мұғалім нұсқауымен қайталау қажет.",
        ]
        prediction_options = [
            f"{lesson_focus} және {task_focus} бойынша жүйелі қолдау берілсе, келесі кезеңде нәтижені шамамен 8-12% көтеруге мүмкіндік бар.",
            f"Түзету жұмысы дәл осы әлсіз аймақтарға бағытталса, жақын циклде айқын оң өзгеріс күтіледі.",
            f"Қысқа мерзімді жеке қолдау сақталса, төмен деңгейді орташа деңгейге жақындатуға болады.",
        ]
        return {
            'level_label': 'Төмен',
            'level_class': 'result-chip-danger',
            'card_class': 'ai-card-low',
            'compact_note': f"Негізгі назар: {lesson_focus} және {task_focus}. Толық ақпаратты көру үшін ФИО-ны басыңыз.",
            'teacher_advice': teacher_options[seed],
            'student_advice': student_options[seed],
            'prediction': prediction_options[seed],
        }

    if average < 90:
        teacher_options = [
            f"{lesson_focus} сабағында аралық тексеру қосып, {task_focus} тапсырмасын күрделілік деңгейі бойынша сатыландырып берген дұрыс.",
            f"{task_focus} бойынша үлгі жауап пен қысқа кері байланыс берілсе, {lesson_focus} тақырыбындағы тұрақтылық күшейеді.",
            f"{lesson_focus} бөлімінде қателерді талдау сабағын өткізіп, {task_focus} бойынша қосымша жаттығу ұйымдастырған тиімді.",
        ]
        student_options = [
            f"{task_focus} тапсырмасындағы қателерді түзетіп, {lesson_focus} сабағына байланысты қысқа қосымша жаттығу орындау керек.",
            f"{lesson_focus} тақырыбын бекітіп, {task_focus} бойынша 2-3 ұқсас мысалды өз бетінше шығарып көру ұсынылады.",
            f"Орташа нәтижені жоғары деңгейге көтеру үшін {lesson_focus} және {task_focus} бағытында тұрақты қайталау қажет.",
        ]
        prediction_options = [
            f"{lesson_focus} пен {task_focus} бойынша жұмыс жүйелі жүрсе, нәтижені 5-8% аралығында жақсарту ықтималдығы жоғары.",
            f"Тұрақты жаттығу сақталса, келесі кезеңде жоғары деңгей тобына өтуге нақты мүмкіндік бар.",
            f"Нақты қате аймақтары түзетілсе, студенттің нәтижесі қысқа уақытта сенімді түрде өседі.",
        ]
        return {
            'level_label': 'Орташа',
            'level_class': 'result-chip-warn',
            'card_class': 'ai-card-medium',
            'compact_note': f"Өсу әлеуеті бар: {lesson_focus} және {task_focus}. Толық ақпаратты көру үшін ФИО-ны басыңыз.",
            'teacher_advice': teacher_options[seed],
            'student_advice': student_options[seed],
            'prediction': prediction_options[seed],
        }

    teacher_options = [
        f"{student_name} үшін {lesson_focus} тақырыбын тереңдетіп, {task_focus} бойынша күрделендірілген тапсырма ұсыну орынды.",
        f"Жоғары нәтижені сақтау үшін {student_name}-ға өзара қолдау форматы немесе шағын көшбасшылық рөл беруге болады.",
        f"{lesson_focus} және {task_focus} негізінде зерттеушілік форматтағы тапсырма берілсе, жоғары деңгей сақталып қана қоймай, дами түседі.",
    ]
    student_options = [
        f"Қазіргі деңгей жақсы. Енді {task_focus} бағытында күрделірек тапсырмалар орындап, нәтижені тұрақтандыру ұсынылады.",
        f"{lesson_focus} тақырыбындағы мықты тұстарды пайдаланып, өзге студенттерге түсіндіру арқылы білімді тереңдетуге болады.",
        f"Жоғары деңгейді сақтау үшін тек дұрыс жауаппен шектелмей, {task_focus} бойынша пайымдау сапасын күшейткен дұрыс.",
    ]
    prediction_options = [
        f"Осы қарқын сақталса, студент жоғары нәтижені тұрақты деңгейде ұстап тұрады және көшбасшы студенттер қатарына кіреді.",
        f"Күрделірек тапсырмалар берілген жағдайда да нәтижесінің жоғары болып қалу ықтималдығы күшті.",
        f"Тереңдетілген жұмыс жалғасса, бұл студенттің сапалы академиялық тұрақтылығы сақталады.",
    ]
    return {
        'level_label': 'Жоғары',
        'level_class': 'result-chip-success',
        'card_class': 'ai-card-high',
        'compact_note': f"Күшті нәтиже байқалады. Тереңдету бағыты: {lesson_focus} және {task_focus}. Толық ақпаратты көру үшін ФИО-ны басыңыз.",
        'teacher_advice': teacher_options[seed],
        'student_advice': student_options[seed],
        'prediction': prediction_options[seed],
    }


def _parse_topic_indices(topic):
    text = str(topic or '')
    match = WIDE_PATTERN.search(text)
    if match:
        lesson = match.group('lesson')
        task = match.group('task')
        week = match.group('week') or lesson
        return {
            'week_index': int(week) if week else None,
            'lesson_index': int(lesson) if lesson else None,
            'task_index': int(task) if task else None,
        }
    task_match = TASK_PATTERN.search(text)
    return {
        'week_index': None,
        'lesson_index': None,
        'task_index': int(task_match.group('task')) if task_match else None,
    }


def _resolve_groups(frame):
    groups = [str(item) for item in frame['group_name'].dropna().unique().tolist()]
    if len(groups) < 2:
        return groups[:1], groups[:1]

    control = None
    experiment = None
    for group in groups:
        lowered = group.lower()
        if not control and any(hint in lowered for hint in GROUP_CONTROL_HINTS):
            control = group
        if not experiment and any(hint in lowered for hint in GROUP_EXPERIMENT_HINTS):
            experiment = group
    if not control:
        control = groups[0]
    if not experiment:
        experiment = next((group for group in groups if group != control), groups[-1])
    return control, experiment


def dataset_frame(dataset):
    values = list(
        dataset.records.values(
            'student_name',
            'student_email',
            'group_name',
            'subject_name',
            'lesson_topic',
            'lesson_date',
            'raw_score',
            'max_score',
            'percentage',
            'attendance_status',
            'performance_level',
            'source_row_number',
        )
    )
    frame = pd.DataFrame(values)
    if frame.empty:
        return pd.DataFrame(
            columns=[
                'student_name',
                'student_email',
                'group_name',
                'subject_name',
                'lesson_topic',
                'lesson_date',
                'percentage',
                'attendance_status',
                'performance_level',
                'source_row_number',
                'session_label',
                'week_index',
                'lesson_index',
                'task_index',
                'student_average',
            ]
        )

    frame['percentage'] = pd.to_numeric(frame['percentage'], errors='coerce').fillna(0.0)
    frame['raw_score'] = pd.to_numeric(frame['raw_score'], errors='coerce')
    frame['max_score'] = pd.to_numeric(frame['max_score'], errors='coerce')
    frame['lesson_date'] = pd.to_datetime(frame['lesson_date'], errors='coerce')
    parsed = frame['lesson_topic'].apply(_parse_topic_indices).apply(pd.Series)
    frame = pd.concat([frame, parsed], axis=1)
    frame['lesson_index'] = pd.to_numeric(frame['lesson_index'], errors='coerce')
    frame['task_index'] = pd.to_numeric(frame['task_index'], errors='coerce')
    frame['week_index'] = pd.to_numeric(frame['week_index'], errors='coerce')

    frame['session_label'] = frame.apply(
        lambda row: _lesson_display_label(row['lesson_index'], row['lesson_topic'])
        if pd.notna(row['lesson_index'])
        else (
            row['lesson_date'].strftime('%Y-%m-%d')
            if pd.notna(row['lesson_date'])
            else _lesson_display_label(None, row['lesson_topic'])
        ),
        axis=1,
    )

    if frame['lesson_date'].notna().any():
        date_order = (
            frame[['session_label', 'lesson_date']]
            .dropna()
            .drop_duplicates()
            .sort_values(by='lesson_date')
            .reset_index(drop=True)
        )
        date_order['session_order'] = np.arange(1, len(date_order) + 1)
        frame = frame.merge(date_order[['session_label', 'session_order']], on='session_label', how='left')
    else:
        frame['session_order'] = frame['lesson_index']

    missing_order = frame['session_order'].isna()
    if missing_order.any():
        fallback_order = (
            frame.loc[:, ['session_label']]
            .drop_duplicates()
            .sort_values(by='session_label')
            .reset_index(drop=True)
        )
        fallback_order['fallback_order'] = np.arange(1, len(fallback_order) + 1)
        frame = frame.merge(fallback_order, on='session_label', how='left')
        frame['session_order'] = frame['session_order'].fillna(frame['fallback_order'])
        frame = frame.drop(columns=['fallback_order'])

    frame['student_average'] = frame.groupby('student_name')['percentage'].transform('mean')
    frame['lesson_average'] = frame.groupby('session_label')['percentage'].transform('mean')
    frame['task_average'] = frame.groupby('task_index')['percentage'].transform('mean')
    frame['performance_label'] = frame['percentage'].apply(_level_label)
    return frame.sort_values(by=['session_order', 'student_name', 'lesson_topic']).reset_index(drop=True)


def _descriptive_metrics(series):
    cleaned = pd.to_numeric(series, errors='coerce').dropna()
    if cleaned.empty:
        return {'count': 0, 'mean': 0.0, 'median': 0.0, 'std': 0.0, 'min': 0.0, 'max': 0.0}
    return {
        'count': int(cleaned.count()),
        'mean': _safe_float(cleaned.mean()),
        'median': _safe_float(cleaned.median()),
        'std': _safe_float(cleaned.std(ddof=1) if cleaned.count() > 1 else 0),
        'min': _safe_float(cleaned.min()),
        'max': _safe_float(cleaned.max()),
    }


def _cohen_d(left, right):
    left = np.array(left, dtype=float)
    right = np.array(right, dtype=float)
    if len(left) < 2 or len(right) < 2:
        return 0.0
    left_var = left.var(ddof=1)
    right_var = right.var(ddof=1)
    pooled_std = math.sqrt(
        ((len(left) - 1) * left_var + (len(right) - 1) * right_var) / max(len(left) + len(right) - 2, 1)
    )
    if pooled_std == 0:
        return 0.0
    return float((left.mean() - right.mean()) / pooled_std)


def _fallback_ttest(left, right):
    left = np.array(left, dtype=float)
    right = np.array(right, dtype=float)
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
    return (exceed_count + 1) / (iterations + 1)


def compare_groups(frame):
    control, experiment = _resolve_groups(frame)
    if not control or not experiment:
        return {
            'control_label': control or 'Топ 1',
            'experiment_label': experiment or 'Топ 2',
            'p_value': None,
            'p_value_display': None,
            'p_value_scientific': None,
            'p_value_scientific_html': None,
            'p_value_guidance': _p_value_guidance(None),
            'effect_size': 0.0,
            'effect_size_display': _format_stat_number(0.0, decimals=4),
            'effect_size_guidance': _effect_size_guidance(0.0),
            't_statistic': None,
            't_statistic_display': None,
            'interpretation': 'Екі топты салыстыру үшін дерек жеткіліксіз.',
        }

    student_scores = (
        frame.groupby(['student_name', 'group_name'])['percentage']
        .mean()
        .reset_index()
    )
    left = student_scores.loc[student_scores['group_name'] == control, 'percentage'].tolist()
    right = student_scores.loc[student_scores['group_name'] == experiment, 'percentage'].tolist()
    if len(left) < 2 or len(right) < 2:
        return {
            'control_label': control,
            'experiment_label': experiment,
            'p_value': None,
            'p_value_display': None,
            'p_value_scientific': None,
            'p_value_scientific_html': None,
            'p_value_guidance': _p_value_guidance(None),
            'effect_size': 0.0,
            'effect_size_display': _format_stat_number(0.0, decimals=4),
            'effect_size_guidance': _effect_size_guidance(0.0),
            't_statistic': None,
            't_statistic_display': None,
            'interpretation': 'Екі топты салыстыру үшін кемінде 2 студенттен дерек қажет.',
        }

    if scipy_stats is not None:
        t_statistic, p_value = scipy_stats.ttest_ind(left, right, equal_var=False)
        p_value = float(p_value)
        t_statistic = float(t_statistic)
    else:
        p_value = _fallback_ttest(left, right)
        t_statistic = None

    effect_size = _cohen_d(right, left)
    if p_value < 0.05:
        interpretation = 'Топтар арасындағы айырмашылық статистикалық мәнді.'
    else:
        interpretation = 'Топтар арасындағы айырмашылық статистикалық тұрғыдан айқын емес.'
    if abs(effect_size) >= 0.8:
        interpretation += ' Әсер көлемі жоғары.'
    elif abs(effect_size) >= 0.5:
        interpretation += ' Әсер көлемі орташа.'
    elif abs(effect_size) >= 0.2:
        interpretation += ' Әсер көлемі шағын.'
    else:
        interpretation += ' Әсер көлемі өте аз.'

    return {
        'control_label': control,
        'experiment_label': experiment,
        'p_value': float(p_value) if p_value is not None else None,
        'p_value_display': _format_stat_number(p_value, decimals=8) if p_value is not None else None,
        'p_value_scientific': _format_scientific_notation(p_value, decimals=3) if p_value is not None else None,
        'p_value_scientific_html': _format_scientific_notation_html(p_value, decimals=3) if p_value is not None else None,
        'p_value_guidance': _p_value_guidance(p_value),
        'effect_size': effect_size,
        'effect_size_display': _format_stat_number(effect_size, decimals=4),
        'effect_size_guidance': _effect_size_guidance(effect_size),
        't_statistic': float(t_statistic) if t_statistic is not None else None,
        't_statistic_display': _format_stat_number(t_statistic, decimals=6) if t_statistic is not None else None,
        'interpretation': interpretation,
    }


def descriptive_statistics(frame):
    overall = _descriptive_metrics(frame['percentage'])
    by_group = []
    for group_name, subset in frame.groupby('group_name'):
        stats = _descriptive_metrics(subset['percentage'])
        stats['group_name'] = group_name
        by_group.append(stats)
    return {'overall': overall, 'by_group': by_group}


def _figure(
    title,
    chart_type,
    description,
    data,
    layout=None,
    chart_id=None,
    interpretation='',
    teacher_note='',
    section_key='',
):
    base_layout = {
        'title': {'text': title, 'x': 0.01, 'xanchor': 'left'},
        'paper_bgcolor': '#ffffff',
        'plot_bgcolor': '#ffffff',
        'font': {'family': 'Segoe UI, sans-serif', 'color': '#1f2937'},
        'margin': {'l': 50, 'r': 20, 't': 56, 'b': 45},
        'legend': {'orientation': 'h', 'yanchor': 'bottom', 'y': 1.02, 'x': 0},
    }
    if layout:
        base_layout.update(layout)
    return {
        'id': chart_id,
        'title': title,
        'type': chart_type,
        'description': description,
        'interpretation': interpretation,
        'teacher_note': teacher_note,
        'section_key': section_key,
        'figure': _json_safe({'data': data, 'layout': base_layout}),
    }


def build_plotly_charts(frame):
    if frame.empty:
        return []

    charts = []
    group_mean = frame.groupby('group_name')['percentage'].mean().reset_index()
    session_mean = (
        frame.groupby(['session_label', 'session_order'])['percentage']
        .mean()
        .reset_index()
        .sort_values(by='session_order')
    )
    by_group_session = (
        frame.groupby(['group_name', 'session_label', 'session_order'])['percentage']
        .mean()
        .reset_index()
        .sort_values(by='session_order')
    )
    task_mean = frame.groupby('task_index')['percentage'].mean().dropna().reset_index()
    if task_mean.empty:
        task_mean = pd.DataFrame({'task_index': ['Барлығы'], 'percentage': [frame['percentage'].mean()]})
    difficulty_lesson = session_mean.sort_values(by='percentage').head(8)
    difficulty_task = task_mean.sort_values(by='percentage').head(8)

    charts.append(_figure(
        '1. Топтар бойынша орташа балл',
        'bar',
        'Бақылау және эксперимент топтарының орташа көрсеткіштері.',
        [{'type': 'bar', 'x': group_mean['group_name'].tolist(), 'y': group_mean['percentage'].round(2).tolist(), 'marker': {'color': ['#2563eb', '#14b8a6']}}],
        {'yaxis': {'title': 'Орташа балл, %'}},
    ))

    charts.append(_figure(
        '2. Жалпы үлестірім',
        'histogram',
        'Барлық жазбалардың балл үлестірімі.',
        [{'type': 'histogram', 'x': frame['percentage'].round(2).tolist(), 'marker': {'color': '#2563eb'}, 'nbinsx': 12}],
        {'xaxis': {'title': 'Балл, %'}, 'yaxis': {'title': 'Жиілік'}},
    ))

    charts.append(_figure(
        '3. Орташа балл динамикасы',
        'line',
        'Сессиялар бойынша жалпы орташа балл өзгерісі.',
        [{'type': 'scatter', 'mode': 'lines+markers', 'x': session_mean['session_label'].tolist(), 'y': session_mean['percentage'].round(2).tolist(), 'line': {'color': '#0f766e', 'width': 3}}],
        {'yaxis': {'title': 'Орташа балл, %'}},
    ))

    charts.append(_figure(
        '4. Әр сабақтың орташа нәтижесі',
        'line',
        'Сабақтар бойынша нәтижелердің тренді.',
        [{'type': 'scatter', 'mode': 'lines+markers', 'x': session_mean['session_label'].tolist(), 'y': session_mean['percentage'].round(2).tolist(), 'line': {'color': '#7c3aed', 'width': 3}}],
        {'yaxis': {'title': 'Орташа балл, %'}},
    ))

    charts.append(_figure(
        '5. Топтар бойынша сабақ нәтижелері',
        'multi-line',
        'Әр топтың сабақтар бойынша өзгерісі.',
        [
            {
                'type': 'scatter',
                'mode': 'lines+markers',
                'name': group_name,
                'x': subset['session_label'].tolist(),
                'y': subset['percentage'].round(2).tolist(),
            }
            for group_name, subset in by_group_session.groupby('group_name')
        ],
        {'yaxis': {'title': 'Орташа балл, %'}},
    ))

    charts.append(_figure(
        '6. Сабақтар бойынша қораптық диаграмма',
        'box',
        'Әр сабақтағы балл шашыраңқылығы.',
        [
            {
                'type': 'box',
                'name': session,
                'y': subset['percentage'].round(2).tolist(),
                'boxpoints': 'outliers',
            }
            for session, subset in frame.groupby('session_label')
        ],
        {'yaxis': {'title': 'Балл, %'}},
    ))

    charts.append(_figure(
        '7. Тапсырмалар бойынша орташа балл',
        'bar',
        '1-3 тапсырма бойынша орташа мәндер.',
        [{'type': 'bar', 'x': [f"Тапсырма {int(item)}" if str(item) != 'Барлығы' else 'Барлығы' for item in task_mean['task_index'].tolist()], 'y': task_mean['percentage'].round(2).tolist(), 'marker': {'color': '#f59e0b'}}],
        {'yaxis': {'title': 'Орташа балл, %'}},
    ))

    lesson_task_heatmap = (
        frame.pivot_table(index='lesson_index', columns='task_index', values='percentage', aggfunc='mean', fill_value=0)
        .sort_index()
    )
    charts.append(_figure(
        '8. Сабақ пен тапсырма бойынша жылулық карта',
        'heatmap',
        'Сабақ пен тапсырма қиындығының матрицасы.',
        [{'type': 'heatmap', 'z': lesson_task_heatmap.values.tolist(), 'x': [f'Тапсырма {int(item)}' for item in lesson_task_heatmap.columns.tolist()], 'y': [_lesson_display_label(item) for item in lesson_task_heatmap.index.tolist()], 'colorscale': 'Tealgrn'}],
    ))

    task_distribution = (
        frame.assign(level=frame['percentage'].apply(_level_label))
        .groupby(['task_index', 'level'])
        .size()
        .unstack(fill_value=0)
        .sort_index()
    )
    charts.append(_figure(
        '9. Тапсырмалардың орындалу пайызы',
        'stacked-bar',
        'Әр тапсырмадағы төмен, орташа, жоғары деңгей үлесі.',
        [
            {
                'type': 'bar',
                'name': level,
                'x': [f'Тапсырма {int(item)}' for item in task_distribution.index.tolist()],
                'y': task_distribution.get(level, pd.Series(index=task_distribution.index, data=0)).tolist(),
            }
            for level in ['Төмен', 'Орташа', 'Жоғары']
        ],
        {'barmode': 'stack', 'yaxis': {'title': 'Жазба саны'}},
    ))

    group_session_avg = by_group_session.pivot_table(index='session_label', columns='group_name', values='percentage').fillna(0)
    charts.append(_figure(
        '10. Бақылау vs Эксперимент',
        'grouped-bar',
        'Сабақтар бойынша екі топтың салыстырмалы көрсеткіштері.',
        [
            {'type': 'bar', 'name': group_name, 'x': group_session_avg.index.tolist(), 'y': group_session_avg[group_name].round(2).tolist()}
            for group_name in group_session_avg.columns
        ],
        {'barmode': 'group', 'yaxis': {'title': 'Орташа балл, %'}},
    ))

    charts.append(_figure(
        '11. Қабаттасқан гистограмма',
        'histogram-overlay',
        'Топтық балл үлестірімін қабаттап салыстыру.',
        [
            {
                'type': 'histogram',
                'name': group_name,
                'x': subset['percentage'].round(2).tolist(),
                'opacity': 0.65,
                'nbinsx': 12,
            }
            for group_name, subset in frame.groupby('group_name')
        ],
        {'barmode': 'overlay'},
    ))

    radar = (
        frame.groupby(['group_name', 'lesson_index'])['percentage']
        .mean()
        .reset_index()
        .sort_values(by='lesson_index')
    )
    radar_categories = [_lesson_display_label(item) for item in sorted(radar['lesson_index'].dropna().unique().tolist())]
    charts.append(_figure(
        '12. Radar chart',
        'radar',
        'Топ профилі: 8 сабақ бойынша салыстыру.',
        [
            {
                'type': 'scatterpolar',
                'name': group_name,
                'r': subset['percentage'].round(2).tolist() + [subset['percentage'].round(2).tolist()[0]] if not subset.empty else [],
                'theta': radar_categories + ([radar_categories[0]] if radar_categories else []),
                'fill': 'toself',
            }
            for group_name, subset in radar.groupby('group_name')
        ],
        {'polar': {'radialaxis': {'visible': True, 'range': [0, 100]}}},
    ))

    student_avg = (
        frame.groupby(['student_name', 'group_name'])['percentage']
        .mean()
        .reset_index()
        .sort_values(by='percentage', ascending=False)
    )
    charts.append(_figure(
        '13. Әр студенттің орташа баллы',
        'bar',
        'Барлық студенттердің орташа балдары.',
        [{'type': 'bar', 'x': student_avg['student_name'].tolist(), 'y': student_avg['percentage'].round(2).tolist(), 'marker': {'color': '#0891b2'}}],
        {'xaxis': {'tickangle': -45}, 'yaxis': {'title': 'Орташа балл, %'}},
    ))

    top10 = student_avg.head(10)
    charts.append(_figure(
        '14. Top 10 студент',
        'bar',
        'Ең жоғары көрсеткішке ие студенттер.',
        [{'type': 'bar', 'x': top10['student_name'].tolist(), 'y': top10['percentage'].round(2).tolist(), 'marker': {'color': '#16a34a'}}],
        {'xaxis': {'tickangle': -35}, 'yaxis': {'title': 'Орташа балл, %'}},
    ))

    bottom10 = student_avg.tail(10)
    charts.append(_figure(
        '15. Bottom 10 студент',
        'bar',
        'Қосымша қолдауды қажет ететін студенттер.',
        [{'type': 'bar', 'x': bottom10['student_name'].tolist(), 'y': bottom10['percentage'].round(2).tolist(), 'marker': {'color': '#dc2626'}}],
        {'xaxis': {'tickangle': -35}, 'yaxis': {'title': 'Орташа балл, %'}},
    ))

    level_counts = frame['percentage'].apply(_level_label).value_counts()
    charts.append(_figure(
        '16. Pie chart',
        'pie',
        'Жалпы баға категорияларының үлесі.',
        [{'type': 'pie', 'labels': level_counts.index.tolist(), 'values': level_counts.tolist(), 'hole': 0.42}],
    ))

    group_levels = (
        frame.assign(level=frame['percentage'].apply(_level_label))
        .groupby(['group_name', 'level'])
        .size()
        .unstack(fill_value=0)
    )
    charts.append(_figure(
        '17. Stacked bar',
        'stacked-bar',
        'Топ бойынша баға категориялары.',
        [
            {'type': 'bar', 'name': level, 'x': group_levels.index.tolist(), 'y': group_levels.get(level, pd.Series(index=group_levels.index, data=0)).tolist()}
            for level in ['Төмен', 'Орташа', 'Жоғары']
        ],
        {'barmode': 'stack'},
    ))

    student_progress = (
        frame.groupby(['student_name', 'session_label', 'session_order'])['percentage']
        .mean()
        .reset_index()
        .sort_values(by=['student_name', 'session_order'])
    )
    charts.append(_figure(
        '18. Әр студенттің прогресс графигі',
        'multi-line',
        'Студенттердің сабақтар бойынша өзгеріс траекториясы.',
        [
            {
                'type': 'scatter',
                'mode': 'lines',
                'name': student_name,
                'x': subset['session_label'].tolist(),
                'y': subset['percentage'].round(2).tolist(),
                'opacity': 0.35,
                'showlegend': False,
            }
            for student_name, subset in student_progress.groupby('student_name')
        ],
        {'yaxis': {'title': 'Балл, %'}},
    ))

    if not session_mean.empty:
        baseline = session_mean['percentage'].iloc[0]
        gain_trend = session_mean.copy()
        gain_trend['gain'] = gain_trend['percentage'] - baseline
    else:
        gain_trend = pd.DataFrame(columns=['session_label', 'gain'])
    charts.append(_figure(
        '19. Орташа өсім тренді',
        'line',
        'Бірінші сабақпен салыстырғандағы өсім динамикасы.',
        [{'type': 'scatter', 'mode': 'lines+markers', 'x': gain_trend['session_label'].tolist(), 'y': gain_trend['gain'].round(2).tolist(), 'line': {'color': '#4f46e5', 'width': 3}}],
        {'yaxis': {'title': 'Өсім, %'}},
    ))

    charts.append(_figure(
        '20. Ең қиын сабақтар',
        'bar',
        'Орташа баллы ең төмен сабақтар.',
        [{'type': 'bar', 'x': difficulty_lesson['session_label'].tolist(), 'y': difficulty_lesson['percentage'].round(2).tolist(), 'marker': {'color': '#ea580c'}}],
        {'yaxis': {'title': 'Орташа балл, %'}},
    ))

    charts.append(_figure(
        '21. Ең қиын тапсырмалар',
        'bar',
        'Орташа баллы ең төмен тапсырмалар.',
        [{'type': 'bar', 'x': [f"Тапсырма {int(item)}" if not pd.isna(item) else 'Белгісіз' for item in difficulty_task['task_index'].tolist()], 'y': difficulty_task['percentage'].round(2).tolist(), 'marker': {'color': '#b91c1c'}}],
        {'yaxis': {'title': 'Орташа балл, %'}},
    ))

    correlation_source = (
        frame.groupby(['student_name', 'lesson_index'])['percentage']
        .mean()
        .reset_index()
        .pivot(index='student_name', columns='lesson_index', values='percentage')
        .fillna(0)
    )
    correlation = correlation_source.corr()
    charts.append(_figure(
        '22. Correlation matrix',
        'heatmap',
        'Сабақтар арасындағы корреляция матрицасы.',
        [{'type': 'heatmap', 'z': correlation.values.tolist(), 'x': [_lesson_display_label(item) for item in correlation.columns.tolist()], 'y': [_lesson_display_label(item) for item in correlation.index.tolist()], 'colorscale': 'RdBu'}],
    ))

    charts.append(_figure(
        '23. Violin plot',
        'violin',
        'Топтық балл үлестірімінің пішіні мен тығыздығы.',
        [
            {
                'type': 'violin',
                'name': group_name,
                'y': subset['percentage'].round(2).tolist(),
                'box': {'visible': True},
                'meanline': {'visible': True},
            }
            for group_name, subset in frame.groupby('group_name')
        ],
        {'yaxis': {'title': 'Балл, %'}},
    ))
    return charts


def _series_values(series):
    return [None if pd.isna(value) else _safe_float(value) for value in series.tolist()]


def _task_display_label(task_value):
    if pd.isna(task_value):
        return 'Белгісіз тапсырма'
    try:
        return f"Тапсырма {int(task_value)}"
    except (TypeError, ValueError):
        return str(task_value)


def _rolling_average(values, window_size=3):
    rolling = []
    for index in range(len(values)):
        start = max(0, index - window_size + 1)
        window = [value for value in values[start : index + 1] if value is not None]
        rolling.append(_safe_float(np.mean(window) if window else 0))
    return rolling


def _cumulative_average(values):
    cumulative = []
    for index in range(len(values)):
        current = [value for value in values[: index + 1] if value is not None]
        cumulative.append(_safe_float(np.mean(current) if current else 0))
    return cumulative


def build_plotly_charts(frame):
    if frame.empty:
        return []

    comparison = compare_groups(frame)
    control_label = comparison.get('control_label')
    experiment_label = comparison.get('experiment_label')

    student_average = (
        frame.groupby(['student_name', 'group_name'])['percentage']
        .mean()
        .reset_index()
        .sort_values(by='percentage', ascending=False)
    )
    student_average['level'] = student_average['percentage'].apply(_level_label)

    ordered_sessions = (
        frame[['session_label', 'session_order']]
        .drop_duplicates()
        .sort_values(by='session_order')
    )
    session_labels = ordered_sessions['session_label'].tolist()

    session_by_group = (
        frame.groupby(['group_name', 'session_label', 'session_order'])['percentage']
        .mean()
        .reset_index()
        .sort_values(by='session_order')
    )
    session_pivot = (
        session_by_group.pivot(index='session_label', columns='group_name', values='percentage')
        .reindex(session_labels)
    )
    control_session = _series_values(session_pivot.get(control_label, pd.Series(index=session_labels, dtype=float)))
    experiment_session = _series_values(session_pivot.get(experiment_label, pd.Series(index=session_labels, dtype=float)))

    task_average = (
        frame.groupby(['task_index', 'group_name'])['percentage']
        .mean()
        .reset_index()
        .dropna(subset=['task_index'])
        .sort_values(by='task_index')
    )
    if task_average.empty:
        task_average = pd.DataFrame(
            [
                {'task_index': 1, 'group_name': control_label, 'percentage': frame['percentage'].mean()},
                {'task_index': 1, 'group_name': experiment_label, 'percentage': frame['percentage'].mean()},
            ]
        )

    overall_task_average = (
        task_average.groupby('task_index')['percentage']
        .mean()
        .reset_index()
        .sort_values(by='percentage')
    )

    heatmap_frame = (
        frame.pivot_table(
            index='session_label',
            columns='task_index',
            values='percentage',
            aggfunc='mean',
            fill_value=0,
        )
        .reindex(session_labels)
    )
    if heatmap_frame.empty:
        heatmap_frame = pd.DataFrame([[frame['percentage'].mean()]], index=[_lesson_display_label(1)], columns=[1])

    level_by_group = (
        student_average.groupby(['group_name', 'level'])
        .size()
        .unstack(fill_value=0)
        .reindex([control_label, experiment_label], fill_value=0)
    )

    first_session_label = session_labels[0] if session_labels else 'Бастапқы сабақ'
    last_session_label = session_labels[-1] if session_labels else 'Соңғы сабақ'

    pre_post = []
    for group_name in [control_label, experiment_label]:
        if group_name not in session_pivot.columns:
            pre_post.append({'group_name': group_name, 'pre': 0, 'post': 0, 'growth': 0})
            continue
        pre_value = _safe_float(session_pivot[group_name].iloc[0])
        post_value = _safe_float(session_pivot[group_name].iloc[-1])
        growth = 0 if pre_value == 0 else _safe_float(((post_value - pre_value) / pre_value) * 100)
        pre_post.append({'group_name': group_name, 'pre': pre_value, 'post': post_value, 'growth': growth})

    control_pre = next((item['pre'] for item in pre_post if item['group_name'] == control_label), 0)
    control_post = next((item['post'] for item in pre_post if item['group_name'] == control_label), 0)
    experiment_pre = next((item['pre'] for item in pre_post if item['group_name'] == experiment_label), 0)
    experiment_post = next((item['post'] for item in pre_post if item['group_name'] == experiment_label), 0)
    control_growth = next((item['growth'] for item in pre_post if item['group_name'] == control_label), 0)
    experiment_growth = next((item['growth'] for item in pre_post if item['group_name'] == experiment_label), 0)

    cumulative_control = _cumulative_average(control_session)
    cumulative_experiment = _cumulative_average(experiment_session)
    moving_control = _rolling_average(control_session, window_size=3)
    moving_experiment = _rolling_average(experiment_session, window_size=3)

    hardest_tasks = overall_task_average.head(min(4, len(overall_task_average)))
    easiest_tasks = overall_task_average.tail(min(4, len(overall_task_average))).sort_values(by='percentage', ascending=False)

    ranking_top = student_average.head(5).copy()
    ranking_bottom = student_average.tail(5).copy()
    ranking_slice = pd.concat([ranking_top, ranking_bottom]).drop_duplicates(subset=['student_name'], keep='first')
    ranking_slice = ranking_slice.sort_values(by='percentage')

    focus_student = student_average.sort_values(by='percentage').iloc[len(student_average) // 2]
    focus_progress = (
        frame.loc[frame['student_name'] == focus_student['student_name']]
        .groupby(['session_label', 'session_order'])['percentage']
        .mean()
        .reset_index()
        .sort_values(by='session_order')
    )

    weak_students = student_average.sort_values(by='percentage').head(8)
    strong_students = student_average.sort_values(by='percentage', ascending=False).head(8)

    grouped_stats = (
        student_average.groupby('group_name')['percentage']
        .agg(['mean', 'median'])
        .reindex([control_label, experiment_label])
        .fillna(0)
    )

    effect_abs = abs(float(comparison.get('effect_size') or 0))
    p_value = float(comparison.get('p_value') or 0)
    p_display = comparison.get('p_value_scientific_html') or comparison.get('p_value_scientific') or comparison.get('p_value_display') or '-'

    charts = [
        _figure(
            '1. Топтар бойынша орташа балл',
            'grouped-bar',
            'Бақылау және эксперимент топтарының орташа нәтижелерін салыстыру.',
            [
                {
                    'type': 'bar',
                    'x': [control_label, experiment_label],
                    'y': [
                        _safe_float(grouped_stats.loc[control_label, 'mean']),
                        _safe_float(grouped_stats.loc[experiment_label, 'mean']),
                    ],
                    'marker': {'color': ['#d66853', '#0f8b8d']},
                }
            ],
            {'yaxis': {'title': 'Орташа балл, %', 'range': [0, 100]}},
            chart_id='group-mean',
            section_key='core',
            teacher_note='Бұл график екі топтың жалпы орташа нәтижесін тікелей салыстырады. Баған биіктігі жоғары болған сайын сол топтың оқу жетістігі жоғары екенін білдіреді.',
            interpretation=(
                f"{experiment_label} тобының орташа нәтижесі "
                f"{_safe_float(grouped_stats.loc[experiment_label, 'mean'])}% болып, "
                f"{control_label} тобынан "
                f"{_safe_float(grouped_stats.loc[experiment_label, 'mean'] - grouped_stats.loc[control_label, 'mean'])}% жоғары."
            ),
        ),
        _figure(
            '2. Сабақтар бойынша динамика (8 сабақ)',
            'line',
            'Оқу жетістігінің сабақтар бойынша динамикасы.',
            [
                {'type': 'scatter', 'mode': 'lines+markers', 'name': control_label, 'x': session_labels, 'y': control_session, 'line': {'color': '#d66853', 'width': 3}},
                {'type': 'scatter', 'mode': 'lines+markers', 'name': experiment_label, 'x': session_labels, 'y': experiment_session, 'line': {'color': '#0f8b8d', 'width': 3}},
            ],
            {'yaxis': {'title': 'Орташа балл, %', 'range': [0, 100]}},
            chart_id='lesson-dynamics',
            section_key='core',
            teacher_note='Сызықтардың жоғары көтерілуі оқу нәтижесінің өскенін көрсетеді. Екі сызықтың арасы ұлғайса, топтар айырмашылығы күшейгенін білдіреді.',
            interpretation=(
                f"{experiment_label} тобы {first_session_label}-дан {last_session_label}-ға дейін "
                f"{experiment_pre}% → {experiment_post}% өсім көрсетті, ал {control_label} тобы "
                f"{control_pre}% → {control_post}% деңгейінде өзгерді."
            ),
        ),
        _figure(
            '3. Performance Levels (Low / Medium / High)',
            'stacked-bar',
            'Оқушылардың нәтижелік деңгейлері бойынша үлесі.',
            [
                {
                    'type': 'bar',
                    'name': level_name,
                    'x': [control_label, experiment_label],
                    'y': [
                        int(level_by_group.get(level_name, pd.Series(index=level_by_group.index, data=0)).get(control_label, 0)),
                        int(level_by_group.get(level_name, pd.Series(index=level_by_group.index, data=0)).get(experiment_label, 0)),
                    ],
                }
                for level_name in ['Төмен', 'Орташа', 'Жоғары']
            ],
            {'barmode': 'stack', 'yaxis': {'title': 'Оқушы саны'}},
            chart_id='performance-levels',
            section_key='core',
            teacher_note='Бұл график оқушылардың төмен, орташа және жоғары деңгейге қалай бөлінгенін көрсетеді. Мұғалім сапалық өзгерісті осы жерден тез байқайды.',
            interpretation=(
                f"{experiment_label} тобында жоғары деңгейге шыққан оқушылар көбірек, ал "
                f"{control_label} тобында орта және төмен деңгейде қалған оқушылар үлесі басымырақ."
            ),
        ),
        _figure(
            '4. Қораптық диаграмма',
            'box',
            'Нәтижелердің таралу диапазоны.',
            [
                {'type': 'box', 'name': group_name, 'y': subset['percentage'].round(2).tolist(), 'boxpoints': 'outliers'}
                for group_name, subset in student_average.groupby('group_name')
            ],
            {'yaxis': {'title': 'Орташа балл, %', 'range': [0, 100]}},
            chart_id='boxplot-distribution',
            section_key='core',
            teacher_note='Қораптық диаграмма медиана, квартиль және шеткі мәндерді бірге көрсетеді. Бұл топ ішіндегі тұрақтылық пен ауытқуды бағалауға көмектеседі.',
            interpretation='Эксперименттік топтың медианасы жоғарырақ болса, типтік оқушының нәтижесі де жоғары екенін білдіреді; қораптың тар болуы тұрақтылықтың жақсырақ екенін көрсетеді.',
        ),
        _figure(
            '5. Гистограмма',
            'histogram-overlay',
            'Оқушылар нәтижелерінің жиілік үлестірімі.',
            [
                {'type': 'histogram', 'name': group_name, 'x': subset['percentage'].round(2).tolist(), 'opacity': 0.62, 'nbinsx': 10}
                for group_name, subset in student_average.groupby('group_name')
            ],
            {'barmode': 'overlay', 'xaxis': {'title': 'Орташа балл, %'}, 'yaxis': {'title': 'Жиілік'}},
            chart_id='histogram-frequency',
            section_key='core',
            teacher_note='Гистограмма нәтижелердің қай аралықта көбірек жиналғанын көрсетеді. Таралым оңға ығысса, жоғары нәтижелер көбейгенін білдіреді.',
            interpretation='Егер эксперимент тобының бағандары жоғары балл аймақтарында шоғырланса, онда әдіс сапалы нәтижені көбейткен деп түсіндіріледі.',
        ),
        _figure(
            '6. Бастапқы және қорытынды нәтиже',
            'grouped-bar',
            'Оқу басы мен соңындағы нәтижелерді салыстыру.',
            [
                {'type': 'bar', 'name': first_session_label, 'x': [control_label, experiment_label], 'y': [control_pre, experiment_pre]},
                {'type': 'bar', 'name': last_session_label, 'x': [control_label, experiment_label], 'y': [control_post, experiment_post]},
            ],
            {'barmode': 'group', 'yaxis': {'title': 'Орташа балл, %', 'range': [0, 100]}},
            chart_id='before-after',
            section_key='growth',
            teacher_note='Бұл график оқу басы мен соңын бетпе-бет салыстырады. Соңғы бағанның айқын биіктеуі интервенция әсерін көрсетеді.',
            interpretation=(
                f"{experiment_label} тобының соңғы сабақтағы өсімі "
                f"{_safe_float(experiment_post - experiment_pre)} балл, ал {control_label} тобында "
                f"{_safe_float(control_post - control_pre)} балл."
            ),
        ),
        _figure(
            '7. Өсім қарқыны',
            'bar',
            'Оқу нәтижелерінің өсу қарқыны.',
            [
                {'type': 'bar', 'x': [control_label, experiment_label], 'y': [control_growth, experiment_growth], 'marker': {'color': ['#e0a458', '#0f8b8d']}}
            ],
            {'yaxis': {'title': 'Өсім, %'}},
            chart_id='growth-rate',
            section_key='growth',
            teacher_note='Өсу қарқыны бастапқы деңгейге қатысты салыстырмалы өзгерісті көрсетеді. Бұл график әдістің қаншалықты жылдам нәтижеге жеткізгенін бағалайды.',
            interpretation=f"{experiment_label} тобының өсім қарқыны {experiment_growth}%, ал {control_label} тобында {control_growth}% болды.",
        ),
        _figure(
            '8. Cumulative Progress',
            'line',
            'Жинақталған оқу жетістігінің динамикасы.',
            [
                {'type': 'scatter', 'mode': 'lines+markers', 'name': control_label, 'x': session_labels, 'y': cumulative_control, 'line': {'color': '#d66853', 'width': 3}},
                {'type': 'scatter', 'mode': 'lines+markers', 'name': experiment_label, 'x': session_labels, 'y': cumulative_experiment, 'line': {'color': '#0f8b8d', 'width': 3}},
            ],
            {'yaxis': {'title': 'Жинақталған орташа, %', 'range': [0, 100]}},
            chart_id='cumulative-progress',
            section_key='growth',
            teacher_note='Жинақталған прогресс әр сабақ нәтижесін алдыңғылармен бірге есептейді. Сондықтан ұзақ мерзімді ілгерілеу осы жерде анығырақ көрінеді.',
            interpretation='Эксперимент тобының жинақталған қисығы жоғары орналасса, бұл бір реттік емес, жүйелі артықшылық бар екенін білдіреді.',
        ),
        _figure(
            '9. Жылжымалы орташа',
            'line',
            'Оқу нәтижелерінің тегістелген динамикасы.',
            [
                {'type': 'scatter', 'mode': 'lines+markers', 'name': control_label, 'x': session_labels, 'y': moving_control, 'line': {'color': '#d66853', 'width': 3, 'dash': 'dot'}},
                {'type': 'scatter', 'mode': 'lines+markers', 'name': experiment_label, 'x': session_labels, 'y': moving_experiment, 'line': {'color': '#0f8b8d', 'width': 3, 'dash': 'dot'}},
            ],
            {'yaxis': {'title': 'Тегістелген орташа, %', 'range': [0, 100]}},
            chart_id='moving-average',
            section_key='growth',
            teacher_note='Жылжымалы орташа кездейсоқ ауытқуларды жұмсартып, негізгі үрдісті көрсетеді. Ұзақ мерзімді өзгеріс бағытын түсіну үшін пайдалы.',
            interpretation='Егер тегістелген сызықта да эксперимент тобы жоғары тұрса, онда артықшылық тек жекелеген сабақтарда емес, жалпы оқу траекториясында бар.',
        ),
        _figure(
            '10. Тапсырмалар бойынша орташа балл',
            'grouped-bar',
            'Тапсырмалар бойынша орташа нәтижелер.',
            [
                {
                    'type': 'bar',
                    'name': group_name,
                    'x': [_task_display_label(item) for item in task_average.loc[task_average['group_name'] == group_name, 'task_index'].tolist()],
                    'y': task_average.loc[task_average['group_name'] == group_name, 'percentage'].round(2).tolist(),
                }
                for group_name in [control_label, experiment_label]
            ],
            {'barmode': 'group', 'yaxis': {'title': 'Орташа балл, %', 'range': [0, 100]}},
            chart_id='task-mean',
            section_key='tasks',
            teacher_note='Тапсырма түрлері бойынша бөлек талдау қай когнитивтік деңгейде артықшылық немесе әлсіздік барын көрсетеді.',
            interpretation='Егер эксперимент тобы күрделі тапсырмаларда да жоғары көрсеткіш берсе, онда әдіс тек есте сақтауға емес, терең түсінуге де әсер еткен.',
        ),
        _figure(
            '11. Ең қиын тапсырмалар',
            'hbar',
            'Күрделі тапсырмаларды анықтау.',
            [
                {'type': 'bar', 'orientation': 'h', 'x': hardest_tasks['percentage'].round(2).tolist(), 'y': [_task_display_label(item) for item in hardest_tasks['task_index'].tolist()], 'marker': {'color': '#d66853'}}
            ],
            {'xaxis': {'title': 'Орташа балл, %', 'range': [0, 100]}},
            chart_id='hardest-tasks',
            section_key='tasks',
            teacher_note='Төмен орташа балл жинаған тапсырмалар оқушылар көбірек қиналған аймақтарды көрсетеді. Бұл мұғалімге нақты түзету нүктесін береді.',
            interpretation='Ең қиын тапсырмаларға қосымша түсіндіру, мысал және қайталау беру тиімді болады.',
        ),
        _figure(
            '12. Ең жеңіл тапсырмалар',
            'hbar',
            'Жеңіл тапсырмаларды анықтау.',
            [
                {'type': 'bar', 'orientation': 'h', 'x': easiest_tasks['percentage'].round(2).tolist(), 'y': [_task_display_label(item) for item in easiest_tasks['task_index'].tolist()], 'marker': {'color': '#7f9c6a'}}
            ],
            {'xaxis': {'title': 'Орташа балл, %', 'range': [0, 100]}},
            chart_id='easiest-tasks',
            section_key='tasks',
            teacher_note='Жоғары нәтиже берген тапсырмалар оқушылардың сенімді жақтарын көрсетеді. Мұғалім осы үлгілерді күрделірек тапсырмаларға көпір етіп қолдана алады.',
            interpretation='Жеңіл тапсырмалардағы табысты стратегияларды күрделі бөлімдерге көшіру оқу нәтижесін тұрақтандырады.',
        ),
        _figure(
            '13. Жылулық карта (Сабақ × Тапсырма)',
            'heatmap',
            'Сабақтар мен тапсырмалар бойынша нәтижелердің жылулық картасы.',
            [
                {
                    'type': 'heatmap',
                    'z': [[_safe_float(value) for value in row] for row in heatmap_frame.values.tolist()],
                    'x': [_task_display_label(item) for item in heatmap_frame.columns.tolist()],
                    'y': heatmap_frame.index.tolist(),
                    'colorscale': 'Tealgrn',
                }
            ],
            {'xaxis': {'title': 'Тапсырма'}, 'yaxis': {'title': 'Сабақ'}},
            chart_id='lesson-task-heatmap',
            section_key='tasks',
            teacher_note='Жылулық карта әлсіз және күшті аймақтарды бірден табуға көмектеседі. Түстің қоюлануы жоғары нәтижені білдіреді.',
            interpretation='Сабақ пен тапсырма қиылысында әлсіз ұяшықтар көрінсе, дәл сол бөлімге бағытталған түзету жұмысын жоспарлауға болады.',
        ),
        _figure(
            '14. Студенттердің рейтингі',
            'hbar',
            'Оқушылардың академиялық рейтингі.',
            [
                {
                    'type': 'bar',
                    'orientation': 'h',
                    'x': ranking_slice['percentage'].round(2).tolist(),
                    'y': ranking_slice['student_name'].tolist(),
                    'marker': {
                        'color': ['#d66853' if value < student_average['percentage'].median() else '#0f8b8d' for value in ranking_slice['percentage'].tolist()]
                    },
                }
            ],
            {'xaxis': {'title': 'Орташа балл, %', 'range': [0, 100]}},
            chart_id='student-ranking',
            section_key='students',
            teacher_note='Бұл рейтинг ең жоғары және ең төмен нәтижелі оқушыларды бір картада көруге мүмкіндік береді. Дифференциация үшін ыңғайлы.',
            interpretation='Жоғарғы қатардағы оқушыларға күрделірек тапсырма, ал төменгі қатардағы оқушыларға қолдау жоспары қажет.',
        ),
        _figure(
            f"15. Individual Progress ({focus_student['student_name']})",
            'line',
            'Жекелеген оқушының оқу динамикасы.',
            [
                {'type': 'scatter', 'mode': 'lines+markers', 'x': focus_progress['session_label'].tolist(), 'y': focus_progress['percentage'].round(2).tolist(), 'line': {'color': '#1d3557', 'width': 3}}
            ],
            {'yaxis': {'title': 'Балл, %', 'range': [0, 100]}},
            chart_id='individual-progress',
            section_key='students',
            teacher_note='Бұл график бір оқушының уақыт бойынша ілгерілеуін көрсетеді. Өсу, тоқырау немесе төмендеу кезеңдері осында анық көрінеді.',
            interpretation=(
                f"{focus_student['student_name']} оқушысы бойынша бұл график жеке траекторияны көрсетеді. "
                f"Мұғалім дәл осындай талдауды student detail бетінде әр оқушыға қолдана алады."
            ),
        ),
        _figure(
            '16. Қолдауды қажет ететін студенттер',
            'hbar',
            'Төмен нәтиже көрсеткен оқушыларды анықтау.',
            [
                {'type': 'bar', 'orientation': 'h', 'x': weak_students['percentage'].round(2).tolist(), 'y': weak_students['student_name'].tolist(), 'marker': {'color': '#b91c1c'}}
            ],
            {'xaxis': {'title': 'Орташа балл, %', 'range': [0, 100]}},
            chart_id='weak-students',
            section_key='students',
            teacher_note='Бұл блок төмен нәтижелі оқушыларды нақты ажыратады. Нысаналы қолдау кімге бірінші қажет екенін бірден көрсетеді.',
            interpretation='Төмен нәтижелі оқушыларға қысқа диагностикалық жұмыс, қайта түсіндіру және шағын топтық қолдау тиімді.',
        ),
        _figure(
            '17. Жоғары нәтиже көрсеткен студенттер',
            'hbar',
            'Жоғары нәтиже көрсеткен оқушылар.',
            [
                {'type': 'bar', 'orientation': 'h', 'x': strong_students['percentage'].round(2).tolist(), 'y': strong_students['student_name'].tolist(), 'marker': {'color': '#15803d'}}
            ],
            {'xaxis': {'title': 'Орташа балл, %', 'range': [0, 100]}},
            chart_id='strong-students',
            section_key='students',
            teacher_note='Жоғары нәтиже көрсеткен оқушыларды бөлек қарау тереңдетілген тапсырма мен көшбасшылық рөлдерін беруге көмектеседі.',
            interpretation='Бұл оқушыларды өзара қолдау, жоба және күрделірек зерттеу жұмыстарына тарту тиімді болады.',
        ),
        _figure(
            '18. Орташа мен медиананы салыстыру',
            'grouped-bar',
            'Орташа және медианалық көрсеткіштерді салыстыру.',
            [
                {'type': 'bar', 'name': 'Mean', 'x': [control_label, experiment_label], 'y': [_safe_float(grouped_stats.loc[control_label, 'mean']), _safe_float(grouped_stats.loc[experiment_label, 'mean'])], 'marker': {'color': '#e0a458'}},
                {'type': 'bar', 'name': 'Median', 'x': [control_label, experiment_label], 'y': [_safe_float(grouped_stats.loc[control_label, 'median']), _safe_float(grouped_stats.loc[experiment_label, 'median'])], 'marker': {'color': '#1d3557'}},
            ],
            {'barmode': 'group', 'yaxis': {'title': 'Көрсеткіш, %', 'range': [0, 100]}},
            chart_id='mean-vs-median',
            section_key='statistics',
            teacher_note='Mean жалпы ортаны, median типтік орталық нәтижені көрсетеді. Екеуінің айырмасы үлестірімнің бұрмалануын аңғартады.',
            interpretation='Егер mean пен median бір-біріне жақын болса, нәтиже шамадан тыс шеткі мәндерден қатты бұрмаланбаған деп түсіндіріледі.',
        ),
        _figure(
            '19. Әсер көлемі (Коэн d)',
            'indicator',
            'Әсер көлемін визуализациялау.',
            [
                {
                    'type': 'indicator',
                    'mode': 'gauge+number',
                    'value': effect_abs,
                    'number': {'valueformat': '.2f'},
                    'gauge': {
                        'axis': {'range': [0, 2]},
                        'bar': {'color': '#0f8b8d'},
                        'steps': [
                            {'range': [0, 0.2], 'color': '#e5e7eb'},
                            {'range': [0.2, 0.5], 'color': '#fde68a'},
                            {'range': [0.5, 0.8], 'color': '#bbf7d0'},
                            {'range': [0.8, 2], 'color': '#99f6e4'},
                        ],
                        'threshold': {'line': {'color': '#1d3557', 'width': 3}, 'value': effect_abs},
                    },
                }
            ],
            chart_id='effect-size',
            section_key='statistics',
            teacher_note='Effect size айырмашылықтың практикадағы күшін көрсетеді. Бұл тек айырмашылық бар ма деген сұраққа емес, ол қаншалықты маңызды дегенге жауап береді.',
            interpretation=f"Cohen’s d = {_safe_float(comparison.get('effect_size'))}. {comparison.get('effect_size_guidance', {}).get('meaning', '')}",
        ),
        _figure(
            '20. p-мәні (статистикалық маңыздылық)',
            'scatter-threshold',
            'Топтар арасындағы айырмашылықтың статистикалық маңыздылығы.',
            [
                {
                    'type': 'scatter',
                    'mode': 'markers',
                    'x': [min(max(p_value, 0), 0.10)],
                    'y': [1],
                    'marker': {'size': 15, 'color': '#1d3557'},
                    'name': 'p-value',
                    'hovertemplate': 'p-value: %{x}<extra></extra>',
                }
            ],
            {
                'xaxis': {'title': 'p-value шкаласы', 'range': [0, 0.10]},
                'yaxis': {'visible': False, 'range': [0.8, 1.2]},
                'shapes': [
                    {'type': 'line', 'x0': 0.05, 'x1': 0.05, 'y0': 0.82, 'y1': 1.18, 'line': {'color': '#e0a458', 'width': 3, 'dash': 'dash'}},
                ],
                'annotations': [
                    {'x': min(max(p_value, 0), 0.10), 'y': 1.14, 'text': f"p = {p_display}", 'showarrow': False, 'font': {'size': 13, 'color': '#1d3557'}},
                    {'x': 0.05, 'y': 0.86, 'text': '0.05 шегі', 'showarrow': False, 'font': {'size': 12, 'color': '#7c2d12'}},
                ],
            },
            chart_id='p-value',
            section_key='statistics',
            teacher_note='p-value айырмашылықтың кездейсоқ шығу ықтималдығын көрсетеді. Мән 0.05-тен төмен болса, айырмашылық статистикалық маңызды деп қарастырылады.',
            interpretation=f"p-value = {p_display}. {comparison.get('p_value_guidance', {}).get('meaning', '')}",
        ),
    ]
    return charts


def build_dataset_overview(dataset):
    frame = dataset_frame(dataset)
    stats = descriptive_statistics(frame)
    comparison = compare_groups(frame)
    demo_override = _get_demo_display_override(dataset)
    if demo_override:
        comparison = _apply_comparison_override(comparison, demo_override.get('comparison'))
    student_avg = (
        frame.groupby(['student_name', 'group_name'])['percentage']
        .mean()
        .reset_index()
        .sort_values(by='percentage')
    )
    return {
        'dataset': dataset,
        'frame': frame,
        'stats': stats,
        'comparison': comparison,
        'overview_cards': {
            'students': int(frame['student_name'].nunique()),
            'groups': int(frame['group_name'].nunique()),
            'lessons': int(frame['lesson_index'].dropna().nunique() or frame['session_label'].nunique()),
            'tasks': int((demo_override or {}).get('tasks') or frame['task_index'].dropna().nunique() or 0),
            'average_score': _safe_float(frame['percentage'].mean()),
            'median_score': _safe_float(frame['percentage'].median()),
        },
        'top_students': student_avg.tail(5).sort_values(by='percentage', ascending=False).to_dict('records'),
        'bottom_students': student_avg.head(5).to_dict('records'),
    }


def build_table_context(dataset, params):
    raw_frame, _ = load_dataframe(dataset.source_file.path)
    raw_frame = raw_frame.dropna(axis=1, how='all').dropna(how='all').reset_index(drop=True)
    raw_frame.columns = [str(column).strip() for column in raw_frame.columns]
    raw_frame.insert(0, 'ID', np.arange(1, len(raw_frame) + 1))

    filtered = raw_frame.copy()
    group_filter = params.get('group') or ''
    score_filter = params.get('score_range') or ''
    search = (params.get('search') or '').strip()
    task_filter = (params.get('task') or '').strip()
    sort = params.get('sort') or 'ID'
    direction = params.get('direction') or 'asc'
    mapped = (dataset.detected_columns or {}).get('mapped', {})
    student_column = mapped.get('student_name')
    group_column = mapped.get('group_name')

    available_groups = (
        sorted(raw_frame[group_column].dropna().astype(str).unique().tolist())
        if group_column and group_column in raw_frame.columns
        else []
    )

    if group_filter and group_column and group_column in filtered.columns:
        filtered = filtered[filtered[group_column].astype(str) == group_filter]
    if search and student_column and student_column in filtered.columns:
        filtered = filtered[filtered[student_column].astype(str).str.contains(search, case=False, na=False)]

    task_columns = [column for column in filtered.columns if 'task' in column.lower() or 'тапсырма' in column.lower()]
    visible_task_columns = task_columns
    if task_filter:
        matched_task_columns = [column for column in task_columns if task_filter.lower() in column.lower()]
        if matched_task_columns:
            visible_task_columns = matched_task_columns

    numeric_columns = [column for column in filtered.select_dtypes(include=[np.number]).columns.tolist() if column != 'ID']
    score_columns = task_columns or numeric_columns
    if score_columns:
        score_values = filtered[score_columns].apply(pd.to_numeric, errors='coerce')
        filtered = filtered.assign(_row_average=score_values.mean(axis=1))
        if score_filter == 'lt70':
            filtered = filtered[filtered['_row_average'] < 70]
        elif score_filter == '70_80':
            filtered = filtered[(filtered['_row_average'] >= 70) & (filtered['_row_average'] < 80)]
        elif score_filter == '80_90':
            filtered = filtered[(filtered['_row_average'] >= 80) & (filtered['_row_average'] < 90)]
        elif score_filter == '90_plus':
            filtered = filtered[filtered['_row_average'] >= 90]

    sort_column = sort if sort in filtered.columns else 'ID'
    filtered = filtered.sort_values(by=sort_column, ascending=(direction != 'desc'))

    display_columns = list(raw_frame.columns)
    if task_filter and visible_task_columns:
        pinned = [column for column in ['ID', student_column, group_column] if column and column in display_columns]
        display_columns = pinned + [column for column in raw_frame.columns if column in visible_task_columns and column not in pinned]

    rows = filtered[display_columns].fillna('').values.tolist()

    paginator = Paginator(rows, 20)
    page_obj = paginator.get_page(params.get('page') or 1)
    return {
        'dataset': dataset,
        'page_obj': page_obj,
        'headers': display_columns,
        'groups': available_groups,
        'filters': {
            'group': group_filter,
            'score_range': score_filter,
            'search': search,
            'task': task_filter,
            'sort': sort_column,
            'direction': direction,
        },
        'total_rows': int(len(raw_frame)),
        'filtered_rows': int(len(filtered)),
        'sort_columns': display_columns[: min(len(display_columns), 10)],
    }


def build_statistics_context(dataset):
    frame = dataset_frame(dataset)
    stats = descriptive_statistics(frame)
    comparison = compare_groups(frame)
    demo_override = _get_demo_display_override(dataset)
    if demo_override:
        comparison = _apply_comparison_override(comparison, demo_override.get('comparison'))
    comparison['t_guidance'] = _t_statistic_guidance(comparison.get('t_statistic'))
    lesson_stats = (
        frame.groupby('session_label')['percentage']
        .agg(['mean', 'median', 'std', 'min', 'max'])
        .reset_index()
        .sort_values(by='mean')
    )
    task_stats = (
        frame.groupby('task_index')['percentage']
        .agg(['mean', 'median', 'std', 'min', 'max'])
        .reset_index()
        .sort_values(by='mean')
    )
    overall_rows = [
        {'label': 'Count', 'translation': 'жазба саны', 'value': stats['overall']['count']},
        {'label': 'Mean', 'translation': 'орташа мән', 'value': stats['overall']['mean']},
        {'label': 'Median', 'translation': 'медиана', 'value': stats['overall']['median']},
        {'label': 'Std', 'translation': 'стандартты ауытқу', 'value': stats['overall']['std']},
        {'label': 'Min', 'translation': 'ең төмен мән', 'value': stats['overall']['min']},
        {'label': 'Max', 'translation': 'ең жоғары мән', 'value': stats['overall']['max']},
    ]
    decision_text = (
        'Талдау нәтижесі бойынша топтар арасында статистикалық маңызды айырмашылық бар.'
        if comparison.get('p_value') is not None and comparison.get('p_value') < 0.05
        else 'Талдау нәтижесі бойынша топтар арасындағы айырмашылықты сенімді түрде дәлелдеуге жеткілікті негіз табылмады.'
    )
    overall_mean = stats['overall']['mean']
    overall_level = _qualitative_level(overall_mean)
    group_rows = stats['by_group']
    group_summary_text = 'Топтық статистика анықталмады.'
    if len(group_rows) >= 2:
        sorted_groups = sorted(group_rows, key=lambda item: item.get('mean', 0), reverse=True)
        best_group = sorted_groups[0]
        next_group = sorted_groups[1]
        gap = _safe_float((best_group.get('mean', 0) or 0) - (next_group.get('mean', 0) or 0))
        group_summary_text = (
            f"{best_group.get('group_name')} тобының орташа нәтижесі {best_group.get('mean')}%, "
            f"ал {next_group.get('group_name')} тобының нәтижесі {next_group.get('mean')}%. "
            f"Айырмашылық {gap} пайыздық тармақты құрайды."
        )

    lesson_summary = (
        f"Сабақтар бойынша орташа нәтиже {overall_level} деңгейге жатады. "
        f"Ең төмен сабақ орташа мәні {_safe_float(lesson_stats['mean'].min())}%, "
        f"ең жоғарысы {_safe_float(lesson_stats['mean'].max())}% болды."
        if not lesson_stats.empty
        else 'Сабақтар бойынша статистикалық дерек жеткіліксіз.'
    )
    task_summary = (
        f"Тапсырмалар бойынша ең төмен орташа нәтиже {_safe_float(task_stats['mean'].min())}%, "
        f"ал ең жоғарысы {_safe_float(task_stats['mean'].max())}% болды. "
        f"Бұл қай тапсырма түрі күрделі, қайсысы жеңілірек болғанын айқын көрсетеді."
        if not task_stats.empty
        else 'Тапсырмалар бойынша статистикалық дерек жеткіліксіз.'
    )
    stat_cards = [
        {
            'title': 'p-value (p-мәні)',
            'value': comparison.get('p_value_scientific_html') or comparison.get('p_value_scientific') or comparison.get('p_value_display') or '-',
            'summary': comparison.get('p_value_guidance', {}).get('summary', '-'),
            'meaning': comparison.get('p_value_guidance', {}).get('meaning', ''),
            'definition': 'p-value топтар арасындағы байқалған айырмашылықтың кездейсоқ пайда болу ықтималдығын көрсетеді.',
            'thresholds': 'Шектер: p < 0.01 өте күшті дәлел, 0.01 ≤ p < 0.05 статистикалық маңызды, p ≥ 0.05 сенімді айырмашылық дәлелденбеген.',
            'is_html': True,
            'accent': 'navy',
        },
        {
            'title': 't-statistic (t-көрсеткіш)',
            'value': comparison.get('t_statistic_display') or comparison.get('t_statistic') or '-',
            'summary': comparison.get('t_guidance', {}).get('summary', '-'),
            'meaning': comparison.get('t_guidance', {}).get('meaning', ''),
            'definition': 't-statistic екі топтың орташа мәндерінің бір-бірінен қаншалықты алшақ екенін көрсетеді.',
            'thresholds': 'Белгінің бағыты маңызды: теріс мән эксперимент тобы жоғарырақ екенін, оң мән бақылау тобы жоғарырақ екенін білдіреді.',
            'accent': 'teal',
        },
        {
            'title': 'Әсер көлемі',
            'value': comparison.get('effect_size_display') or comparison.get('effect_size') or '-',
            'summary': comparison.get('effect_size_guidance', {}).get('summary', '-'),
            'meaning': comparison.get('effect_size_guidance', {}).get('meaning', ''),
            'definition': 'Effect size айырмашылықтың практикадағы күшін көрсетеді, яғни нәтиженің шынайы педагогикалық маңызын ашады.',
            'thresholds': 'Шектер: |d| < 0.20 елеусіз, 0.20-0.49 шағын, 0.50-0.79 орташа, |d| ≥ 0.80 күшті әсер.',
            'accent': 'amber',
        },
    ]
    commission_notes = [
        {
            'title': 'Зерттеу шешімі',
            'text': decision_text,
        },
        {
            'title': 'Нәтиженің сенімділігі',
            'text': comparison.get('p_value_guidance', {}).get('meaning', ''),
        },
        {
            'title': 'Педагогикалық мағынасы',
            'text': comparison.get('effect_size_guidance', {}).get('meaning', ''),
        },
    ]
    section_explanations = {
        'overall': (
            f"Жалпы сипаттамалық статистика деректердің орталық деңгейін көрсетеді. "
            f"Қазіргі орташа нәтиже {overall_mean}% болып, бұл {overall_level} деңгейге жатады."
        ),
        'comparison': (
            f"{group_summary_text} "
            f"{comparison.get('interpretation', '')}"
        ),
        'groups': (
            "Топтар бойынша сипаттамалық статистика әр топтың ішкі тұрақтылығын, "
            "орташа нәтижесін және таралу ауқымын салыстыруға мүмкіндік береді."
        ),
        'lessons': lesson_summary,
        'tasks': task_summary,
    }
    return {
        'dataset': dataset,
        'statistics': stats,
        'comparison': comparison,
        'overall_rows': overall_rows,
        'stat_cards': stat_cards,
        'commission_notes': commission_notes,
        'section_explanations': section_explanations,
        'teacher_conclusion': _statistics_conclusion(comparison),
        'lesson_stats': [
            {
                'session_label': row['session_label'],
                'mean': _safe_float(row['mean']),
                'median': _safe_float(row['median']),
                'std': _safe_float(row['std']),
                'min': _safe_float(row['min']),
                'max': _safe_float(row['max']),
            }
            for _, row in lesson_stats.iterrows()
        ],
        'task_stats': [
            {
                'task_label': f"Тапсырма {int(row['task_index'])}" if not pd.isna(row['task_index']) else 'Белгісіз',
                'mean': _safe_float(row['mean']),
                'median': _safe_float(row['median']),
                'std': _safe_float(row['std']),
                'min': _safe_float(row['min']),
                'max': _safe_float(row['max']),
            }
            for _, row in task_stats.iterrows()
        ],
    }


def build_ai_context(dataset, filters=None):
    filters = filters or {}
    selected_score_band = str(filters.get('score_band', 'all')).strip().lower() or 'all'
    selected_task_focus = str(filters.get('task_focus', 'all')).strip() or 'all'

    frame = dataset_frame(dataset)
    comparison = compare_groups(frame)
    demo_override = _get_demo_display_override(dataset)
    if demo_override:
        comparison = _apply_comparison_override(comparison, demo_override.get('comparison'))
    comparison['t_guidance'] = _t_statistic_guidance(comparison.get('t_statistic'))
    student_summary = (
        frame.groupby(['student_name', 'group_name'])['percentage']
        .mean()
        .reset_index()
        .rename(columns={'percentage': 'average_score'})
    )
    student_contacts = (
        frame.groupby(['student_name', 'group_name'])['student_email']
        .agg(_first_nonempty)
        .reset_index()
    )
    student_summary = student_summary.merge(student_contacts, on=['student_name', 'group_name'], how='left')
    lesson_scores = (
        frame.groupby(['student_name', 'session_label'])['percentage']
        .mean()
        .reset_index()
        .sort_values(by=['student_name', 'percentage'])
    )
    task_scores = (
        frame.groupby(['student_name', 'lesson_topic'])['percentage']
        .mean()
        .reset_index()
        .sort_values(by=['student_name', 'percentage'])
    )
    student_summary['risk_score'] = (100 - student_summary['average_score']).clip(lower=0)
    student_summary['risk_label'] = student_summary['risk_score'].apply(_risk_label)
    student_summary = student_summary.sort_values(by='average_score')

    hard_lessons = frame.groupby('session_label')['percentage'].mean().sort_values().head(3)
    hard_tasks = frame.groupby('lesson_topic')['percentage'].mean().sort_values().head(3)
    experiment_label = comparison.get('experiment_label', 'Эксперимент')
    control_label = comparison.get('control_label', 'Бақылау')

    student_cards = []
    for _, row in student_summary.iterrows():
        student_name = row['student_name']
        average = _safe_float(row['average_score'])
        weakest_lessons = lesson_scores.loc[lesson_scores['student_name'] == student_name].head(3)
        weakest_tasks = task_scores.loc[task_scores['student_name'] == student_name].head(3)
        weak_lesson_names = weakest_lessons['session_label'].tolist()
        weak_task_names = weakest_tasks['lesson_topic'].tolist()
        weak_lesson_text = ', '.join(
            f"{item['session_label']} ({_safe_float(item['percentage'])}%)"
            for _, item in weakest_lessons.iterrows()
        ) or 'Анықталмады'
        weak_task_text = ', '.join(
            f"{item['lesson_topic']} ({_safe_float(item['percentage'])}%)"
            for _, item in weakest_tasks.iterrows()
        ) or 'Анықталмады'
        focus_lesson = weak_lesson_names[0] if weak_lesson_names else 'Анықталмады'
        focus_task = weak_task_names[0] if weak_task_names else 'Анықталмады'
        focus_task_short = _task_focus_label(focus_task)

        ai_messages = _compose_student_ai_messages(
            student_name,
            row['group_name'],
            average,
            weak_lesson_names,
            weak_task_names,
        )
        student_cards.append(
            {
                'student_name': student_name,
                'student_email': row.get('student_email', ''),
                'group_name': row['group_name'],
                'average_score': average,
                'risk_label': row['risk_label'],
                'result_level': ai_messages['level_label'],
                'level_class': ai_messages['level_class'],
                'card_class': ai_messages['card_class'],
                'compact_note': 'Толық жеке траекторияны көру үшін карточканы ашыңыз.',
                'focus_lesson': focus_lesson,
                'focus_task': focus_task,
                'focus_task_short': focus_task_short,
                'weak_lessons': weak_lesson_text,
                'weak_tasks': weak_task_text,
                'teacher_advice': ai_messages['teacher_advice'],
                'student_advice': ai_messages['student_advice'],
                'prediction': ai_messages['prediction'],
                'trajectory_step': ai_messages['student_advice'],
                'expected_result': ai_messages['prediction'],
            }
        )

    student_cards = _apply_level_override_to_cards(student_cards, demo_override)

    risk_groups = {
        'high': [item for item in student_cards if item['risk_label'] == 'Жоғары тәуекел'],
        'medium': [item for item in student_cards if item['risk_label'] == 'Орташа тәуекел'],
        'low': [item for item in student_cards if item['risk_label'] == 'Төмен тәуекел'],
    }

    filtered_cards = list(student_cards)
    if selected_score_band in {'low', 'medium', 'high'}:
        score_label_map = {'low': 'Төмен', 'medium': 'Орташа', 'high': 'Жоғары'}
        filtered_cards = [item for item in filtered_cards if item['result_level'] == score_label_map[selected_score_band]]
    if selected_task_focus != 'all':
        filtered_cards = [item for item in filtered_cards if item['focus_task_short'] == selected_task_focus]

    grouped_cards = {
        'high': [item for item in filtered_cards if item['result_level'] == 'Жоғары'],
        'medium': [item for item in filtered_cards if item['result_level'] == 'Орташа'],
        'low': [item for item in filtered_cards if item['result_level'] == 'Төмен'],
    }

    hardest_lesson_label = hard_lessons.index.tolist()[0] if not hard_lessons.empty else 'анықталмады'
    hardest_task_label = hard_tasks.index.tolist()[0] if not hard_tasks.empty else 'анықталмады'
    support_names = ', '.join(item['student_name'] for item in risk_groups['high'][:8]) or 'Анықталмады'
    advanced_names = ', '.join(item['student_name'] for item in grouped_cards['high'][:8]) or 'Анықталмады'
    growth_names = ', '.join(item['student_name'] for item in grouped_cards['medium'][:8]) or 'Анықталмады'

    task_health_cards = []
    task_health_frame = (
        frame.groupby('task_index')['percentage']
        .mean()
        .reset_index()
        .dropna(subset=['task_index'])
        .sort_values(by='task_index')
    )
    for _, task_row in task_health_frame.iterrows():
        task_label = f"Тапсырма {int(task_row['task_index'])}"
        score = _safe_float(task_row['percentage'])
        level_meta = _score_level_details(score)
        task_health_cards.append(
            {
                'label': task_label,
                'value': f"{score}%",
                'description': f"{level_meta['label']} деңгей",
                'class_name': {
                    'result-chip-danger': 'ai-level-low',
                    'result-chip-warn': 'ai-level-medium',
                    'result-chip-success': 'ai-level-high',
                }.get(level_meta['class_name'], 'ai-level-medium'),
            }
        )

    if not task_health_cards and (demo_override or {}).get('tasks'):
        fallback_score = _safe_float(frame['percentage'].mean())
        fallback_level = _score_level_details(fallback_score)
        fallback_class = {
            'result-chip-danger': 'ai-level-low',
            'result-chip-warn': 'ai-level-medium',
            'result-chip-success': 'ai-level-high',
        }.get(fallback_level['class_name'], 'ai-level-medium')
        for task_index in range(1, int((demo_override or {}).get('tasks', 0)) + 1):
            task_health_cards.append(
                {
                    'label': f'Тапсырма {task_index}',
                    'value': f'{fallback_score}%',
                    'description': f"{fallback_level['label']} деңгей",
                    'class_name': fallback_class,
                }
            )

    filter_summary = 'Сүзгі қолданылмаған. Барлық студент көрсетіліп тұр.'
    if selected_score_band != 'all' or selected_task_focus != 'all':
        score_titles = {'low': 'төмен баға', 'medium': 'орташа баға', 'high': 'жоғары баға', 'all': 'барлық баға'}
        parts = [f"Баға сүзгісі: {score_titles.get(selected_score_band, 'барлық баға')}"]
        if selected_task_focus != 'all':
            parts.append(f"Тапсырма сүзгісі: {selected_task_focus}")
        parts.append(f"Іріктелген студент саны: {len(filtered_cards)}")
        filter_summary = ' | '.join(parts)

    override_levels = (demo_override or {}).get('levels') or {}
    low_count = int(override_levels.get('low', len([item for item in filtered_cards if item['result_level'] == 'Төмен'])))
    medium_count = int(override_levels.get('medium', len([item for item in filtered_cards if item['result_level'] == 'Орташа'])))
    high_count = int(override_levels.get('high', len([item for item in filtered_cards if item['result_level'] == 'Жоғары'])))

    overall_insights = [
        {
            'title': 'Жалпы қорытынды',
            'text': f"{experiment_label} және {control_label} топтарының нәтижелері салыстырылды. {comparison.get('interpretation', '')}",
        },
        {
            'title': 'Статистикалық негіздеме',
            'text': f"p-мәні бойынша {comparison.get('p_value_guidance', {}).get('meaning', '')} Әсер көлемі бойынша {comparison.get('effect_size_guidance', {}).get('meaning', '')}",
        },
        {
            'title': 'Нәтижелік деңгейлер көрінісі',
            'text': f"Төмен деңгейде {low_count} студент, орташа деңгейде {medium_count} студент, жоғары деңгейде {high_count} студент анықталды.",
        },
        {
            'title': 'Негізгі әлсіз аймақтар',
            'text': f"Ең әлсіз сабақтар: {', '.join(hard_lessons.index.tolist()) if not hard_lessons.empty else 'анықталмады'}. Ең әлсіз тапсырмалар: {', '.join(_task_focus_label(item) for item in hard_tasks.index.tolist()) if not hard_tasks.empty else 'анықталмады'}.",
        },
    ]

    teacher_recommendations = [
        {
            'title': 'Жалпы педагогикалық шешім',
            'text': f"Негізгі назарды {hardest_lesson_label} тақырыбы мен {hardest_task_label} тапсырмасына бағыттау ұсынылады. Бұл аймақтарда түсіндіруді күшейту қажет.",
        },
        {
            'title': 'Қолдауды қажет ететін топ',
            'text': 'Төмен және орташа деңгейдегі студенттермен қысқа диагностикалық жұмыс, үлгімен орындау және кезеңдік кері байланыс ұйымдастырған дұрыс.',
        },
        {
            'title': 'Жоғары нәтижелі студенттермен жұмыс',
            'text': 'Жоғары нәтиже көрсеткен студенттерге күрделендірілген тапсырма мен көшбасшылық сипаттағы жұмыс беру тиімді.',
        },
    ]

    level_tiles = [
        {
            'label': 'Төмен деңгей',
            'count': low_count,
            'description': 'Жедел қолдау мен қысқа түзету жұмысын қажет ететін студенттер.',
            'class_name': 'ai-level-low',
        },
        {
            'label': 'Орташа деңгей',
            'count': medium_count,
            'description': 'Жоғары деңгейге көтерілу әлеуеті бар студенттер.',
            'class_name': 'ai-level-medium',
        },
        {
            'label': 'Жоғары деңгей',
            'count': high_count,
            'description': 'Тұрақты нәтижені сақтап, тереңдетілген тапсырма беруге болатын студенттер.',
            'class_name': 'ai-level-high',
        },
    ]

    teacher_action_plan = [
        {
            'title': 'Осы аптада істеу керек',
            'text': f"{hardest_lesson_label} сабағы бойынша қысқа қайталау, қате талдауы және {hardest_task_label} тапсырмасына арналған бекіту жұмысын енгізу қажет.",
        },
        {
            'title': 'Келесі сабақта істеу керек',
            'text': f"Сабақ басында қысқа диагностикалық сұрақтар алып, {hardest_lesson_label} тақырыбына қайта түсіндіру элементін қосу ұсынылады.",
        },
        {
            'title': 'Қосымша қолдау керек студенттер',
            'text': support_names,
        },
        {
            'title': 'Күрделендірілген тапсырма беру керек студенттер',
            'text': advanced_names,
        },
    ]

    trajectory_groups = [
        {
            'title': 'Қалпына келтіру траекториясы',
            'subtitle': 'Төмен деңгейдегі студенттер',
            'students': support_names,
            'action': f"Негізгі әлсіз бөлімдер бойынша, әсіресе {hardest_lesson_label} тақырыбында қайта түсіндіру мен қысқа жеке қолдау қажет.",
            'expected': 'Қысқа мерзімде нәтижені орташа деңгейге жақындату күтіледі.',
        },
        {
            'title': 'Өсу траекториясы',
            'subtitle': 'Орташа деңгейдегі студенттер',
            'students': growth_names,
            'action': 'Қате талдау, үлгімен жұмыс және сатыланған тапсырмалар арқылы жоғары деңгейге көтерілуге бағыттау қажет.',
            'expected': 'Жүйелі жаттығу сақталса, бұл топтың бір бөлігі жоғары деңгейге өтеді.',
        },
        {
            'title': 'Көшбасшылық траекториясы',
            'subtitle': 'Жоғары деңгейдегі студенттер',
            'students': advanced_names,
            'action': 'Күрделендірілген тапсырма мен зерттеушілік сипаттағы жұмыс ұсыну қажет.',
            'expected': 'Жоғары нәтиже тұрақтанып, сыныпішілік академиялық көшбасшылық қалыптасады.',
        },
    ]

    weak_area_solutions = []
    for lesson_name, lesson_value in hard_lessons.items():
        weak_area_solutions.append(
            {
                'area_type': 'Сабақ',
                'title': lesson_name,
                'metric': f"Орташа нәтиже: {_safe_float(lesson_value)}%",
                'reason': 'Бұл бөлімде базалық түсінуді бекіту жеткіліксіз немесе қадамдық түсіндіру қажет.',
                'action': 'Қайта түсіндіру, қысқа диагностика және шағын топпен жұмыс ұйымдастыру ұсынылады.',
                'method': 'Қадамдық қолдау, үлгі көрсету, сұрақ-жауап және қалыптастырушы бағалау тәсілдері тиімді.',
            }
        )
    for task_name, task_value in hard_tasks.items():
        weak_area_solutions.append(
            {
                'area_type': 'Тапсырма',
                'title': _task_focus_label(task_name),
                'metric': f"Орташа нәтиже: {_safe_float(task_value)}%",
                'reason': 'Бұл тапсырмада қолдану және талдау кезінде қателік жиі кездеседі.',
                'action': 'Ұқсас тапсырмалардың жеңілден күрделіге өтетін тізбегін беріп, қате талдау жүргізу қажет.',
                'method': 'Үлгімен орындау, жұптық талқылау және кезең-кезеңмен кері байланыс тиімді.',
            }
        )

    auto_pedagogical_summary = [
        {
            'title': 'Зерттеу қорытындысы',
            'text': f"{experiment_label} және {control_label} топтарының салыстырмалы талдауы бойынша {comparison.get('interpretation', '').lower()}",
        },
        {
            'title': 'Әдістемелік қорытынды',
            'text': f"Ең әлсіз бөлімдер ретінде {hardest_lesson_label} және {hardest_task_label} айқындалды. Келесі циклде әдістемелік түзету дәл осы аймақтарға бағытталуы керек.",
        },
        {
            'title': 'Мұғалімге ұсыныс',
            'text': f"Алдымен тәуекелі жоғары студенттерге назар аударып, {hardest_lesson_label} тақырыбы бойынша қысқа қолдау блогын енгізу орынды.",
        },
        {
            'title': 'Студентке ұсыныс',
            'text': 'Әр студент өз деңгейіне сәйкес жеке траекториямен жұмыс істеуі керек: төмен деңгейде бекіту, орташа деңгейде өсу, жоғары деңгейде тереңдету.',
        },
    ]

    risk_map = [
        {
            'title': 'Жоғары тәуекел',
            'count': len(risk_groups['high']),
            'description': 'Жедел педагогикалық қолдау мен тұрақты бақылауды қажет ететін студенттер.',
            'class_name': 'ai-risk-high',
            'students': [item['student_name'] for item in risk_groups['high']],
        },
        {
            'title': 'Орташа тәуекел',
            'count': len(risk_groups['medium']),
            'description': 'Нәтижесі тұрақсыз немесе жүйелі бекіту қажет студенттер.',
            'class_name': 'ai-risk-medium',
            'students': [item['student_name'] for item in risk_groups['medium']],
        },
        {
            'title': 'Төмен тәуекел',
            'count': len(risk_groups['low']),
            'description': 'Нәтижесі тұрақты және өздігінен ілгерілеуге бейім студенттер.',
            'class_name': 'ai-risk-low',
            'students': [item['student_name'] for item in risk_groups['low']],
        },
    ]

    task_filter_options = [{'value': 'all', 'label': 'Барлық тапсырма'}] + [
        {'value': f"Тапсырма {int(item)}", 'label': f"Тапсырма {int(item)}"}
        for item in sorted(frame['task_index'].dropna().unique().tolist())
    ]
    if len(task_filter_options) == 1 and (demo_override or {}).get('tasks'):
        task_filter_options += [
            {'value': f'Тапсырма {index}', 'label': f'Тапсырма {index}'}
            for index in range(1, int((demo_override or {}).get('tasks', 0)) + 1)
        ]

    return {
        'dataset': dataset,
        'comparison': comparison,
        'overall_insights': overall_insights,
        'teacher_recommendations': teacher_recommendations,
        'student_cards': filtered_cards,
        'student_groups': grouped_cards,
        'student_group_counts': {
            'low': low_count,
            'medium': medium_count,
            'high': high_count,
        },
        'level_tiles': level_tiles,
        'teacher_action_plan': teacher_action_plan,
        'trajectory_groups': trajectory_groups,
        'weak_area_solutions': weak_area_solutions,
        'auto_pedagogical_summary': auto_pedagogical_summary,
        'risk_map': risk_map,
        'task_health_cards': task_health_cards,
        'selected_filters': {
            'score_band': selected_score_band,
            'task_focus': selected_task_focus,
        },
        'score_filter_options': [
            {'value': 'all', 'label': 'Барлық баға'},
            {'value': 'low', 'label': 'Төмен баға'},
            {'value': 'medium', 'label': 'Орташа баға'},
            {'value': 'high', 'label': 'Жоғары баға'},
        ],
        'task_filter_options': task_filter_options,
        'filter_summary': filter_summary,
    }


def build_dashboard_page_context(dataset, selected_chart_ids=None):
    frame = dataset_frame(dataset)
    overview = build_dataset_overview(dataset)
    score_details = _dashboard_score_details(overview['overview_cards']['average_score'])
    comparison = overview['comparison']
    charts = build_plotly_charts(frame)
    all_charts = list(charts)

    selected_chart_ids = [str(item) for item in (selected_chart_ids or []) if str(item).strip()]
    if selected_chart_ids:
        selected_set = set(selected_chart_ids)
        charts = [chart for chart in charts if str(chart.get('id')) in selected_set]

    for index, chart in enumerate(charts, start=1):
        chart['dom_id'] = f"chart-{index}"

    student_average = (
        frame.groupby(['student_name', 'group_name'])['percentage']
        .mean()
        .reset_index()
    )
    level_counts = student_average['percentage'].apply(_level_label).value_counts()
    demo_override = _get_demo_display_override(dataset)
    override_levels = (demo_override or {}).get('levels') or {}
    low_count = int(override_levels.get('low', level_counts.get('Төмен', 0)))
    medium_count = int(override_levels.get('medium', level_counts.get('Орташа', 0)))
    high_count = int(override_levels.get('high', level_counts.get('Жоғары', 0)))
    group_mean_map = (
        student_average.groupby('group_name')['percentage']
        .mean()
        .to_dict()
    )

    if demo_override and demo_override.get('comparison'):
        comparison = _apply_comparison_override(comparison, demo_override.get('comparison'))
        for chart in charts:
            if chart.get('id') == 'effect-size':
                chart['figure']['data'][0]['value'] = abs(float(comparison.get('effect_size') or 0))
                chart['interpretation'] = f"Cohen’s d = {_safe_float(comparison.get('effect_size'))}. {comparison.get('effect_size_guidance', {}).get('meaning', '')}"
            if chart.get('id') == 'p-value':
                p_value = float(comparison.get('p_value') or 0)
                p_display = comparison.get('p_value_display') or str(p_value)
                chart['figure']['data'][0]['x'] = [min(max(p_value, 0), 0.10)]
                chart['figure']['layout']['annotations'][0]['text'] = f"p = {p_display}"
                chart['interpretation'] = f"p-value = {p_display}. {comparison.get('p_value_guidance', {}).get('meaning', '')}"

    metric_cards = [
        {
            'slug': 'students',
            'label': 'Студент саны',
            'value': overview['overview_cards']['students'],
            'subtitle': 'Талдауға енген бірегей оқушылар саны',
            'accent': 'blue',
            'details': 'Бұл көрсеткіш талдауға қанша оқушы қатысқанын көрсетеді. Оқушы саны жеткілікті болған сайын қорытындыны сенімдірек түсіндіруге болады.',
        },
        {
            'slug': 'mean',
            'label': 'Орташа балл',
            'value': f"{overview['overview_cards']['average_score']}%",
            'subtitle': f"{score_details['label']} деңгей · {score_details['description']}",
            'accent': 'teal',
            'details': (
                f"Орташа балл барлық оқушылар нәтижесінің арифметикалық ортасы. "
                f"Деңгей шектері: Жоғары 85-100%, Орташа 70-84.99%, Төмен 0-69.99%. "
                f"Қазіргі үлестірім: Жоғары {high_count}, Орташа {medium_count}, Төмен {low_count}."
            ),
        },
        {
            'slug': 'median',
            'label': 'Медиана',
            'value': f"{overview['overview_cards']['median_score']}%",
            'subtitle': 'Орталық типтік нәтиже',
            'accent': 'amber',
            'details': 'Медиана нәтижелерді өсу ретімен орналастырғанда дәл ортасында тұратын мән. Ол шектен тыс жоғары не төмен баллдардың әсерін азайтып, типтік деңгейді көрсетеді.',
        },
        {
            'slug': 'levels',
            'label': 'Нәтижелік деңгейлер',
            'value': f"{high_count} / {medium_count} / {low_count}",
            'subtitle': 'Жоғары / Орта / Төмен',
            'accent': 'purple',
            'details': (
                f"Жоғары деңгей: 85-100% ({high_count} оқушы). "
                f"Орта деңгей: 70-84.99% ({medium_count} оқушы). "
                f"Төмен деңгей: 0-69.99% ({low_count} оқушы)."
            ),
        },
    ]

    section_meta = [
        ('core', 'I. Негізгі', 'Негізгі салыстырулар', 'Бұл бөлімде топтар арасындағы негізгі айырмашылықтар, динамика және сапалық деңгейлер көрсетіледі.'),
        ('growth', 'II. Өсім және тиімділік', 'Өсім, қарқын және жинақталған прогресс', 'Оқу басы мен соңы, өсім пайызы және уақыт бойынша тұрақты даму осы бөлімде жинақталған.'),
        ('tasks', 'III. Тапсырма анализі', 'Тапсырмалар бойынша сапалы талдау', 'Қай тапсырмалар оңай, қайсысы күрделі екенін және сабақ × тапсырма аймақтарын осы жерден көруге болады.'),
        ('students', 'IV. Студент деңгейі', 'Жеке оқушы және рейтингтер', 'Мұғалім кімге қолдау, кімге күрделі тапсырма беру керегін осы блок арқылы жылдам анықтай алады.'),
        ('statistics', 'V. Статистика', 'Маңызды статистикалық интерпретация', 'Орташа, медиана, әсер көлемі және p-мәні айырмашылықтың мәнін дәлелдеуге көмектеседі.'),
    ]
    sections = []
    for key, tag, title, intro in section_meta:
        section_charts = [chart for chart in charts if chart.get('section_key') == key]
        sections.append(
            {
                'key': key,
                'tag': tag,
                'title': title,
                'intro': intro,
                'charts': section_charts,
            }
        )

    chart_download_sections = []
    for key, tag, title, _intro in section_meta:
        section_options = [
            {
                'id': chart.get('id'),
                'title': chart.get('title'),
                'checked': not selected_chart_ids or str(chart.get('id')) in selected_chart_ids,
            }
            for chart in all_charts
            if chart.get('section_key') == key
        ]
        chart_download_sections.append(
            {
                'key': key,
                'tag': tag,
                'title': title,
                'charts': section_options,
            }
        )

    group_gap = _safe_float((comparison.get('effect_size') or 0))
    experiment_label = comparison.get('experiment_label') or 'Эксперимент'
    control_label = comparison.get('control_label') or 'бақылау'
    group_summary_cards = [
        {
            'title': 'Статистикалық маңыздылық',
            'text': (
                f"p-мәні {comparison.get('p_value_scientific_html') or comparison.get('p_value_scientific') or comparison.get('p_value_display') or '-'} болды. "
                f"Бұл {comparison.get('p_value_guidance', {}).get('meaning', '').lower()}"
            ),
            'is_html': True,
        },
        {
            'title': 'Практикалық әсер',
            'text': (
                f"Әсер көлемі {comparison.get('effect_size_display') or comparison.get('effect_size') or '-'} болды. "
                f"{comparison.get('effect_size_guidance', {}).get('meaning', '')}"
            ),
        },
        {
            'title': 'Педагогикалық қорытынды',
            'text': (
                f"{experiment_label} тобының орташа нәтижесі {_safe_float(group_mean_map.get(experiment_label, 0))}%, "
                f"ал {control_label} тобының орташа нәтижесі {_safe_float(group_mean_map.get(control_label, 0))}%. "
                f"Сондықтан интервенция қолданылған топта нәтиже жоғарырақ байқалды."
            ),
        },
    ]
    return {
        'dataset': dataset,
        'frame': frame,
        'overview_cards': overview['overview_cards'],
        'comparison': comparison,
        'score_details': score_details,
        'charts': charts,
        'chart_sections': sections,
        'metric_cards': metric_cards,
        'group_summary_title': 'Топаралық статистикалық қорытынды',
        'group_summary_text': (
            f"{experiment_label} және {control_label} топтарының нәтижелері салыстырылды. "
            f"Талдау бойынша айырмашылық сенімді байқалды: әсер көлемі {group_gap}, "
            f"ал p-мәні {comparison.get('p_value_scientific_html') or comparison.get('p_value_scientific') or comparison.get('p_value_display') or '-'}."
        ),
        'group_summary_cards': group_summary_cards,
        'chart_download_sections': chart_download_sections,
        'selected_chart_ids': selected_chart_ids,
        'selected_chart_count': len(charts),
    }


def build_excel_export(dataset):
    overview = build_dataset_overview(dataset)
    stats = build_statistics_context(dataset)
    ai_context = build_ai_context(dataset)
    frame = dataset_frame(dataset)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        frame.to_excel(writer, index=False, sheet_name='Raw Data')
        pd.DataFrame(stats['statistics']['by_group']).to_excel(writer, index=False, sheet_name='By Group Stats')
        pd.DataFrame(stats['lesson_stats']).to_excel(writer, index=False, sheet_name='Lesson Stats')
        pd.DataFrame(stats['task_stats']).to_excel(writer, index=False, sheet_name='Task Stats')
        pd.DataFrame(ai_context['student_cards']).to_excel(writer, index=False, sheet_name='AI Insights')
        pd.DataFrame([overview['comparison']]).to_excel(writer, index=False, sheet_name='Comparison')
    output.seek(0)
    return output


def _register_pdf_fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = [
        (
            'ArialCustom',
            [r'C:\Windows\Fonts\arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'],
            [r'C:\Windows\Fonts\arialbd.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'],
        ),
        (
            'SegoeUICustom',
            [r'C:\Windows\Fonts\segoeui.ttf'],
            [r'C:\Windows\Fonts\segoeuib.ttf'],
        ),
    ]

    for font_name, regular_paths, bold_paths in candidates:
        regular_path = next((path for path in regular_paths if os.path.exists(path)), None)
        bold_path = next((path for path in bold_paths if os.path.exists(path)), None)
        if not regular_path:
            continue
        try:
            if font_name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(font_name, regular_path))
            bold_name = f'{font_name}-Bold'
            if bold_path and bold_name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(bold_name, bold_path))
            return font_name, bold_name if bold_path else font_name
        except Exception:
            continue
    return 'Helvetica', 'Helvetica-Bold'


def _data_url_to_image_stream(data_url):
    if not data_url:
        return None
    try:
        encoded = data_url.split(',', 1)[1] if ',' in data_url else data_url
        return BytesIO(base64.b64decode(encoded))
    except Exception:
        return None


def _chart_to_pdf_image(chart, chart_image_map=None):
    chart_id = str(chart.get('id', ''))
    if chart_image_map and chart_id in chart_image_map:
        provided_stream = _data_url_to_image_stream(chart_image_map.get(chart_id))
        if provided_stream is not None:
            return provided_stream
    try:
        import plotly.graph_objects as go
        import plotly.io as pio

        figure_payload = chart.get('figure') or {}
        figure = go.Figure(data=figure_payload.get('data', []), layout=figure_payload.get('layout', {}))
        image_bytes = pio.to_image(figure, format='png', width=1280, height=760, scale=2)
        return BytesIO(image_bytes)
    except Exception:
        try:
            import plotly.graph_objects as go

            figure_payload = chart.get('figure') or {}
            figure = go.Figure(data=figure_payload.get('data', []), layout=figure_payload.get('layout', {}))
            return BytesIO(figure.to_image(format='png', width=1280, height=760, scale=2))
        except Exception:
            return None


def build_pdf_export(dataset, selected_chart_ids=None, chart_image_map=None):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    overview = build_dataset_overview(dataset)
    stats = build_statistics_context(dataset)
    dashboard = build_dashboard_page_context(dataset, selected_chart_ids=selected_chart_ids)
    ai_context = build_ai_context(dataset)

    regular_font, bold_font = _register_pdf_fonts()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'PdfTitle',
        parent=styles['Title'],
        fontName=bold_font,
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#182338'),
        alignment=TA_LEFT,
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        'PdfHeading',
        parent=styles['Heading2'],
        fontName=bold_font,
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1f355a'),
        spaceBefore=8,
        spaceAfter=8,
    )
    subheading_style = ParagraphStyle(
        'PdfSubheading',
        parent=styles['Heading3'],
        fontName=bold_font,
        fontSize=11.5,
        leading=14,
        textColor=colors.HexColor('#2448a7'),
        spaceBefore=8,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        'PdfBody',
        parent=styles['BodyText'],
        fontName=regular_font,
        fontSize=10.4,
        leading=14.5,
        textColor=colors.HexColor('#334155'),
        spaceAfter=6,
    )
    note_style = ParagraphStyle(
        'PdfNote',
        parent=body_style,
        fontName=bold_font,
        fontSize=10,
        textColor=colors.HexColor('#0f766e'),
    )

    story = [
        Paragraph(
            'Оқу нәтижелері бойынша толық аналитикалық есеп'
            if not selected_chart_ids else
            'Оқу нәтижелері бойынша таңдалған графиктердің аналитикалық есебі',
            title_style
        ),
        Paragraph(f'Талдау атауы: {dataset.title}', body_style),
        Paragraph(f'Пән атауы: {dataset.subject_title or dataset.title}', body_style),
        Paragraph(f'Пән мұғалімі: {dataset.teacher_name or "Көрсетілмеген"}', body_style),
        Paragraph(f'Оқу контексті: {dataset.cohort_label or "Көрсетілмеген"}', body_style),
        Paragraph(f'Дереккөз файлы: {dataset.original_filename}', body_style),
        Paragraph(
            f"Есепке енгізілген график саны: {dashboard.get('selected_chart_count', len(dashboard.get('charts', [])))}",
            body_style,
        ),
        Spacer(1, 8),
    ]

    overview_table = Table(
        [
            ['Көрсеткіш', 'Мәні', 'Түсіндірме'],
            ['Студент саны', str(overview['overview_cards']['students']), 'Талдауға енген бірегей оқушылар саны'],
            ['Топ саны', str(overview['overview_cards']['groups']), 'Салыстырылған зерттеу топтарының саны'],
            ['Сабақ саны', str(overview['overview_cards']['lessons']), 'Талдауға кірген сабақтар саны'],
            ['Тапсырма саны', str(overview['overview_cards']['tasks']), 'Бағаланған тапсырма түрлері'],
            ['Орташа балл', f"{overview['overview_cards']['average_score']}%", 'Жалпы оқу жетістігінің орташа деңгейі'],
            ['Медиана', f"{overview['overview_cards']['median_score']}%", 'Типтік орталық нәтиже'],
        ],
        colWidths=[4.1 * cm, 3.1 * cm, 9.2 * cm],
    )
    overview_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), bold_font),
        ('FONTNAME', (0, 1), (-1, -1), regular_font),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2448a7')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor('#f8fbff')]),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#d6deeb')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.extend([
        Paragraph('Негізгі көрсеткіштер', heading_style),
        overview_table,
        Spacer(1, 10),
        Paragraph('Топаралық қорытынды', heading_style),
        Paragraph(dashboard['group_summary_text'].replace('<sup>', '<super>').replace('</sup>', '</super>'), body_style),
    ])

    for item in dashboard.get('group_summary_cards', []):
        text = item['text'].replace('<sup>', '<super>').replace('</sup>', '</super>') if item.get('is_html') else item['text']
        story.extend([
            Paragraph(item['title'], subheading_style),
            Paragraph(text, body_style),
        ])

    story.extend([
        Paragraph('Статистикалық талдаудың қысқа түсіндірмесі', heading_style),
    ])
    for card in stats.get('stat_cards', []):
        value_text = card['value'].replace('<sup>', '<super>').replace('</sup>', '</super>') if card.get('is_html') else str(card['value'])
        story.extend([
            Paragraph(f"{card['title']}: {value_text}", subheading_style),
            Paragraph(card['meaning'], body_style),
            Paragraph(card['thresholds'], body_style),
        ])

    story.extend([
        Paragraph('ЖИ-негізделген педагогикалық қорытынды', heading_style),
    ])
    for item in ai_context.get('auto_pedagogical_summary', []):
        story.extend([
            Paragraph(item['title'], subheading_style),
            Paragraph(item['text'], body_style),
        ])
    story.extend([
        Paragraph('Мұғалімге арналған жедел әрекет жоспары', heading_style),
    ])
    for item in ai_context.get('teacher_action_plan', []):
        story.extend([
            Paragraph(item['title'], subheading_style),
            Paragraph(item['text'], body_style),
        ])
    story.extend([
        Paragraph('Тәуекел картасының қысқаша көрінісі', heading_style),
    ])
    for item in ai_context.get('risk_map', []):
        student_names = ', '.join(item.get('students', [])[:12]) or 'Студент анықталмады'
        story.extend([
            Paragraph(f"{item['title']} ({item['count']})", subheading_style),
            Paragraph(item['description'], body_style),
            Paragraph(f"Студенттер: {student_names}", body_style),
        ])

    story.append(PageBreak())

    for section in dashboard.get('chart_sections', []):
        story.extend([
            Paragraph(section['title'], heading_style),
            Paragraph(section['intro'], body_style),
        ])
        for chart in section.get('charts', []):
            story.append(Paragraph(chart['title'], subheading_style))
            story.append(Paragraph(chart.get('description', ''), body_style))
            image_stream = _chart_to_pdf_image(chart, chart_image_map=chart_image_map)
            if image_stream is not None:
                try:
                    chart_image = Image(image_stream, width=17.2 * cm, height=9.8 * cm)
                    story.append(chart_image)
                    story.append(Spacer(1, 6))
                except Exception:
                    pass
            else:
                story.append(Paragraph('Ескерту: бұл графиктің суреті қалыптаспады. Беттен PDF жүктеген кезде график тікелей экраннан алынып, көрінуі тиіс.', body_style))
            story.append(Paragraph(f"График нені көрсетеді: {chart.get('teacher_note', '')}", note_style))
            story.append(Paragraph(chart.get('interpretation', ''), body_style))
            story.append(Spacer(1, 8))
        story.append(PageBreak())

    story.extend([
        Paragraph('Қосымша статистикалық түсіндірмелер', heading_style),
        Paragraph(stats['section_explanations']['overall'], body_style),
        Paragraph(stats['section_explanations']['comparison'], body_style),
        Paragraph(stats['section_explanations']['groups'], body_style),
        Paragraph(stats['section_explanations']['lessons'], body_style),
        Paragraph(stats['section_explanations']['tasks'], body_style),
    ])

    if story and isinstance(story[-1], PageBreak):
        story = story[:-1]

    document.build(story)
    buffer.seek(0)
    return buffer


def active_dataset_from_session(request):
    ensure_demo_ready_datasets()
    teacher_priority = [
        ('Алсу Жалгасова', 'Информатика'),
        ('Аширбекова Жанат', 'Автоматизированные информационные системы'),
        ('Бекен Оралбай', 'Инструментальные средства визуальной коммуникации и прикладной дизайн'),
        ('Илесбекова Жанар', 'Дискреттік және жоғарғы математика'),
    ]
    allowed_pairs = set(teacher_priority)

    dataset_id = request.session.get('active_analysis_dataset_id')
    if dataset_id:
        dataset = AnalysisDataset.objects.filter(pk=dataset_id, status='ready').first()
        if dataset and (dataset.teacher_name, dataset.subject_title) in allowed_pairs:
            return dataset

    preferred_dataset = None
    for teacher_name, subject_title in teacher_priority:
        preferred_dataset = AnalysisDataset.objects.filter(
            teacher_name=teacher_name,
            subject_title=subject_title,
            status='ready',
        ).order_by('-created_at').first()
        if preferred_dataset:
            break
    if preferred_dataset:
        request.session['active_analysis_dataset_id'] = preferred_dataset.id
        return preferred_dataset

    latest_ready_dataset = AnalysisDataset.objects.filter(
        status='ready',
        teacher_name__in=[teacher_name for teacher_name, _ in teacher_priority],
    ).order_by('-created_at').first()
    if latest_ready_dataset:
        request.session['active_analysis_dataset_id'] = latest_ready_dataset.id
        return latest_ready_dataset

    return None



