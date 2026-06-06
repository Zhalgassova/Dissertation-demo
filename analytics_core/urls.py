from django.urls import path

from . import views

app_name = 'analytics_core'

urlpatterns = [
    path('', views.home, name='home'),
    path('demo/open/', views.quick_demo_entry, name='quick_demo_entry'),
    path('accounts/register/', views.register_teacher, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('students/<int:student_id>/', views.student_detail, name='student_detail'),
    path('interventions/', views.interventions, name='interventions'),
    path('lab/', views.analysis_lab, name='analysis_lab'),
    path('lab/upload/', views.upload_dataset, name='upload_dataset'),
    path('lab/template/', views.download_template, name='download_template'),
    path('lab/<int:dataset_id>/open/', views.activate_dataset, name='activate_dataset'),
    path('lab/<int:dataset_id>/select/', views.select_teacher_dataset, name='select_teacher_dataset'),
    path('lab/table/', views.analysis_table, name='analysis_table'),
    path('lab/panel/', views.analysis_dashboard_section, name='analysis_panel'),
    path('lab/statistics/', views.analysis_statistics_section, name='analysis_statistics'),
    path('lab/ai-summary/', views.analysis_ai_section, name='analysis_ai'),
    path('lab/<int:dataset_id>/', views.analysis_detail, name='analysis_detail'),
    path('lab/<int:dataset_id>/student/', views.analysis_student_detail, name='analysis_student_detail'),
    path('lab/<int:dataset_id>/report/docx/', views.download_report, name='download_report'),
    path('lab/<int:dataset_id>/report/xlsx/', views.download_excel_analysis, name='download_excel_analysis'),
    path('lab/<int:dataset_id>/report/pdf/', views.download_pdf_analysis, name='download_pdf_analysis'),
]
