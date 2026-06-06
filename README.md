# Educational Data Analytics Research Platform

Магистрлік диссертацияның практикалық бөлігіне арналған Django-жоба:

**«Білім беру деректерін талдау әдістері және оларды педагогикалық тәжірибеде қолдану»**

## Қысқаша сипаттама

Жүйе білім беру ұйымдарындағы эксперименттік және бақылау топтарының нәтижелерін жүктеп,
оларды ғылыми тұрғыда өңдейді, интерактивті визуализация жасайды, статистикалық салыстыру орындайды
және педагогикалық интерпретация береді.

## Негізгі мүмкіндіктер

- Django негізіндегі толық веб-қосымша
- CSV және Excel (`.csv`, `.xlsx`, `.xls`, `.xlsm`) жүктеу
- Файл жоқ кезде аналитиканы толық бұғаттау
- Файл жүктелгеннен кейін session арқылы аналитикалық бөлімдерді ашу
- Кең форматтағы деректі оқу:
  - `Student_ID | Group | Lesson_1_Task_1 ... Lesson_8_Task_3`
  - `ФИО | Топ | 1 сабақ 1 тапсырма ... 8 сабақ 3 тапсырма`
- HTML деректер кестесі:
  - топ бойынша фильтр
  - баға диапазоны бойынша фильтр
  - search
  - pagination
  - ascending / descending sort
- Plotly.js арқылы 23 интерактивті график
- Descriptive statistics:
  - mean
  - median
  - std
  - min
  - max
- Эксперимент vs бақылау салыстыруы:
  - `t-test`
  - `p-value`
  - `effect size`
  - мәтіндік интерпретация
- Rule-based AI қорытындысы:
  - қай топ тиімді
  - қай сабақтар қиын
  - қай студент әлсіз
  - қай сабақ / қай тапсырма әлсіз
  - мұғалімге және студентке ұсыныстар
- Экспорттар:
  - PDF
  - DOCX
  - Excel
- Excel шаблонын жүктеу
- Жеке студент профилі
- Демо аналитикалық бөлімдер мен интервенциялар модулі

## Қолданылған технологиялар

- Backend: Django
- Frontend: Bootstrap 5 + HTML + CSS + JavaScript
- Data processing: Pandas, NumPy
- Visualization: Plotly.js
- Statistics: SciPy (бар болса), fallback permutation test
- Reports: python-docx, reportlab, openpyxl
- AI: rule-based analytics

## Файл құрылымы

```text
thesis_platform/
analytics_core/
  services/
    analytics.py
    reporting.py
    research_analytics.py
    upload_analysis.py
  templates/analytics_core/
    home.html
    analysis_lab.html
    analysis_detail.html
    analysis_table.html
    analysis_dashboard_page.html
    analysis_statistics.html
    analysis_ai_summary.html
    analysis_student_detail.html
    analysis_locked.html
    dashboard.html
    interventions.html
    student_detail.html
  static/analytics_core/
    css/style.css
    js/plotly_renderer.js
  forms.py
  models.py
  urls.py
  views.py
templates/registration/
  login.html
sample_data/
README.md
manage.py
requirements.txt
```

## Орнату және іске қосу

```powershell
cd "C:\Users\Admin\Documents\Codex\2026-04-20-new-chat-2"
& "C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pip install -r requirements.txt
& "C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" manage.py migrate
& "C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" manage.py seed_demo_data --reset
& "C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" manage.py runserver
```

## Негізгі беттер

- `http://127.0.0.1:8000/` — басты бет
- `http://127.0.0.1:8000/lab/` — файл жүктеу
- `http://127.0.0.1:8000/lab/table/` — деректер кестесі
- `http://127.0.0.1:8000/lab/panel/` — аналитикалық панель
- `http://127.0.0.1:8000/lab/statistics/` — статистикалық талдау
- `http://127.0.0.1:8000/lab/ai-summary/` — ЖИ қорытындысы
- `http://127.0.0.1:8000/dashboard/` — демо dashboard
- `http://127.0.0.1:8000/interventions/` — интервенциялар

## Қолдану сценарийі

1. `/lab/` бетінде CSV/Excel файлын жүктеңіз
2. Сәтті жүктелгеннен кейін:
   - overview беті ашылады
   - деректер кестесі белсенді болады
   - аналитикалық панель белсенді болады
   - статистикалық талдау белсенді болады
   - ЖИ қорытындысы белсенді болады
3. Қажет болса PDF, DOCX немесе Excel экспортын жүктеңіз

## Үлгі файлдар

- [demo_results.csv](C:/Users/Admin/Documents/Codex/2026-04-20-new-chat-2/sample_data/demo_results.csv)
- [wide_experiment_template.csv](C:/Users/Admin/Documents/Codex/2026-04-20-new-chat-2/sample_data/wide_experiment_template.csv)

## Тестілеу

```powershell
& "C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" manage.py check
& "C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" manage.py test
```

## Ескерту

- Егер `scipy`, `plotly`, `openai` локалды ортада орнатылмаса, жоба негізгі логикамен бәрібір жұмыс істейді.
- Статистика үшін fallback механизмі бар.
- Visual layer Plotly.js CDN арқылы рендерленеді.
