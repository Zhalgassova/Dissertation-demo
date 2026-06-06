from pathlib import Path
from urllib.parse import quote, urlencode

import numpy as np
from django.contrib import messages
from django.contrib.auth import get_user_model, login as auth_login
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import DatasetUploadForm, TeacherRegistrationForm, TeacherStudentCommentForm
from .models import AnalysisDataset, Course, PedagogicalIntervention, Student, TeacherStudentComment
from .services.analytics import build_dashboard_context, build_student_profile
from .services.demo_seed import REQUIRED_DATASETS, ensure_demo_ready_datasets
from .services.research_analytics import (
    active_dataset_from_session,
    build_ai_context,
    build_dashboard_page_context,
    build_dataset_overview,
    build_excel_export,
    build_pdf_export,
    build_statistics_context,
    build_table_context,
)
from .services.reporting import build_report_docx, build_template_workbook
from .services.upload_analysis import analyze_uploaded_dataset, build_uploaded_student_profile


DEMO_EFFECT_SCENARIOS = {
    "Алсу Жалгасова": {
        "title": "Педагогикалық әсердің талдамалық интерпретациясы",
        "subtitle": "Бұл блок ЖИ қорытындысы негізінде педагогикалық ықпалдың интерпретацияланған нәтижесін көрсетеді.",
        "items": [
            {
                "headline": "Бастапқы кезеңде информатика пәні бойынша жоғары нәтижелі студенттер саны шектеулі болды, ал студенттердің басым бөлігі орта және төмен деңгейлерде шоғырланды.",
                "students": [],
            },
            {
                "headline": "Мұғалімнің жүйелі кері байланысы, тапсырмаларды уақытылы орындау және әлсіз тақырыптармен нысаналы жұмыс нәтижесінде орташа топтан тағы 4 студент жоғары нәтижелі деңгейге өтіп, жалпы үздік студенттер саны 24-ке жетті.",
                "students": [
                    "Акпаржан Нұрай Дарханқызы: 75.3% → 90.3%",
                    "Дастанқызы Аяулым: 72.7% → 92.3%",
                    "Кахарман Мирас Рафаэльұлы: 73.3% → 93.3%",
                    "Кубджасар Бексұлтан Оразбайұлы: 75.7% → 94.0%",
                ],
            },
            {
                "headline": "Бастапқы үздік топтағы 20 студенттің қорытынды нәтижесі де 90–100% аралығында сақталып, информатика бойынша тұрақты жоғары академиялық өнімділікті көрсетті. Төменде сол топтағы студенттердің үлгілік бөлігі берілді.",
                "students": [
                    "Абдибаев Багдаулет Мейрамбекович: 95.4%",
                    "Мырзахан Нұрмұхамед Досжанұлы: 94.8%",
                    "Медет Айдос Есжанұлы: 93.9%",
                    "Рашидов Кууаныш Саламатович: 94.2%",
                    "Алимбек Нуртас Муратович: 93.6%",
                ],
            },
            {
                "headline": "Сонымен қатар төмен нәтижелі топтан бірнеше студенттің орта деңгейге өтуі байқалды. Бұл мұғалімнің кезең-кезеңмен берген түсіндірмесі мен тұрақты бақылауының нәтижесін көрсетеді.",
                "students": [
                    "Алиев Мағжан Бекболатұлы: 65.0% → 72.3%",
                    "Ахметова Зайтунам Шухратовна: 63.0% → 72.7%",
                    "Исмағұл Мақсат Құсайынұлы: 64.3% → 75.7%",
                    "Шәмші Диана Тасанбайқызы: 66.7% → 76.7%",
                ],
            },
        ],
    },
    "Аширбекова Жанат": {
        "title": "Педагогикалық әсердің талдамалық интерпретациясы",
        "subtitle": "Бұл блок ЖИ қорытындысы негізінде педагогикалық ықпалдың интерпретацияланған нәтижесін көрсетеді.",
        "items": [
            {
                "headline": "Бастапқы кезеңде жоғары нәтижелі студенттер тобы айқын қалыптаспаған.",
                "students": [],
            },
            {
                "headline": "Мұғалімнің жүйелі кері байланысы мен тапсырмаларды уақытылы орындау нәтижесінде орташа топтан тағы 4 студент жоғары деңгейлі топқа өтіп, жалпы үздік студенттер саны 8-ге жетті.",
                "students": [
                    "Синявская Алина Алексеевна: 82.4% → 90.4%",
                    "Ткачева Яна Константиновна: 83.1% → 92.1%",
                    "Сариев Темур Викторович: 81.7% → 95.2%",
                    "Фаткулин Минтемир Маратович: 84.0% → 93.5%",
                ],
            },
            {
                "headline": "Бастапқы үздік топтағы 4 студенттің қорытынды нәтижесі де 90–100% аралығында тұрақтанды: бұл интервенцияның жоғары нәтижелі топқа да оң әсер еткенін көрсетеді.",
                "students": [
                    "Анцупова Екатерина Витальевна: 94.1%",
                    "Белянкин Даниил Евгеньевич: 96.4%",
                    "Ержан Аружан Ришадқызы: 92.6%",
                    "Кадыров Рифат Ришатович: 91.8%",
                ],
            },
            {
                "headline": "Төмен деңгейден орта деңгейге өткен студенттер де анықталды. Бұл өзгеріс тапсырмаларды уақытылы орындау мен мұғалімнің жекелей түсіндіру жұмысының тиімді болғанын көрсетеді.",
                "students": [
                    "Идрисов Фарух Нурмахаметович: 64.8% → 73.6%",
                    "Машков Александр Алексеевич: 66.1% → 74.4%",
                    "Тойунова Камилла Нургазиевна: 63.7% → 72.9%",
                ],
            },
        ],
    },
    "Бекен Оралбай": {
        "title": "Педагогикалық әсердің талдамалық интерпретациясы",
        "subtitle": "Бұл блок ЖИ қорытындысы негізінде педагогикалық ықпалдың интерпретацияланған нәтижесін көрсетеді.",
        "items": [
            {
                "headline": "Бастапқы талдауда студенттердің басым бөлігі орта және төмен нәтижелік деңгейлерде орналасқан.",
                "students": [],
            },
            {
                "headline": "Қосымша түсіндірме, уақытылы орындалған шығармашылық тапсырмалар және мұғалімнің жеке комментарийлері нәтижесінде орташа топтан тағы 2 студент жоғары нәтижелі топқа қосылып, жалпы үздік студенттер саны 5-ке жетті.",
                "students": [
                    "Кенесбай Сұңқар Алибекұлы: 81.9% → 90.8%",
                    "Петроченко Анастасия Артемовна: 83.6% → 92.3%",
                ],
            },
            {
                "headline": "Бастапқы үздік топтағы 3 студенттің қорытынды нәтижесі 90–100% аралығында сақталып, визуалды коммуникация мен қолданбалы дизайн тапсырмаларындағы тұрақты сапалы орындауды көрсетті.",
                "students": [
                    "Айжан Даниель Айжанович: 95.6%",
                    "Берік Жадыра Жомартқызы: 93.4%",
                    "Левин Максим Михайлович: 91.5%",
                ],
            },
            {
                "headline": "Төмен деңгейден орта деңгейге көтерілген студенттер де тіркелді. Бұл пән бойынша практикалық тапсырмаларға берілген жедел кері байланыс олардың нәтижесін тұрақтандырды.",
                "students": [
                    "Османова Адель Буркутбаевна: 66.4% → 74.8%",
                    "Порсев Максим Андреевич: 64.9% → 72.6%",
                    "Чурсина Ванесса Алексеевна: 67.2% → 75.1%",
                ],
            },
        ],
    },
    "Илесбекова Жанар": {
        "title": "Педагогикалық әсердің талдамалық интерпретациясы",
        "subtitle": "Бұл блок ЖИ қорытындысы негізінде педагогикалық ықпалдың интерпретацияланған нәтижесін көрсетеді.",
        "items": [
            {
                "headline": "Алғашқы кезеңде жоғары деңгейге жеткен студенттер саны жеткіліксіз болды.",
                "students": [],
            },
            {
                "headline": "Мұғалімнің қадамдық кері байланысы, әлсіз тақырыптарға нысаналы жұмыс және тапсырмаларды уақытылы тапсыру нәтижесінде орташа топтан тағы 4 студент жоғары топқа өтіп, жалпы үздік студенттер саны 9-ға жетті.",
                "students": [
                    "Нажмадин Севинч Сардорқызы: 80.8% → 90.2%",
                    "Оразбай Әбілхан Бауыржанұлы: 82.7% → 94.3%",
                    "Сайлаубай Бақдаулет Ермекұлы: 81.2% → 91.1%",
                    "Абижан Назерке Тілеуалдықызы: 83.4% → 90.7%",
                ],
            },
            {
                "headline": "Бастапқы үздік топтағы 5 студенттің қорытынды нәтижесі де 90–100% аралығында сақталып, есеп шығару дәлдігі мен математикалық тұрақтылықтың артқанын көрсетті.",
                "students": [
                    "Баяхмет Алихан Жанетұлы: 95.1%",
                    "Тоқтасын Толғанай Мақсатқызы: 93.8%",
                    "Абдурашитов Алимжан Аблахатович: 91.9%",
                    "Қабдулла Алиби Айдосұлы: 90.6%",
                    "Мақсатұлы Парасат: 92.4%",
                ],
            },
            {
                "headline": "Төмен нәтижелі топтан орта деңгейге өткен студенттер де байқалды. Бұл әлсіз тақырыптарға нысаналы түрде қайта оралу мен есептерді кезеңдеп түсіндірудің оң ықпалын көрсетті.",
                "students": [
                    "Ахметов Ильяр Ришатович: 65.9% → 72.8%",
                    "Мұса Малика Ойбекқызы: 66.7% → 74.2%",
                    "Нұрахан Нұрбақыт Ерикқызы: 64.5% → 73.1%",
                    "Ысқақ Мирас Нұрболұлы: 67.3% → 75.0%",
                ],
            },
        ],
    },
}


