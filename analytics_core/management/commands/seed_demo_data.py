import random
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from analytics_core.models import (
    Assessment,
    AssessmentResult,
    AttendanceRecord,
    Course,
    EngagementSnapshot,
    Enrollment,
    PedagogicalIntervention,
    Student,
    Teacher,
)


class Command(BaseCommand):
    help = '��������� ������ ����������������� ������� ��� ������ ��� ������ ���������.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='�������� ������� ������ �������������� ������ ����� �����������.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['reset']:
            AssessmentResult.objects.all().delete()
            AttendanceRecord.objects.all().delete()
            EngagementSnapshot.objects.all().delete()
            Enrollment.objects.all().delete()
            Assessment.objects.all().delete()
            PedagogicalIntervention.objects.all().delete()
            Course.objects.all().delete()
            Student.objects.all().delete()
            Teacher.objects.all().delete()

        user_model = get_user_model()
        demo_user, created = user_model.objects.get_or_create(username='researcher')
        if created or not demo_user.check_password('Research2026!'):
            demo_user.set_password('Research2026!')
            demo_user.is_staff = True
            demo_user.save()

        random.seed(42)

        teachers = [
            Teacher.objects.create(
                full_name='����� ���������� ������',
                department='���������� � �������� ���������',
                position='���������',
                research_focus='Learning analytics, ����������� ����������',
            ),
            Teacher.objects.create(
                full_name='������ ��������� �������',
                department='�������������� ���������� � �����������',
                position='������',
                research_focus='��������������� �������������� �����',
            ),
        ]

        courses = [
            Course.objects.create(
                title='������ ������� ��������������� ������',
                code='EDA-601',
                description='������ ������������, ��������������� ������ � �������������� ������������� ��������� �����.',
                semester='spring',
                teacher=teachers[0],
                ects_credits=6,
                delivery_format='blended',
            ),
            Course.objects.create(
                title='�������������� ������ �������� �����',
                code='PDD-302',
                description='�������������� ������� � ��������� ��������� �� ������ ���������.',
                semester='spring',
                teacher=teachers[1],
                ects_credits=5,
                delivery_format='online',
            ),
            Course.objects.create(
                title='����������� ���������� � �������� �����',
                code='FOR-210',
                description='�������� ������, ��������������� �� ���� � ���������.',
                semester='spring',
                teacher=teachers[0],
                ects_credits=4,
                delivery_format='offline',
            ),
        ]

        student_specs = [
            ('���� ��������', 'PI-21', Decimal('4.80')),
            ('���� �������', 'PI-21', Decimal('4.10')),
            ('����� ��������', 'PI-22', Decimal('4.65')),
            ('������ �������', 'PI-22', Decimal('3.90')),
            ('����� ������', 'PI-23', Decimal('4.95')),
            ('������ �������', 'PI-23', Decimal('3.70')),
        ]

        students = []
        for index, (full_name, group_name, gpa) in enumerate(student_specs, start=1):
            students.append(
                Student.objects.create(
                    full_name=full_name,
                    email=f'student{index}@demo.edu',
                    cohort='2024',
                    study_group=group_name,
                    enrollment_year=2024,
                    prior_gpa=gpa,
                    learning_preferences='��������� ������, ������������, ������ � �������',
                    support_notes='������� � ���������� �������������� �������������',
                )
            )

        assessments = []
        base_due_date = date(2026, 3, 10)
        for course_index, course in enumerate(courses):
            assessments.extend(
                [
                    Assessment.objects.create(
                        course=course,
                        title='��������������� ����',
                        assessment_type='quiz',
                        max_score=100,
                        weight=Decimal('0.20'),
                        due_date=base_due_date + timedelta(days=course_index * 5),
                    ),
                    Assessment.objects.create(
                        course=course,
                        title='������������� �����',
                        assessment_type='project',
                        max_score=100,
                        weight=Decimal('0.45'),
                        due_date=base_due_date + timedelta(days=14 + course_index * 5),
                    ),
                    Assessment.objects.create(
                        course=course,
                        title='�������� �����������',
                        assessment_type='exam',
                        max_score=100,
                        weight=Decimal('0.35'),
                        due_date=base_due_date + timedelta(days=28 + course_index * 5),
                    ),
                ]
            )

        priority_templates = [
            ('������������ ������������ �� ���������� ��������', 'feedback', 'medium'),
            ('����� ������ ��������� ��������', 'peer', 'low'),
            ('���������� ����� �������', 'adaptive', 'high'),
            ('�������������� ������� �� ������������� ���������', 'mentoring', 'high'),
        ]

        for student_index, student in enumerate(students):
            for course in courses:
                current_grade = Decimal(str(68 + random.randint(0, 28) - (student_index % 3) * 4))
                progress = Decimal(str(58 + random.randint(0, 35)))
                status = 'support' if current_grade < 75 else 'active'
                Enrollment.objects.create(
                    student=student,
                    course=course,
                    target_grade=85,
                    current_grade=current_grade,
                    progress_pct=progress,
                    status=status,
                )

                course_assessments = [assessment for assessment in assessments if assessment.course_id == course.id]
                for assessment in course_assessments:
                    base_score = float(current_grade) + random.randint(-10, 8)
                    score = max(45, min(98, base_score))
                    aware_dt = timezone.make_aware(
                        datetime.combine(assessment.due_date, datetime.min.time()) + timedelta(hours=10 + random.randint(0, 6))
                    )
                    AssessmentResult.objects.create(
                        student=student,
                        assessment=assessment,
                        score=Decimal(str(round(score, 2))),
                        submitted_at=aware_dt,
                        attempt_number=1,
                        feedback='������������� ��������������� ���������������� �������� ����� �� �������� ������.',
                    )

                for week_offset in range(4):
                    EngagementSnapshot.objects.create(
                        student=student,
                        course=course,
                        week_start=date(2026, 3, 3) + timedelta(days=week_offset * 7),
                        platform_logins=max(2, 10 - student_index + random.randint(-1, 2)),
                        minutes_online=max(45, 220 - student_index * 18 + random.randint(-15, 20)),
                        forum_posts=max(0, 5 - student_index // 2 + random.randint(-1, 2)),
                        assignment_timeliness=Decimal(str(round(max(0.45, min(1.0, 0.92 - student_index * 0.06 + random.uniform(-0.04, 0.05))), 2))),
                        self_regulation_score=max(45, min(95, 82 - student_index * 6 + random.randint(-4, 5))),
                    )

                for meeting_index in range(5):
                    AttendanceRecord.objects.create(
                        student=student,
                        course=course,
                        lesson_date=date(2026, 3, 1) + timedelta(days=meeting_index * 7),
                        status=random.choices(
                            ['present', 'late', 'absent'],
                            weights=[0.72 - student_index * 0.04, 0.18, 0.10 + student_index * 0.04],
                            k=1,
                        )[0],
                        participation_score=max(45, min(95, 78 - student_index * 5 + random.randint(-10, 10))),
                    )

            if student_index < 4:
                intervention_title, strategy_type, priority = priority_templates[student_index]
                PedagogicalIntervention.objects.create(
                    student=student,
                    course=courses[student_index % len(courses)],
                    title=intervention_title,
                    strategy_type=strategy_type,
                    rationale='��������� ����������� ������������, ������������� � ������������ ������� �������� ���������.',
                    recommended_actions='�������� �������, ����������� �����-����, ������������ �������, ���-���� � ������������ ������.',
                    expected_outcome='�������� �����, ���� ������������� ������������ � ����� ������� ���������� � LMS.',
                    priority=priority,
                    is_applied=student_index % 2 == 0,
                )

        self.stdout.write(self.style.SUCCESS('���������������� ������ ������� �������.'))
        self.stdout.write(self.style.SUCCESS('Demo login: researcher / Research2026!'))
