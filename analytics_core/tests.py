from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (
    AnalysisDataset,
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
from .services.analytics import build_dashboard_context, build_student_profile


TEST_MEDIA_ROOT = str(Path(settings.BASE_DIR) / 'test_media')


class AnalyticsViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='tester', password='StrongPass123!')
        self.client.force_login(self.user)
        teacher = Teacher.objects.create(
            full_name='����� �������',
            department='���������� � �������� ����������',
            position='���������',
        )
        student = Student.objects.create(
            full_name='����� ��������',
            email='alina@example.com',
            cohort='2024',
            study_group='��-11',
            enrollment_year=2024,
            prior_gpa=Decimal('4.60'),
        )
        course = Course.objects.create(
            title='��������������� ���������',
            code='EDA-101',
            description='���� �� ������� ��������� ����� �����������.',
            semester='spring',
            teacher=teacher,
            ects_credits=5,
        )
        Enrollment.objects.create(
            student=student,
            course=course,
            current_grade=Decimal('78.00'),
            progress_pct=Decimal('64.00'),
            status='active',
        )
        assessment = Assessment.objects.create(
            course=course,
            title='��������������� ����',
            assessment_type='quiz',
            max_score=100,
            weight=Decimal('0.20'),
            due_date=date(2026, 4, 1),
        )
        AssessmentResult.objects.create(
            student=student,
            assessment=assessment,
            score=Decimal('76.00'),
            submitted_at=timezone.make_aware(datetime(2026, 4, 1, 12, 0)),
            feedback='����� ��������� �� ������������ ������.',
        )
        AttendanceRecord.objects.create(
            student=student,
            course=course,
            lesson_date=date(2026, 4, 3),
            status='present',
            participation_score=82,
        )
        EngagementSnapshot.objects.create(
            student=student,
            course=course,
            week_start=date(2026, 3, 30),
            platform_logins=8,
            minutes_online=165,
            forum_posts=4,
            assignment_timeliness=Decimal('0.90'),
            self_regulation_score=74,
        )
        PedagogicalIntervention.objects.create(
            student=student,
            course=course,
            title='����������� ������������',
            strategy_type='feedback',
            rationale='������������� ��������� ���� ��������.',
            recommended_actions='�������� ������������ ������������ � ������ ������ �������������� ������.',
            expected_outcome='��������� �������� ������������ � ���� ������������.',
            priority='medium',
        )
        self.student = student

    def test_dashboard_page_opens(self):
        response = self.client.get(reverse('analytics_core:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_student_page_opens(self):
        response = self.client.get(reverse('analytics_core:student_detail', args=[self.student.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student.full_name)

    def test_dashboard_context_contains_metrics(self):
        context = build_dashboard_context()
        self.assertGreaterEqual(context['totals']['students'], 1)
        self.assertIn('risk_distribution', context)

    def test_student_profile_contains_recommendations(self):
        profile = build_student_profile(self.student)
        self.assertTrue(profile['recommendations'])


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class UploadAnalysisTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='uploader', password='StrongPass123!')
        self.client.force_login(self.user)

    def _upload_long_dataset(self):
        csv_content = "\n".join(
            [
                "student,group,subject,topic,date,score,max_score,attendance",
                "Amina,8A,Mathematics,Fractions,2026-04-01,42,100,present",
                "Amina,8A,Mathematics,Equations,2026-04-05,58,100,present",
                "Dias,8A,Mathematics,Fractions,2026-04-01,34,100,absent",
                "Dana,8B,Physics,Motion,2026-04-02,77,100,present",
                "Dana,8B,Physics,Force,2026-04-06,71,100,late",
                "Miras,8B,Physics,Motion,2026-04-02,88,100,present",
            ]
        ).encode('utf-8')
        upload = SimpleUploadedFile('results.csv', csv_content, content_type='text/csv')
        self.client.post(
            reverse('analytics_core:upload_dataset'),
            {
                'title': '8-����� �?�������',
                'notes': '��������� �����?�� ����',
                'source_file': upload,
            },
            follow=True,
        )
        return AnalysisDataset.objects.get(title='8-����� �?�������')

    def _upload_wide_dataset(self):
        csv_content = "\n".join(
            [
                "���,���,1 ����? 1 ��������,1 ����? 2 ��������,1 ����? 3 ��������,2 ����? 1 ��������,2 ����? 2 ��������,2 ����? 3 ��������,3 ����? 1 ��������,3 ����? 2 ��������,3 ����? 3 ��������,4 ����? 1 ��������,4 ����? 2 ��������,4 ����? 3 ��������,5 ����? 1 ��������,5 ����? 2 ��������,5 ����? 3 ��������,6 ����? 1 ��������,6 ����? 2 ��������,6 ����? 3 ��������",
                "������ ����?���,�����������,4,5,4,4,5,5,3,4,4,5,5,4,4,4,5,5,5,5",
                "�?��?���� ���?��?��,��?����,3,3,4,3,4,4,2,3,3,4,4,3,3,3,4,4,4,4",
            ]
        ).encode('utf-8')
        upload = SimpleUploadedFile('wide_results.csv', csv_content, content_type='text/csv')
        self.client.post(
            reverse('analytics_core:upload_dataset'),
            {
                'title': '��? ��������?� �����������',
                'notes': '8 ����??� ??��� ??�������? ?��?�����?�� ?���',
                'source_file': upload,
            },
            follow=True,
        )
        return AnalysisDataset.objects.get(title='��? ��������?� �����������')

    def test_csv_upload_builds_dataset_summary(self):
        dataset = self._upload_long_dataset()
        response = self.client.get(reverse('analytics_core:analysis_detail', args=[dataset.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(dataset.status, 'ready')
        self.assertEqual(dataset.row_count, 6)
        self.assertGreaterEqual(len(dataset.summary_json.get('charts', [])), 10)
        self.assertIn('comparison', dataset.summary_json)
        self.assertContains(response, 'p-value')

    def test_wide_format_upload_is_supported(self):
        dataset = self._upload_wide_dataset()
        response = self.client.get(reverse('analytics_core:analysis_panel'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(dataset.status, 'ready')
        self.assertEqual(dataset.summary_json['metrics']['format_type'], 'wide')
        self.assertEqual(dataset.summary_json['metrics']['groups'], 2)
        self.assertContains(response, '23 ������')
        self.assertIn('prepost', dataset.summary_json)

    def test_student_profile_and_report_download_work(self):
        dataset = self._upload_wide_dataset()

        student_response = self.client.get(
            reverse('analytics_core:analysis_student_detail', args=[dataset.id]),
            {'name': '������ ����?���'},
        )
        self.assertEqual(student_response.status_code, 200)
        self.assertContains(student_response, '������ ����?���')

        report_response = self.client.get(reverse('analytics_core:download_report', args=[dataset.id]))
        self.assertEqual(report_response.status_code, 200)
        self.assertEqual(
            report_response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )

        pdf_response = self.client.get(reverse('analytics_core:download_pdf_analysis', args=[dataset.id]))
        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(pdf_response['Content-Type'], 'application/pdf')

    def test_template_download_works(self):
        response = self.client.get(reverse('analytics_core:download_template'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    def test_locked_sections_without_active_file(self):
        self.client.get(reverse('analytics_core:analysis_lab'))
        response = self.client.get(reverse('analytics_core:analysis_table'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '���� �������� ��?')
