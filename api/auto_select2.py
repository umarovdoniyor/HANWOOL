from django.core.paginator import Paginator
from django.http import JsonResponse
from api.models import CodeMaster, CodeGroup, UserMaster, CompanyMaster, SalaryItem, ProjectManage, FactoryItem, \
    FactoryCustomer, CompanyCard
from django.db.models import Q
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, time

def sel2_user(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    # sel2_user_avatar/?me=true
    withme = request.GET.get('me', 'false').lower() == 'true'  # "true"일 때만 본인 포함

    options = UserMaster.objects.filter(company=company, name__icontains=query).select_related('job_level')

    if not withme:
        options = options.exclude(Q(id=request.user.id) | Q(is_staff=False))  # 본인 제외
    else:
        options = options.exclude(is_staff=False)  # 본인 포함

    options = options.order_by('name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = []
    for user in page_obj:
        name = user.name
        job_level = user.job_level.name if user.job_level else ''
        avatar_url = user.profile_image.url

        text = f"{name} {job_level}".strip()
        results.append({
            'id': user.id,
            'text': text,
            'avatar': avatar_url
        })

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_user_manager(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    # sel2_user_avatar/?me=true
    withme = request.GET.get('me', 'false').lower() == 'true'  # "true"일 때만 본인 포함

    options = UserMaster.objects.filter(work_type="관리직", company=company, name__icontains=query).select_related('job_level')

    if not withme:
        options = options.exclude(Q(id=request.user.id) | Q(is_staff=False))  # 본인 제외
    else:
        options = options.exclude(is_staff=False)  # 본인 포함

    options = options.order_by('name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = []
    for user in page_obj:
        name = user.name
        job_level = user.job_level.name if user.job_level else ''
        avatar_url = user.profile_image.url
        monthly_leave = 0
        retire_date = user.retire_date
        if retire_date is None:
            diff = relativedelta(date.today(), user.join_date)
            for idx in range(diff.years):
                if idx <= 1:
                    monthly_leave += 15
                else:
                    monthly_leave += (idx - 1) + 15
        text = f"{name} {job_level}".strip()
        results.append({
            'id': user.id,
            'text': text,
            'etc': monthly_leave,
            'avatar': avatar_url
        })

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_group(request):
    query = request.GET.get('q', '').strip()  # 검색어
    page = int(request.GET.get('page', 1))

    # CodeGroup에서 직접 필터링
    options = [
        {'id': choice.value, 'text': choice.label}
        for choice in CodeGroup
        if not query or query.lower() in choice.label.lower()
    ]

    # 페이징 적용
    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
        'id': item['id'],
        'text': item['text'],
    } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_event_category(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.EVENT_CATEGORY, name__icontains=query, company=company).order_by('name').values('id', 'name')

    # sel2_code_event_category/?cal=true
    calendar = request.GET.get('cal', 'false').lower() == 'true'  # "true"일 때 휴가, 출장 제외

    if calendar:
        options = options.exclude(Q(name__iexact="휴가") | Q(name__iexact="출장"))  # "true"일 때 휴가, 출장 제외

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_team(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.TEAM, name__icontains=query, company=company).order_by('name').values('id', 'name')

    paginator = Paginator(options, 300)  # 페이지 벗어난 항목을 불러오는 문제 임시조치 (속도문제있을수있음)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_job_title(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.JOB_TITLE, name__icontains=query, company=company).order_by('name').values('id', 'name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_job_level(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.JOB_LEVEL, name__icontains=query, company=company).order_by('name').values('id', 'name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_bank(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.BANK, name__icontains=query, company=company).order_by('name').values('id', 'name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_card_account(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.CARD_ACCOUNT, name__icontains=query, company=company).order_by('name').values('id', 'name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_cost_account(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.COST_ACCOUNT, name__icontains=query, company=company).order_by('name').values('id', 'name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_customer_class(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.CUSTOMER_CLASS, name__icontains=query, company=company).order_by('name').values('id', 'name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_recruit_site(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.RECRUIT_SITE, name__icontains=query, company=company).order_by('name').values('id', 'name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_subsidiary(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.SUBSIDIARY, name__icontains=query, company=company).order_by('order', 'name').values('id', 'name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_daily_wage(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.DAILY_WAGE, name__icontains=query, company=company).order_by('name').values('id', 'name', 'price', 'desc1')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
            'price': item['price'],
            'desc1': item['desc1'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_daily_worktime(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.DAILY_WORKTIME, name__icontains=query, company=company).order_by('name').values('id', 'name', 'desc1')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
            'desc1': item['desc1'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_board_category(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.BOARD_CATEGORY, name__icontains=query, company=company).order_by('name').values('id', 'name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_asset_category(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.ASSET_CATEGORY, name__icontains=query, company=company).order_by('name').values('id', 'name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_item_class(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.FACTORY_ITEM_CLASS, name__icontains=query, company=company).order_by('name').values('id', 'name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_unit(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.FACTORY_ITEM_UNIT, name__icontains=query, company=company).order_by('name').values('id', 'name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_warehouse(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.FACTORY_WAREHOUSE, name__icontains=query, company=company).order_by('name').values('id', 'name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_process(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.FACTORY_PROCESS, name__icontains=query, company=company).order_by('name').values('id', 'name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_workshop(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.FACTORY_WORKSHOP, name__icontains=query, company=company).order_by('name').values('id', 'name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_faulty_class(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.FACTORY_FAULTY_CLASS, name__icontains=query, company=company).order_by('name').values('id', 'name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_factory_event_category(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.FACTORY_EVENT_CATEGORY, name__icontains=query, company=company).order_by('name').values('id', 'name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_company(request):
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CompanyMaster.objects.filter(
        name__icontains=query).order_by('id').values('id', 'name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_company_card(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CompanyCard.objects.filter(company=company, is_valid=True, name__icontains=query).order_by('name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
        'id': item.id,
        'text': f"[{item.code}] {item.name}",
    } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_my_salary(request):
    query = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))

    options = SalaryItem.objects.select_related('salary').filter(user=request.user)

    if query.isdigit():
        options = options.filter(
            Q(salary__year=query) | Q(salary__month=query)
        )

    options = options.order_by('salary__year', 'salary__month').values('id', 'salary__year', 'salary__month')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
        'id': item['id'],
        'text': f"{item['salary__year']}년 {item['salary__month']}월",
    } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_prj_cat1(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.PROJECT_CATEGORY, desc3='cat1', name__icontains=query, company=company).order_by('name').values('id', 'name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_prj_cat2(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.PROJECT_CATEGORY, desc3='cat2', name__icontains=query, company=company).order_by('name').values('id', 'name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_code_prj_cat3(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = CodeMaster.objects.filter(
        group=CodeGroup.PROJECT_CATEGORY, desc3='cat3', name__icontains=query, company=company).order_by('name').values('id', 'name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
            'id': item['id'],
            'text': item['name'],
        } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_project(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = ProjectManage.objects.filter(company=company, title__icontains=query).order_by('title')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
        'id': item.id,
        'text': item.title,
    } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_factory_item(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = FactoryItem.objects.filter(company=company, is_valid=True, name__icontains=query).order_by('name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
        'id': item.id,
        'text': f"[{item.code}] {item.name}",
    } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_factory_all_customer(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = FactoryCustomer.objects.filter(company=company, name__icontains=query).order_by('name')

    customer_class_id = request.GET.get('customer_class_id', None)
    if customer_class_id:
        options = options.filter(customer_class_id=customer_class_id)

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
        'id': item.id,
        'text': f"[{item.code}] {item.name}",
    } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_hanwool_subsidiary(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = FactoryCustomer.objects.filter(customer_class__name="관리법인", company=company, name__icontains=query).order_by('order', 'name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
        'id': item.id,
        'text': f"{item.name}",
    } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_hanwool_customer(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    subsidiary = request.GET.get('subsidiary', '')
    page = int(request.GET.get('page', 1))

    options = FactoryCustomer.objects.filter(company=company, name__icontains=query)
    if subsidiary:
        qs = FactoryCustomer.objects.filter(id=subsidiary).values("subsidiary_code_id").first()
        options = options.filter(subsidiary_code_id=qs["subsidiary_code_id"]).exclude(id=subsidiary)
    options = options.order_by('name')
    options = options.exclude(customer_class__name="관리법인")

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
        'id': item.id,
        'text': f"[{item.code}] {item.name}",
    } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_factory_customer(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = FactoryCustomer.objects.filter(company=company, customer_type__in=["고객사", "공급사&고객사"], name__icontains=query).order_by('name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
        'id': item.id,
        'text': f"[{item.code}] {item.name}",
    } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})


def sel2_factory_supplier(request):
    company = request.user.company
    query = request.GET.get('q', '')  # 검색어
    page = int(request.GET.get('page', 1))

    options = FactoryCustomer.objects.filter(company=company, customer_type__in=["공급사", "공급사&고객사"], name__icontains=query).order_by('name')

    paginator = Paginator(options, 300)
    page_obj = paginator.get_page(page)

    results = [{
        'id': item.id,
        'text': f"[{item.code}] {item.name}",
    } for item in page_obj]

    return JsonResponse({'results': results, 'pagination': {'more': page_obj.has_next()}})

def sel2_code_menu(request):
    menu_access = request.user.menu_access
    desc1 = request.GET.get('desc1', '')
    desc2 = request.GET.get('desc2', '')
    options = CodeMaster.objects.filter(group=CodeGroup.MENU)
    """
    options = options.filter(desc1=desc1)
    if desc2:
        options = options.filter(desc2=desc2)
    else:
        options = options.filter(desc2='')
    """
    options = options.order_by('desc1', 'id').values('id', 'name', 'desc1', 'desc2', 'desc3', 'desc4', 'desc5', 'price')

    results = [{
            'id': item['id'],
            'text': item['name'],
            'desc1': item['desc1'],
            'desc2': item['desc2'],
            'desc3': item['desc3'],
            'desc4': item['desc4'],
            'desc5': item['desc5'],
            'price': item['price'],
        } for item in options]

    return JsonResponse({'results': results, 'menu_access': menu_access})