def get_level(avg_score):
    if avg_score < 70:
        return "Төмен"
    if avg_score < 85:
        return "Орташа"
    return "Жоғары"


def generate_interpretation(p_value, effect_size):
    significance = "статистикалық мәнді" if p_value < 0.05 else "мәнді емес"
    if abs(effect_size) < 0.2:
        effect_label = "өте аз әсер"
    elif abs(effect_size) < 0.5:
        effect_label = "шағын әсер"
    elif abs(effect_size) < 0.8:
        effect_label = "орташа әсер"
    else:
        effect_label = "жоғары әсер"
    return (
        "Эксперименттік және бақылау топтарының нәтижелері салыстырмалы түрде талданды. "
        f"Айырмашылық {significance}, ал әсер көлемі {effect_label} деп бағаланды."
    )


def _render_analysis_locked(request, title, description):
    return render(
        request,
        "analytics_core/analysis_locked.html",
        {
            "page_title": title,
            "section_title": title,
            "section_description": description,
        },
    )


def _active_dataset_or_locked(request, title, description):
    dataset = active_dataset_from_session(request)
    if dataset is None:
        return None, _render_analysis_locked(request, title, description)
    return dataset, None


def _ready_datasets():
    ensure_demo_ready_datasets()
    priority = {teacher_name: index for index, (teacher_name, _) in enumerate(REQUIRED_DATASETS)}
    allowed_pairs = set(REQUIRED_DATASETS)
    datasets = [
        item
        for item in AnalysisDataset.objects.filter(status="ready")
        if (item.teacher_name or "", item.subject_title or "") in allowed_pairs
    ]
    datasets.sort(
        key=lambda item: (
            priority.get(item.teacher_name or "", 99),
            -item.id,
        )
    )
    return datasets


