from django.contrib import admin

from .models import (
    Assessment,
    AssessmentResult,
    AnalysisDataset,
    AttendanceRecord,
    Course,
    EngagementSnapshot,
    Enrollment,
    PedagogicalIntervention,
    PerformanceRecord,
    Student,
    Teacher,
)


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'department', 'position')
    search_fields = ('full_name', 'department')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'study_group', 'cohort', 'prior_gpa')
    list_filter = ('cohort', 'study_group')
    search_fields = ('full_name', 'email')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'teacher', 'semester', 'delivery_format')
    list_filter = ('semester', 'delivery_format')
    search_fields = ('code', 'title')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'current_grade', 'progress_pct', 'status')
    list_filter = ('status', 'course')
    search_fields = ('student__full_name', 'course__title')


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'assessment_type', 'weight', 'due_date')
    list_filter = ('assessment_type', 'course')


@admin.register(AssessmentResult)
class AssessmentResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'assessment', 'score', 'attempt_number', 'submitted_at')
    list_filter = ('assessment__course', 'assessment__assessment_type')
    search_fields = ('student__full_name', 'assessment__title')


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'lesson_date', 'status', 'participation_score')
    list_filter = ('status', 'course')


@admin.register(EngagementSnapshot)
class EngagementSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        'student',
        'course',
        'week_start',
        'platform_logins',
        'minutes_online',
        'assignment_timeliness',
    )
    list_filter = ('course', 'week_start')


@admin.register(PedagogicalIntervention)
class PedagogicalInterventionAdmin(admin.ModelAdmin):
    list_display = ('title', 'student', 'course', 'strategy_type', 'priority', 'is_applied')
    list_filter = ('strategy_type', 'priority', 'is_applied')
    search_fields = ('title', 'student__full_name')


@admin.register(AnalysisDataset)
class AnalysisDatasetAdmin(admin.ModelAdmin):
    list_display = ('title', 'original_filename', 'status', 'row_count', 'created_at')
    list_filter = ('status', 'file_type')
    search_fields = ('title', 'original_filename')


@admin.register(PerformanceRecord)
class PerformanceRecordAdmin(admin.ModelAdmin):
    list_display = (
        'student_name',
        'group_name',
        'subject_name',
        'lesson_date',
        'percentage',
        'performance_level',
    )
    list_filter = ('dataset', 'group_name', 'subject_name', 'performance_level', 'attendance_status')
    search_fields = ('student_name', 'subject_name', 'lesson_topic')
