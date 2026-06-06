from statistics import mean

from django.db.models import Avg, Count

from analytics_core.models import (
    AssessmentResult,
    AttendanceRecord,
    Course,
    EngagementSnapshot,
    Enrollment,
    PedagogicalIntervention,
    Student,
)


def _clamp(value, lower=0, upper=100):
    return max(lower, min(upper, round(value, 1)))


def _risk_label(score):
    if score >= 70:
        return '������� ����'
    if score >= 40:
        return '������� ����'
    return '������ ����'


def _risk_tone(score):
    if score >= 70:
        return 'high'
    if score >= 40:
        return 'medium'
    return 'low'


def _attendance_ratio(student):
    records = AttendanceRecord.objects.filter(student=student)
    total = records.count()
    if not total:
        return 0
    attended = records.filter(status__in=['present', 'late']).count()
    return round(attended / total * 100, 1)


def _engagement_index(student):
    snapshots = EngagementSnapshot.objects.filter(student=student)
    if not snapshots.exists():
        return 0
    values = []
    for snapshot in snapshots:
        values.append(
            (
                min(snapshot.platform_logins, 10) * 3
                + min(snapshot.minutes_online / 3, 50)
                + min(snapshot.forum_posts * 5, 20)
                + float(snapshot.assignment_timeliness) * 20
                + snapshot.self_regulation_score * 0.7
            )
            / 1.9
        )
    return _clamp(mean(values))


def _achievement_average(student):
    results = AssessmentResult.objects.filter(student=student).select_related('assessment')
    if not results:
        return 0
    weighted_scores = []
    total_weight = 0
    for result in results:
        percent = float(result.score) / result.assessment.max_score * 100
        weight = float(result.assessment.weight)
        weighted_scores.append(percent * weight)
        total_weight += weight
    if not total_weight:
        return 0
    return _clamp(sum(weighted_scores) / total_weight)


def calculate_risk_score(student):
    attendance = _attendance_ratio(student)
    engagement = _engagement_index(student)
    achievement = _achievement_average(student)

    score = (
        (100 - attendance) * 0.35
        + (100 - engagement) * 0.25
        + (100 - achievement) * 0.40
    )
    return _clamp(score)


def build_student_profile(student):
    attendance = _attendance_ratio(student)
    engagement = _engagement_index(student)
    achievement = _achievement_average(student)
    risk_score = calculate_risk_score(student)
    enrollments = Enrollment.objects.filter(student=student).select_related('course', 'course__teacher')
    interventions = list(
        PedagogicalIntervention.objects.filter(student=student).select_related('course')
    )

    recommendations = []
    if attendance < 75:
        recommendations.append('������������ �������� ����������� ������� ��� ���������� ������ ���������.')
    if achievement < 80:
        recommendations.append('������ ���������� ����� ������� � ��������� ��������� � ��������� �������.')
    if engagement < 65:
        recommendations.append('���������� �������� � ����� ������ ��������� �������� � ���������� � LMS.')
    if not recommendations:
        recommendations.append('��������� ������� ���������� � ������� ����������������� ������ ���������� ���������.')

    course_cards = []
    for enrollment in enrollments:
        course_cards.append(
            {
                'course': enrollment.course,
                'teacher': enrollment.course.teacher,
                'current_grade': enrollment.current_grade,
                'progress_pct': enrollment.progress_pct,
                'status': enrollment.get_status_display(),
            }
        )

    return {
        'student': student,
        'attendance': attendance,
        'engagement': engagement,
        'achievement': achievement,
        'risk_score': risk_score,
        'risk_label': _risk_label(risk_score),
        'risk_tone': _risk_tone(risk_score),
        'course_cards': course_cards,
        'interventions': interventions,
        'recommendations': recommendations,
    }


def build_dashboard_context():
    students = list(Student.objects.all())
    courses = list(Course.objects.select_related('teacher').annotate(student_count=Count('enrollments')))
    profiles = [build_student_profile(student) for student in students]
    profiles_sorted = sorted(profiles, key=lambda profile: profile['risk_score'], reverse=True)

    at_risk_students = profiles_sorted[:5]
    high_risk_count = sum(1 for profile in profiles if profile['risk_tone'] == 'high')
    medium_risk_count = sum(1 for profile in profiles if profile['risk_tone'] == 'medium')
    low_risk_count = sum(1 for profile in profiles if profile['risk_tone'] == 'low')

    avg_attendance = round(mean([profile['attendance'] for profile in profiles]), 1) if profiles else 0
    avg_engagement = round(mean([profile['engagement'] for profile in profiles]), 1) if profiles else 0
    avg_achievement = round(mean([profile['achievement'] for profile in profiles]), 1) if profiles else 0

    course_snapshots = []
    for course in courses:
        enrollments = Enrollment.objects.filter(course=course)
        course_snapshots.append(
            {
                'course': course,
                'student_count': course.student_count,
                'avg_grade': enrollments.aggregate(value=Avg('current_grade'))['value'] or 0,
                'avg_progress': enrollments.aggregate(value=Avg('progress_pct'))['value'] or 0,
            }
        )

    methodology = [
        '���� ��������� �����: ������, ������������, ���������� � LMS � ��������������� ����� �����.',
        '������� � ������������ ������ ��� ������������� ����������� �������������� �����������.',
        '������ ������� ����� � ������� ������������� ��� ������� ��������� ��������������� �����������.',
        '������ �������������� �����������: ��������������, ���������� �������, �������� ����� � peer-learning.',
        '������ ������� ������������ �� �������� ������������, ������� � ������������� ������������.',
    ]

    return {
        'totals': {
            'students': len(students),
            'courses': len(courses),
            'interventions': PedagogicalIntervention.objects.count(),
            'avg_risk': round(mean([profile['risk_score'] for profile in profiles]), 1) if profiles else 0,
        },
        'quality_metrics': {
            'attendance': avg_attendance,
            'engagement': avg_engagement,
            'achievement': avg_achievement,
        },
        'risk_distribution': {
            'high': high_risk_count,
            'medium': medium_risk_count,
            'low': low_risk_count,
        },
        'at_risk_students': at_risk_students,
        'course_snapshots': course_snapshots,
        'recent_interventions': PedagogicalIntervention.objects.select_related('student', 'course')[:6],
        'methodology': methodology,
        'top_students': sorted(profiles, key=lambda profile: profile['achievement'], reverse=True)[:3],
    }