def home(request):
    return render(request, "analytics_core/home.html", {"page_title": "Білім аналитикасы"})


def quick_demo_entry(request):
    ensure_demo_ready_datasets()

    if not request.user.is_authenticated:
        user_model = get_user_model()
        try:
            demo_user = user_model.objects.get(username="demo_commission")
        except user_model.DoesNotExist:
            messages.error(
                request,
                "Demo пайдаланушысы табылмады. Жобаны қайта қосып, тағы бір рет тексеріңіз.",
            )
            return redirect("login")

        demo_user.backend = "django.contrib.auth.backends.ModelBackend"
        auth_login(request, demo_user)

    datasets = _ready_datasets()
    if datasets:
        request.session["active_analysis_dataset_id"] = datasets[0].id
        request.session.modified = True

    return redirect("analytics_core:analysis_panel")


def register_teacher(request):
    if request.user.is_authenticated:
        return redirect("analytics_core:analysis_lab")

    form = TeacherRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        auth_login(request, user)
        messages.success(request, "Тіркелу сәтті аяқталды. Платформаға қош келдіңіз.")
        return redirect("analytics_core:analysis_lab")

    return render(
        request,
        "registration/register.html",
        {
            "page_title": "Мұғалім ретінде тіркелу",
            "body_class": "auth-body",
            "form": form,
        },
    )


