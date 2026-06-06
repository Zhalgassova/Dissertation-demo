from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Teacher(TimestampedModel):
    full_name = models.CharField(max_length=150)
    department = models.CharField(max_length=150)
    position = models.CharField(max_length=120, default='������')
    research_focus = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return self.full_name


class Student(TimestampedModel):
    full_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    cohort = models.CharField(max_length=50, help_text='��������: 2023')
    study_group = models.CharField(max_length=50)
    enrollment_year = models.PositiveIntegerField()
    prior_gpa = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    learning_preferences = models.CharField(max_length=255, blank=True)
    support_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return self.full_name


class Course(TimestampedModel):
    SEMESTER_CHOICES = [
        ('autumn', '�������'),
        ('spring', '��������'),
    ]
    FORMAT_CHOICES = [
        ('blended', '���������'),
        ('online', '������'),
        ('offline', '�����'),
    ]

    title = models.CharField(max_length=150)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField()
    semester = models.CharField(max_length=20, choices=SEMESTER_CHOICES)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='courses')
    ects_credits = models.PositiveIntegerField(default=3)
    delivery_format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default='blended')

    class Meta:
        ordering = ['title']

    def __str__(self):
        return f'{self.code} - {self.title}'


class Enrollment(TimestampedModel):
    STATUS_CHOICES = [
        ('active', '�������'),
        ('support', '����� ���������'),
        ('completed', '��������'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    target_grade = models.PositiveIntegerField(default=85)
    current_grade = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    progress_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    class Meta:
        unique_together = ('student', 'course')
        ordering = ['course__title', 'student__full_name']

    def __str__(self):
        return f'{self.student} -> {self.course}'


class Assessment(TimestampedModel):
    TYPE_CHOICES = [
        ('quiz', '����'),
        ('project', '������'),
        ('exam', '�������'),
        ('lab', '������������'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assessments')
    title = models.CharField(max_length=120)
    assessment_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    max_score = models.PositiveIntegerField(default=100)
    weight = models.DecimalField(max_digits=4, decimal_places=2, default=0.20)
    due_date = models.DateField()

    class Meta:
        ordering = ['course__title', 'due_date']

    def __str__(self):
        return f'{self.course.code}: {self.title}'


class AssessmentResult(TimestampedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='assessment_results')
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='results')
    score = models.DecimalField(max_digits=6, decimal_places=2)
    submitted_at = models.DateTimeField()
    attempt_number = models.PositiveSmallIntegerField(default=1)
    feedback = models.TextField(blank=True)

    class Meta:
        ordering = ['student__full_name', 'assessment__due_date']

    def __str__(self):
        return f'{self.student} - {self.assessment}: {self.score}'


class AttendanceRecord(TimestampedModel):
    STATUS_CHOICES = [
        ('present', '�������������'),
        ('late', '�������'),
        ('absent', '������������'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='attendance_records')
    lesson_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    participation_score = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-lesson_date']

    def __str__(self):
        return f'{self.student} - {self.lesson_date}: {self.status}'


class EngagementSnapshot(TimestampedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='engagement_snapshots')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='engagement_snapshots')
    week_start = models.DateField()
    platform_logins = models.PositiveIntegerField(default=0)
    minutes_online = models.PositiveIntegerField(default=0)
    forum_posts = models.PositiveIntegerField(default=0)
    assignment_timeliness = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1.00,
        help_text='���� ������������ ����������� ����� �� 0 �� 1.',
    )
    self_regulation_score = models.PositiveIntegerField(default=50, help_text='������ ������� ��������������� 0-100')

    class Meta:
        ordering = ['-week_start']
        unique_together = ('student', 'course', 'week_start')

    def __str__(self):
        return f'{self.student} - {self.course.code} - {self.week_start}'


class PedagogicalIntervention(TimestampedModel):
    PRIORITY_CHOICES = [
        ('high', '�������'),
        ('medium', '�������'),
        ('low', '������'),
    ]
    STRATEGY_CHOICES = [
        ('mentoring', '��������������'),
        ('adaptive', '���������� �������'),
        ('feedback', '����������� �������� �����'),
        ('peer', '��������������'),
        ('motivation', '������������� ���������'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='interventions')
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='interventions',
    )
    title = models.CharField(max_length=150)
    strategy_type = models.CharField(max_length=20, choices=STRATEGY_CHOICES)
    rationale = models.TextField()
    recommended_actions = models.TextField()
    expected_outcome = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    is_applied = models.BooleanField(default=False)

    class Meta:
        ordering = ['priority', '-created_at']

    def __str__(self):
        return self.title


class AnalysisDataset(TimestampedModel):
    STATUS_CHOICES = [
        ('draft', '����'),
        ('processing', '??������'),
        ('ready', '�����'),
        ('failed', '?���'),
    ]

    title = models.CharField(max_length=180)
    teacher_name = models.CharField(max_length=180, blank=True)
    subject_title = models.CharField(max_length=180, blank=True)
    cohort_label = models.CharField(max_length=120, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    source_file = models.FileField(upload_to='analysis_uploads/')
    file_type = models.CharField(max_length=20, blank=True)
    sheet_name = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    row_count = models.PositiveIntegerField(default=0)
    detected_columns = models.JSONField(default=dict, blank=True)
    summary_json = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class PerformanceRecord(TimestampedModel):
    ATTENDANCE_CHOICES = [
        ('present', '?������'),
        ('late', '������'),
        ('absent', '?��������'),
        ('unknown', '������'),
    ]
    LEVEL_CHOICES = [
        ('low', '�?���'),
        ('medium', '������'),
        ('high', '��?���'),
    ]

    dataset = models.ForeignKey(AnalysisDataset, on_delete=models.CASCADE, related_name='records')
    student_name = models.CharField(max_length=180)
    student_email = models.EmailField(blank=True)
    group_name = models.CharField(max_length=120, blank=True)
    subject_name = models.CharField(max_length=160, blank=True)
    lesson_topic = models.CharField(max_length=200, blank=True)
    lesson_date = models.DateField(null=True, blank=True)
    raw_score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    max_score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    percentage = models.DecimalField(max_digits=6, decimal_places=2)
    attendance_status = models.CharField(max_length=20, choices=ATTENDANCE_CHOICES, default='unknown')
    performance_level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    source_row_number = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['student_name', 'subject_name', 'lesson_date']

    def __str__(self):
        return f'{self.student_name} - {self.subject_name} ({self.percentage}%)'


class TeacherStudentComment(TimestampedModel):
    dataset = models.ForeignKey(AnalysisDataset, on_delete=models.CASCADE, related_name='teacher_comments')
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_comments')
    student_name = models.CharField(max_length=180)
    student_email = models.EmailField(blank=True)
    group_name = models.CharField(max_length=120, blank=True)
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ('dataset', 'teacher', 'student_name')
        ordering = ['student_name']

    def __str__(self):
        return f'{self.student_name} / {self.teacher}'