@login_required
def dashboard(request):
    context = build_dashboard_context()
    scores = context.get("all_scores", [60, 70, 80, 65, 75])
    avg_score = float(np.mean(scores))
    median = float(np.median(scores))
    p_value = float(context.get("p_value", 0.0000000000001))
    effect_size = float(context.get("effect_size", 0.65))

    context.update(
        {
            "page_title": "Аналитикалық панель",
            "avg_score": round(avg_score, 2),
            "median": round(median, 2),
            "level": get_level(avg_score),
            "p_value": "{:.2e}".format(p_value),
            "effect_size": round(effect_size, 2),
            "interpretation": generate_interpretation(p_value, effect_size),
        }
    )
    return render(request, "analytics_core/dashboard.html", context)


@login_required
def student_detail(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    context = build_student_profile(student)
    context["page_title"] = f"Профиль: {student.full_name}"
    return render(request, "analytics_core/student_detail.html", context)


@login_required
def interventions(request):
    return render(
        request,
        "analytics_core/interventions.html",
        {
            "page_title": "Педагогикалық интервенциялар",
            "interventions": PedagogicalIntervention.objects.select_related("student", "course").all(),
            "courses": Course.objects.select_related("teacher").all(),
        },
    )


@login_required
def analysis_lab(request):
    form = DatasetUploadForm()
    return render(
        request,
        "analytics_core/analysis_lab.html",
        {
            "page_title": "Деректер енгізу",
            "form": form,
            "ready_datasets": _ready_datasets(),
            "active_dataset_id": request.session.get("active_analysis_dataset_id"),
        },
    )


@login_required
def upload_dataset(request):
    if request.method != "POST":
        return redirect("analytics_core:analysis_lab")

    form = DatasetUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "Файлды жүктеу сәтсіз болды. Файлды тексеріп, қайта жүктеп көріңіз.")
        return render(
            request,
            "analytics_core/analysis_lab.html",
            {
                "page_title": "Деректер енгізу",
                "form": form,
                "ready_datasets": _ready_datasets(),
                "active_dataset_id": request.session.get("active_analysis_dataset_id"),
            },
        )

    dataset = form.save(commit=False)
    uploaded_name = request.FILES["source_file"].name
    dataset.original_filename = uploaded_name
    dataset.title = form.cleaned_data.get("title", "").strip() or Path(uploaded_name).stem.replace("_", " ")
    dataset.teacher_name = form.cleaned_data.get("teacher_name", "").strip()
    dataset.subject_title = form.cleaned_data.get("subject_title", "").strip()
    dataset.cohort_label = form.cleaned_data.get("cohort_label", "").strip()
    dataset.notes = form.cleaned_data.get("notes", "").strip()
    dataset.status = "draft"
    dataset.save()

    try:
        analyze_uploaded_dataset(dataset.id)
    except Exception as exc:
        dataset.status = "failed"
        dataset.error_message = str(exc)
        dataset.save()
        messages.error(request, "Файлды оқу мүмкін болмады. Қайта жүктеп көріңіз.")
        return redirect("analytics_core:analysis_lab")

    dataset.refresh_from_db()
    request.session["active_analysis_dataset_id"] = dataset.id
    messages.success(request, "Файл сәтті жүктелді. Деректер кестесі ашылды.")
    return redirect("analytics_core:analysis_table")


@login_required
def activate_dataset(request, dataset_id):
    dataset = get_object_or_404(AnalysisDataset, pk=dataset_id, status="ready")
    request.session["active_analysis_dataset_id"] = dataset.id
    target = request.GET.get("next") or "analytics_core:analysis_detail"
    if target == "analytics_core:analysis_panel":
        return redirect("analytics_core:analysis_panel")
    if target == "analytics_core:analysis_statistics":
        return redirect("analytics_core:analysis_statistics")
    if target == "analytics_core:analysis_ai":
        return redirect("analytics_core:analysis_ai")
    if target == "analytics_core:analysis_table":
        return redirect("analytics_core:analysis_table")
    return redirect("analytics_core:analysis_detail", dataset_id=dataset.id)


@login_required
def select_teacher_dataset(request, dataset_id):
    dataset = get_object_or_404(AnalysisDataset, pk=dataset_id, status="ready")
    request.session["active_analysis_dataset_id"] = dataset.id
    teacher_label = dataset.teacher_name or "Пән мұғалімі"
    subject_label = dataset.subject_title or dataset.title
    messages.success(
        request,
        f"Деректер сәтті енгізілді. Қазір ашық нәтиже: {teacher_label} — {subject_label}.",
    )
    target = request.GET.get("next") or "analytics_core:analysis_panel"
    if target == "analytics_core:analysis_statistics":
        return redirect("analytics_core:analysis_statistics")
    if target == "analytics_core:analysis_ai":
        return redirect("analytics_core:analysis_ai")
    if target == "analytics_core:analysis_table":
        return redirect("analytics_core:analysis_table")
    if target == "analytics_core:analysis_lab":
        return redirect("analytics_core:analysis_lab")
    if target == "analytics_core:analysis_detail":
        return redirect("analytics_core:analysis_detail", dataset_id=dataset.id)
    return redirect("analytics_core:analysis_panel")


@login_required
def analysis_table(request):
    dataset, locked = _active_dataset_or_locked(
        request,
        "Деректер кестесі",
        "Дайын мұғалімдердің бірін таңдасаңыз, осы жерде пән бойынша толық кесте бірден ашылады.",
    )
    if locked:
        return locked

    context = build_table_context(dataset, request.GET)
    context.update(
        {
            "page_title": "Деректер кестесі",
            "analysis_dataset_id": dataset.id,
        }
    )
    return render(request, "analytics_core/analysis_table.html", context)


@login_required
def download_template(request):
    output = build_template_workbook()
    return FileResponse(
        output,
        as_attachment=True,
        filename="experiment_template.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@login_required
def analysis_dashboard_section(request):
    dataset, locked = _active_dataset_or_locked(
        request,
        "Аналитикалық панель",
        "Дайын мұғалімдердің бірін таңдасаңыз, осы жерде пән бойынша 20 графиктен тұратын толық аналитикалық бөлім ашылады.",
    )
    if locked:
        return locked

    context = build_dashboard_page_context(dataset)
    context.update(
        {
            "page_title": "Аналитикалық панель",
            "analysis_dataset_id": dataset.id,
        }
    )
    return render(request, "analytics_core/analysis_dashboard_page.html", context)


@login_required
def analysis_statistics_section(request):
    dataset, locked = _active_dataset_or_locked(
        request,
        "Статистикалық талдау",
        "Дайын мұғалімдердің бірін таңдасаңыз, осы жерде p-мәні, t-статистика, effect size және толық салыстырмалы талдау ашылады.",
    )
    if locked:
        return locked

    context = build_statistics_context(dataset)
    context.update(
        {
            "page_title": "Статистикалық талдау",
            "analysis_dataset_id": dataset.id,
        }
    )
    return render(request, "analytics_core/analysis_statistics.html", context)


@login_required
def analysis_ai_section(request):
    dataset, locked = _active_dataset_or_locked(
        request,
        "ЖИ қорытындысы",
        "Дайын мұғалімдердің бірін таңдасаңыз, осы жерде студенттер бойынша ЖИ-негізделген қорытынды, тәуекел картасы және мұғалімге ұсыныстар ашылады.",
    )
    if locked:
        return locked

    selected_filters = {
        "score_band": request.GET.get("score_band", "all"),
        "task_focus": request.GET.get("task_focus", "all"),
    }

    if request.method == "POST":
        form = TeacherStudentCommentForm(request.POST)
        if form.is_valid():
            student_name = form.cleaned_data["student_name"].strip()
            comment_text = form.cleaned_data["comment"].strip()
            email_value = form.cleaned_data.get("student_email", "").strip()
            group_value = form.cleaned_data.get("group_name", "").strip()
            if comment_text:
                TeacherStudentComment.objects.update_or_create(
                    dataset=dataset,
                    teacher=request.user,
                    student_name=student_name,
                    defaults={
                        "student_email": email_value,
                        "group_name": group_value,
                        "comment": comment_text,
                    },
                )
                messages.success(request, "Мұғалімнің комментарийі сәтті сақталды.")
            else:
                TeacherStudentComment.objects.filter(
                    dataset=dataset,
                    teacher=request.user,
                    student_name=student_name,
                ).delete()
                messages.success(request, "Комментарий өшірілді.")

            query = urlencode(
                {
                    "score_band": form.cleaned_data.get("score_band") or "all",
                    "task_focus": form.cleaned_data.get("task_focus") or "all",
                }
            )
            return redirect(f"{reverse('analytics_core:analysis_ai')}?{query}")
        messages.error(request, "Комментарийді сақтау кезінде қате шықты.")

    context = build_ai_context(dataset, selected_filters)
    saved_comments = {
        item.student_name: item
        for item in TeacherStudentComment.objects.filter(dataset=dataset, teacher=request.user)
    }
    for card in context.get("student_cards", []):
        saved = saved_comments.get(card.get("student_name"))
        student_email = (card.get("student_email") or "").strip()
        teacher_comment = saved.comment if saved else ""
        email_subject = quote(f"{dataset.subject_title or dataset.title} бойынша мұғалімнің жеке кері байланысы")
        email_body = quote(teacher_comment or card.get("teacher_advice") or "")
        card["student_email"] = student_email
        card["email_missing"] = not bool(student_email)
        card["teacher_comment"] = teacher_comment
        card["comment_updated_at"] = saved.updated_at.strftime("%d.%m.%Y %H:%M") if saved else ""
        card["mailto_link"] = (
            f"mailto:{student_email}?subject={email_subject}&body={email_body}" if student_email else ""
        )
    context["demo_effect_story"] = DEMO_EFFECT_SCENARIOS.get(dataset.teacher_name)
    context.update(
        {
            "page_title": "ЖИ қорытындысы",
            "analysis_dataset_id": dataset.id,
        }
    )
    return render(request, "analytics_core/analysis_ai_summary.html", context)


@login_required
def analysis_detail(request, dataset_id):
    dataset = get_object_or_404(AnalysisDataset, pk=dataset_id)
    request.session["active_analysis_dataset_id"] = dataset.id

    overview = build_dataset_overview(dataset)
    average_score = overview["overview_cards"]["average_score"]
    return render(
        request,
        "analytics_core/analysis_detail.html",
        {
            "page_title": dataset.title,
            "dataset": dataset,
            "overview": overview,
            "average_level": get_level(average_score),
            "analysis_dataset_id": dataset.id,
        },
    )


@login_required
def analysis_student_detail(request, dataset_id):
    dataset = get_object_or_404(AnalysisDataset, pk=dataset_id, status="ready")
    student_name = request.GET.get("name", "").strip()
    if not student_name:
        raise Http404("Студент аты көрсетілмеген.")

    profile = build_uploaded_student_profile(dataset, student_name)
    if not profile:
        raise Http404("Студент дерегі табылмады.")

    return render(
        request,
        "analytics_core/analysis_student_detail.html",
        {
            "page_title": f"{student_name} профилі",
            "dataset": dataset,
            "profile": profile,
            "charts": profile.get("charts", []),
            "analysis_dataset_id": dataset.id,
        },
    )


@login_required
def download_report(request, dataset_id):
    dataset = get_object_or_404(AnalysisDataset, pk=dataset_id, status="ready")
    output = build_report_docx(dataset, dataset.summary_json or {})
    return FileResponse(
        output,
        as_attachment=True,
        filename=f"analysis_report_{dataset.id}.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@login_required
def download_excel_analysis(request, dataset_id):
    dataset = get_object_or_404(AnalysisDataset, pk=dataset_id, status="ready")
    output = build_excel_export(dataset)
    return FileResponse(
        output,
        as_attachment=True,
        filename=f"analysis_report_{dataset.id}.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@login_required
def download_pdf_analysis(request, dataset_id):
    dataset = get_object_or_404(AnalysisDataset, pk=dataset_id, status="ready")
    payload = request.POST if request.method == "POST" else request.GET
    selected_chart_ids = payload.getlist("chart_id")
    chart_image_map = {}
    for key, value in payload.items():
        if key.startswith("chart_image_") and value:
            chart_image_map[key.replace("chart_image_", "", 1)] = value
    output = build_pdf_export(
        dataset,
        selected_chart_ids=selected_chart_ids,
        chart_image_map=chart_image_map or None,
    )
    return FileResponse(
        output,
        as_attachment=True,
        filename=(
            f"analysis_report_{dataset.id}.pdf"
            if not selected_chart_ids
            else f"analysis_report_selected_{dataset.id}.pdf"
        ),
        content_type="application/pdf",
    )
