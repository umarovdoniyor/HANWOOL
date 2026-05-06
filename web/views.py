from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse, Http404
from api.models import BoardMaster, ApvMaster, UserMaster, CodeMaster, CommentMaster, CompanyInfo, CodeGroup, \
    CompanyMaster, ReadStatus, ProjectManage, DailyWorkOrder, DailyWorker, GeneralWorkOrder, GeneralWorker, \
    FactoryCustomer, MonthlySales
from django.db.models import Q, Count, Subquery, OuterRef, F
from datetime import date
from django.views.decorators.cache import never_cache
from django.contrib import messages
import calendar
import logging
from device_detector import DeviceDetector


# 브랜드 페이지 영역 ------------------------------------------------------------------------------------------------------
def brand_page(request):
    context = {}
    return render(request, 'brand/brand_index.html', context)

# def brand_fn_intro_page(request):
#     context = {}
#     return render(request, 'brand/brand_fn_intro.html', context)


# 토스트 오피스 영역 ------------------------------------------------------------------------------------------------------
@never_cache
def login_page(request):
    if request.user.is_authenticated:
        return redirect('index_page')

    next_url = request.GET.get("next", "/")
    if next_url in ["", "/", "|", "/login/"]:
        next_url = "index_page"

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        remember_me = request.POST.get("remember_me")
        next_url = request.POST.get("next") or "index_page"

        user = authenticate(username=username, password=password)
        if user:
            # 업체 사용이 제한되었을 경우 접속금지
            if not hasattr(user, "company") or not user.company.is_valid:
                return render(request, 'login.html', {
                    "error": "접속이 제한된 업체입니다. 관리자에게 문의해주세요.",
                    "next": next_url
                })

            if not user.is_active:
                return render(request, 'login.html', {
                    "error": "접속이 제한된 사용자입니다. 관리자에게 문의해주세요.",
                    "next": next_url
                })

            login(request, user)

            if remember_me:
                request.session.set_expiry(60 * 60 * 24 * 7)  # 7일 유지
            else:
                request.session.set_expiry(0)  # 브라우저 종료 시 세션 만료

            return redirect(next_url)  # 로그인 후 정상적인 페이지로 이동
        else:
            return render(request, 'login.html',
                          {"error": "로그인에 실패하였습니다.<br>'아이디'와 '비밀번호' 확인 후에도 지속적으로 실패할 경우 업체관리자에게 문의주시기 바랍니다.",
                           "next": next_url})

    return render(request, 'login.html', {"next": next_url})


@login_required(login_url="/login/")
def index_page(request):
    # 로그인 후 `next=/` 같은 비정상적인 값이 들어오면 기본 페이지로 이동
    if request.GET.get("next") in ["", "/", "|", "/login/"]:
        return redirect("index_page")  # 기본 페이지로 이동

    qs = CompanyMaster.objects.filter(id=request.user.company.id)

    master_user_subquery = UserMaster.objects.filter(
        company_id=OuterRef('id'), is_master=True
    ).values('user_id')[:1]

    qs = qs.annotate(
        master_user_id=Subquery(master_user_subquery),
        active_users=Count('user_company', filter=Q(user_company__is_staff=True))
    )

    context = {
        'results': qs,
    }

    return render(request, "index.html", context)


@login_required(login_url="/login/")
def index2_page(request):
    # 로그인 후 `next=/` 같은 비정상적인 값이 들어오면 기본 페이지로 이동
    if request.GET.get("next") in ["", "/", "|", "/login/"]:
        return redirect("index_page")  # 기본 페이지로 이동

    qs = CompanyMaster.objects.filter(id=request.user.company.id)

    master_user_subquery = UserMaster.objects.filter(
        company_id=OuterRef('id'), is_master=True
    ).values('user_id')[:1]

    qs = qs.annotate(
        master_user_id=Subquery(master_user_subquery),
        active_users=Count('user_company', filter=Q(user_company__is_staff=True))
    )

    context = {
        'results': qs,
    }

    return render(request, "index2.html", context)


def dashboard_page(request):
    event_category = (CodeMaster.objects.filter(group=CodeGroup.EVENT_CATEGORY, company=request.user.company).
                      order_by('id').values('id', 'name', 'desc3'))
    context = {
        'event_category': event_category,
    }
    return render(request, "basic/dashboard.html", context)


# 게시판
def board_list_page(request, board_id=None):
    if board_id:
        board = get_object_or_404(BoardMaster, id=board_id, board_type='notice')

        context = {
            'board': board,
        }

    else:
        context = {}

    return render(request, 'board/board_list.html', context)

def board_read_page(request, board_id=None):
    request_user = request.user
    company_id = request_user.company.id

    board = get_object_or_404(BoardMaster, id=board_id, board_type='notice')

    # 회사 불일치 시 오류 페이지 이동
    if board.company_id != company_id:
        return render(request, 'error_page.html', {
            'message': '잘못된 접근입니다.'
        })

    # 조회수 증가
    BoardMaster.objects.filter(id=board_id).update(views_count=F('views_count') + 1)

    # 읽음 상태 업데이트
    ReadStatus.objects.get_or_create(
        user=request_user,
        board=board,
        company=request_user.company,
        defaults={'is_read': True}
    )

    comment_count = CommentMaster.objects.filter(board=board_id).count()

    context = {
        'board': board,
        'comment_count': comment_count,
    }
    return render(request, 'board/board_read.html', context)

def board_create_page(request, board_id=None):
    board = get_object_or_404(BoardMaster, id=board_id) if board_id else None
    context = {
        'board': board,
    }
    return render(request, 'board/board_create.html', context)


# 일정관리
def calendar_page(request):
    event_category = (CodeMaster.objects.filter(group=CodeGroup.EVENT_CATEGORY, company=request.user.company).
                      order_by('id').values('id', 'name', 'desc3'))
    context = {
        'event_category': event_category,
    }
    return render(request, 'basic/calendar.html', context)


# 전자결재
def approval_list_page(request):
    return render(request, 'approval/apv_list.html')

def approval_create_page(request, category_id, apv_id=None):
    if apv_id:
        # 수정 가능 조건:
        #   - 임시문서 (작성 중인 드래프트)
        #   - 본인이 작성한 반려문서 (수정 후 재요청)
        apv = ApvMaster.objects.filter(id=apv_id).only('status', 'created_by_id').first()
        if apv is None:
            return HttpResponseForbidden("잘못된 요청입니다.")
        is_draft = apv.status == '임시'
        is_owner_resubmit = apv.status == '반려' and apv.created_by_id == request.user.id
        if not (is_draft or is_owner_resubmit):
            return HttpResponseForbidden("잘못된 요청입니다.")

    user = request.user
    create_template = 'approval/template_' + category_id + '_create.html'
    company_info = CompanyInfo.objects.filter(company=user.company).first()
    context = {
        'category_id': category_id,
        'apv_id': apv_id,
        'leave_choices': ApvMaster.LEAVE_CHOICES,
        'apv_memo_1': getattr(company_info, "apv_memo_1", None) if company_info else None,
        'apv_memo_2': getattr(company_info, "apv_memo_2", None) if company_info else None,
        'apv_memo_3': getattr(company_info, "apv_memo_3", None) if company_info else None,
        'apv_memo_4': getattr(company_info, "apv_memo_4", None) if company_info else None,
        'apv_memo_5': getattr(company_info, "apv_memo_5", None) if company_info else None,
    }
    return render(request, create_template, context)

def approval_progress_page(request, category_id, apv_id):
    detail_template = 'approval/template_' + category_id + '_read.html'
    context = {
        'apv_id': apv_id,
        'category_id': category_id,
        'leave_choices': ApvMaster.LEAVE_CHOICES,
    }
    return render(request, detail_template, context)

def approval_cost_page(request):
    return render(request, 'approval/apv_cost.html')


# 근태관리
def worktime_list_page(request):
    context = {}
    return render(request, 'worktime/worktime_list.html', context)

def worktime_status_page(request):
    context = {}
    return render(request, 'worktime/worktime_status.html', context)

def worktime_report_page(request):
    company_year = request.user.company.created_at.year
    current_year = date.today().year
    year_range = range(company_year, current_year + 4)  # +3년까지

    context = {
        'year_range': year_range,
        'default_year': current_year,
    }
    return render(request, 'worktime/worktime_report.html', context)


# 휴가관리
@login_required(login_url='/login/')
def leave_manage_page(request):
    context = {}
    return render(request, 'leave/leave_manage.html', context)

@login_required(login_url='/login/')
def leave_report_page(request):
    current_year = date.today().year
    year_range = range(current_year - 4, current_year + 4)  # +3년까지

    context = {
        'year_range': year_range,
        'default_year': current_year,
    }
    return render(request, 'leave/leave_report.html', context)


# 프로젝트
def prj_gantt_page(request):
    return render(request, 'project/prj_gantt.html')

def prj_viewer_page(request, id):
    project = get_object_or_404(ProjectManage, id=id)

    context = {
        'project': project,
        'comment_count': project.comment_prj.count(),
    }
    return render(request, 'project/prj_viewer.html', context)

def task_gantt_page(request):
    return render(request, 'project/task_gantt.html')

def user_gantt_page(request):
    return render(request, 'project/user_gantt.html')


# 자산관리
def asset_public_page(request):
    return render(request, 'asset/asset_public.html')

def asset_private_page(request):
    return render(request, 'asset/asset_private.html')

def asset_item_page(request):
    return render(request, 'asset/asset_item.html')


# 조직관리
def employee_list_page(request):
    return render(request, 'employee/employee_list.html')

def org_chart_page(request):
    return render(request, 'employee/org_chart.html')


# 설정관리
def admin_employee_list_page(request):
    context = {}
    return render(request, 'admin/admin_employee_list.html', context)

def admin_employee_cert_page(request, u):
    user = get_object_or_404(UserMaster, id=u)
    if user.company.id != request.user.company.id:
        messages.error(request, "잘못된 접근입니다.")
        return redirect('error_page')

    context = {
        'user': user,
    }
    return render(request, 'admin/admin_employee_cert.html', context)

def admin_company_list_page(request):
    context = {}
    return render(request, 'admin/admin_company_list.html', context)

def admin_code_page(request):
    context = {}
    return render(request, 'admin/admin_code.html', context)

def admin_setting_page(request):
    context = {}
    return render(request, 'admin/admin_setting.html', context)

def myinfo_page(request):
    context = {}
    return render(request, 'basic/myinfo.html', context)

def noti_list_page(request):
    context = {}
    return render(request, 'basic/noti_list.html', context)

def error_page(request):
    context = {}
    return render(request, 'error_page.html', context)


# 급여정산
def salary_base_list_page(request):
    context = {}
    return render(request, 'admin/salary_base_list.html', context)

def salary_history_page(request):
    context = {}
    return render(request, 'admin/salary_history.html', context)

def my_salary_page(request):
    context = {}
    return render(request, 'basic/my_salary.html', context)




# 토스트 팩토리 영역 ------------------------------------------------------------------------------------------------------
@login_required(login_url="/login/")
def factory_index_page(request):
    # 로그인 후 `next=/` 같은 비정상적인 값이 들어오면 기본 페이지로 이동
    if request.GET.get("next") in ["", "/", "|", "/login/"]:
        return redirect("index_page")  # 기본 페이지로 이동

    qs = CompanyMaster.objects.filter(id=request.user.company.id)

    master_user_subquery = UserMaster.objects.filter(
        company_id=OuterRef('id'), is_master=True
    ).values('user_id')[:1]

    qs = qs.annotate(
        master_user_id=Subquery(master_user_subquery),
        active_users=Count('user_company', filter=Q(user_company__is_staff=True))
    )

    context = {
        'results': qs,
    }

    return render(request, 'factory/index.html', context)

def factory_dashboard_page(request):
    event_category = (CodeMaster.objects.filter(group=CodeGroup.FACTORY_EVENT_CATEGORY, company=request.user.company).
                      order_by('id').values('id', 'name', 'desc3'))
    context = {
        'event_category': event_category,
    }
    return render(request, "factory/dashboard.html", context)

def factory_guide_page(request):
    context = {}
    return render(request, 'factory/guide.html', context)

def factory_init_setup_page(request):
    context = {}
    return render(request, 'factory/init_setup.html', context)


# 설정관리
def factory_item_list_page(request):
    context = {}
    return render(request, 'factory/setting/item_list.html', context)

def factory_customer_list_page(request):
    context = {}
    return render(request, 'factory/setting/customer_list.html', context)

def factory_code_page(request):
    context = {}
    return render(request, 'factory/setting/code_list.html', context)


# 일정관리(팩토리)
def factory_calendar_page(request):
    event_category = (CodeMaster.objects.filter(group=CodeGroup.FACTORY_EVENT_CATEGORY, company=request.user.company).
                      order_by('id').values('id', 'name', 'desc3'))
    context = {
        'event_category': event_category,
    }
    return render(request, 'factory/calendar/calendar.html', context)


# 재고관리
def factory_inventory_list_page(request):
    context = {}
    return render(request, 'factory/inventory/inventory_list.html', context)

def factory_inventory_in_list_page(request):
    context = {}
    return render(request, 'factory/inventory/inventory_in.html', context)

def factory_inventory_out_list_page(request):
    context = {}
    return render(request, 'factory/inventory/inventory_out.html', context)


# 구매관리
def factory_po_list_page(request):
    sch_id = request.GET.get('sch_id', '')

    context = {
        'sch_id': sch_id,
    }
    return render(request, 'factory/purchase/po_list.html', context)

def factory_po_input_page(request):
    sch_id = request.GET.get('sch_id', '')

    context = {
        'sch_id': sch_id,
    }
    return render(request, 'factory/purchase/po_input.html', context)


# 생산관리
def factory_production_list_page(request):
    sch_id = request.GET.get('sch_id', '')

    context = {
        'sch_id': sch_id,
    }
    return render(request, 'factory/production/production_list.html', context)

def factory_production_status_page(request):
    sch_id = request.GET.get('sch_id', '')

    context = {
        'sch_id': sch_id,
    }
    return render(request, 'factory/production/production_status.html', context)


# 품질관리 - 추후 업데이트
def factory_quality_document_page(request):
    context = {}
    return render(request, 'factory/quality/quality_document.html', context)

def factory_quality_claim_page(request):
    context = {}
    return render(request, 'factory/quality/quality_claim.html', context)


# 영업관리
def factory_sales_quotation_list_page(request):
    sch_id = request.GET.get('sch_id', '')

    context = {
        'sch_id': sch_id,
    }
    return render(request, 'factory/sales/quotation_list.html', context)

def factory_sales_co_list_page(request):
    sch_id = request.GET.get('sch_id', '')

    context = {
        'sch_id': sch_id,
    }
    return render(request, 'factory/sales/co_list.html', context)

def factory_sales_delivery_list_page(request):
    sch_id = request.GET.get('sch_id', '')

    context = {
        'sch_id': sch_id,
    }
    return render(request, 'factory/sales/delivery_list.html', context)



# 일일근무관리
def daily_work_order_page(request):
    return render(request, 'hanwool/daily_work/daily_work_order.html')


def factory_customer_salary_page(request):
    return render(request, 'factory/setting/customer_salary.html')


def daily_worker_list_page(request, work_order_id=None):
    if not work_order_id:
        return HttpResponseForbidden("일일근무관리 문서가 누락되었습니다.")

    work_order = get_object_or_404(DailyWorkOrder, id=work_order_id)

    context = {
        'work_order': work_order,
    }

    return render(request, 'hanwool/daily_work/daily_worker_list.html', context)

def daily_work_contract_page(request, work_order_id=None, worker_id=None):
    referer = request.META.get('HTTP_REFERER')
    if not work_order_id:
        return HttpResponseForbidden("일일근무관리 문서가 누락되었습니다.")

    if not worker_id:
        return HttpResponseForbidden("근무자 정보가 누락되었습니다.")

    try:
        work_order = get_object_or_404(DailyWorkOrder, id=work_order_id)
        worker = get_object_or_404(DailyWorker, id=worker_id)
        company_info = CompanyInfo.objects.filter(company=worker.company).first()
    except Http404:
        return render(request, 'error_page.html', status=404)
    if worker.wage.price:
        wage_price = f"{int(worker.wage.price):,}"
    else:
        wage_price = 0
    user_agent_string = request.headers.get('User-Agent')
    device = DeviceDetector(user_agent_string).parse()
    context = {
        'work_order': work_order,
        'worker': worker,
        'company_info': company_info,
        'wage_price': wage_price,
        'referer': referer,
        'device_type': device.device_type(),
        'work_order_id': work_order_id,
        'worker_id': worker_id,
    }
    logging.debug("context:", context)
    return render(request, 'hanwool/daily_work/daily_work_contract.html', context)

def daily_work_contract_test_page(request, work_order_id=None, worker_id=None):
    referer = request.META.get('HTTP_REFERER')
    if not work_order_id:
        return HttpResponseForbidden("일일근무관리 문서가 누락되었습니다.")

    if not worker_id:
        return HttpResponseForbidden("근무자 정보가 누락되었습니다.")

    try:
        work_order = get_object_or_404(DailyWorkOrder, id=work_order_id)
        worker = get_object_or_404(DailyWorker, id=worker_id)
        company_info = CompanyInfo.objects.filter(company=worker.company).first()
    except Http404:
        return render(request, 'error_page.html', status=404)
    if worker.wage.price:
        wage_price = f"{int(worker.wage.price):,}"
    else:
        wage_price = 0
    user_agent_string = request.headers.get('User-Agent')
    device = DeviceDetector(user_agent_string).parse()
    context = {
        'work_order': work_order,
        'worker': worker,
        'company_info': company_info,
        'wage_price': wage_price,
        'referer': referer,
        'device_type': device.device_type()
    }
    logging.debug("context:", context)
    return render(request, 'hanwool/daily_work/daily_work_contract_test.html', context)

def daily_work_invoice_page(request, work_order_id=None):
    if not work_order_id:
        return HttpResponseForbidden("일일근무관리 문서가 누락되었습니다.")

    work_order = get_object_or_404(DailyWorkOrder, id=work_order_id)

    context = {
        'work_order': work_order,
    }

    return render(request, 'hanwool/daily_work/daily_work_invoice.html', context)


# 정규파견관리
def general_work_order_page(request):
    return render(request, 'hanwool/general_work/general_work_order.html')

def general_work_order_page2(request):
    return render(request, 'hanwool/general_work/general_work_order2.html')

def general_worker_list_page(request, work_order_id=None):
    if not work_order_id:
        return HttpResponseForbidden("일일근무관리 문서가 누락되었습니다.")

    work_order = get_object_or_404(GeneralWorkOrder, id=work_order_id)

    context = {
        'work_order': work_order,
    }

    return render(request, 'hanwool/general_work/general_worker_list.html', context)

def general_work_contract_page(request, work_order_id=None, worker_id=None):
    referer = request.META.get('HTTP_REFERER')
    if not work_order_id:
        return HttpResponseForbidden("정규파견관리 문서가 누락되었습니다.")

    if not worker_id:
        return HttpResponseForbidden("근무자 정보가 누락되었습니다.")

    try:
        work_order = get_object_or_404(GeneralWorkOrder, id=work_order_id)
        worker = get_object_or_404(GeneralWorker, id=worker_id)
        company_info = CompanyInfo.objects.filter(company=worker.company).first()
    except Http404:
        return render(request, 'error_page.html', status=404)

    user_agent_string = request.headers.get('User-Agent')
    device = DeviceDetector(user_agent_string).parse()
    context = {
        'work_order': work_order,
        'worker': worker,
        'company_info': company_info,
        'referer': referer,
        'device_type': device.device_type(),
        'work_order_id': work_order_id,
        'worker_id': worker_id,
    }

    return render(request, 'hanwool/general_work/general_work_contract.html', context)

def general_work_invoice_page(request, work_order_id=None):
    if not work_order_id:
        return HttpResponseForbidden("일일근무관리 문서가 누락되었습니다.")

    work_order = get_object_or_404(GeneralWorkOrder, id=work_order_id)
    worker = get_object_or_404(GeneralWorker, work_order_id=work_order_id)

    render_html = 'hanwool/general_work/general_work_invoice.html'
    # if work_order.customer.general_work_type == "물류직":
    #     render_html = 'hanwool/general_work/general_work_logi_invoice.html'

    context = {
        'work_order': work_order,
        'worker': worker,
    }

    return render(request, render_html, context)


def performance_page(request):
    current_year = date.today().year
    start_year = 2024
    end_year = current_year + 4
    year_range = range(start_year, end_year)

    context = {
        'year_range': year_range,
        'default_year': current_year,
    }
    return render(request, 'hanwool/customer/performance.html', context)

def human_performance_page(request):
    current_year = date.today().year
    start_year = 2024
    end_year = current_year + 4
    year_range = range(start_year, end_year)

    context = {
        'year_range': year_range,
        'default_year': current_year,
    }
    return render(request, 'hanwool/customer/human_performance.html', context)

def team_performance_page(request):
    current_year = date.today().year
    start_year = 2024
    end_year = current_year + 4
    year_range = range(start_year, end_year)

    context = {
        'year_range': year_range,
        'default_year': current_year,
    }
    return render(request, 'hanwool/customer/team_performance.html', context)


# 매출관리
def sales_monthly_list_page(request):
    current_year = date.today().year
    start_year = 2024
    end_year = current_year + 4
    year_range = range(start_year, end_year)

    context = {
        'year_range': year_range,
        'default_year': current_year,
    }
    return render(request, 'hanwool/sales/monthly_list.html', context)

def sales_monthly_claim_page(request, monthly_sales_id=None):
    monthly_sales = get_object_or_404(MonthlySales, id=monthly_sales_id)
    year, month = monthly_sales.year, monthly_sales.month
    start_date = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)

    context = {
        'monthly_sales': monthly_sales,
        "start_date": start_date,
        "end_date": end_date,
        "price_no_vat": (monthly_sales.total_price or 0) - (monthly_sales.vat or 0),
    }
    return render(request, 'hanwool/sales/monthly_claim.html', context)


def sales_monthly_daily_price_page(request, year=None, month=None, customer_id=None, monthly_sales_id=None):
    customer = get_object_or_404(FactoryCustomer, id=customer_id)
    monthly_sales = get_object_or_404(MonthlySales, id=monthly_sales_id)

    context = {
        'year': year,
        'month': month,
        'customer': customer,
        'monthly_sales': monthly_sales,
    }
    return render(request, 'hanwool/sales/daily_price.html', context)


def sales_monthly_general_price_page(request, year=None, month=None, customer_id=None, monthly_sales_id=None):
    customer = get_object_or_404(FactoryCustomer, id=customer_id)
    monthly_sales = get_object_or_404(MonthlySales, id=monthly_sales_id)

    work_order_date = date(int(year), int(month), 1)
    work_order = (
        GeneralWorkOrder.objects.filter(customer=customer, general_worker_salary_order__date=work_order_date,
                                        company=request.user.company).first()
    )

    render_html = 'hanwool/sales/general_price.html'
    # if work_order and work_order.customer and work_order.customer.general_work_type == "물류직":
    #     render_html = 'hanwool/sales/general_logi_price.html'

    context = {
        'year': year,
        'month': month,
        'customer': customer,
        'monthly_sales': monthly_sales,
        'work_order': work_order,
    }
    return render(request, render_html, context)


def sales_monthly_result_page(request):
    current_year = date.today().year
    start_year = 2024
    end_year = current_year + 4
    year_range = range(start_year, end_year)

    context = {
        'year_range': year_range,
        'default_year': current_year,
    }
    return render(request, 'hanwool/sales/monthly_result.html', context)

def sales_monthly_result_data_page(request):
    current_year = date.today().year
    start_year = 2024
    end_year = current_year + 4
    year_range = range(start_year, end_year)

    context = {
        'year_range': year_range,
        'default_year': current_year,
    }
    return render(request, 'hanwool/sales/monthly_result_data.html', context)


# 고정/변동비
def general_cost_list_page(request):
    return render(request, 'hanwool/cost/general_cost.html')

def general_cost_data_page(request):
    current_year = date.today().year
    start_year = 2024
    end_year = current_year + 4
    year_range = range(start_year, end_year)

    context = {
        'year_range': year_range,
        'default_year': current_year,
    }
    return render(request, 'hanwool/cost/general_cost_data.html', context)


# 근태/급여관리 : 소득신고자료
def salary_monthly_claim_page(request):
    current_year = date.today().year
    start_year = 2024
    end_year = current_year + 4
    year_range = range(start_year, end_year)

    context = {
        'year_range': year_range,
        'default_year': current_year,
    }
    return render(request, 'hanwool/salary/monthly_claim.html', context)


# 근태/급여관리 : 가불금관리
def salary_prepayment_page(request):
    return render(request, 'hanwool/salary/prepayment.html')

def salary_prepayment_data_page(request):
    current_year = date.today().year
    start_year = 2024
    end_year = current_year + 4
    year_range = range(start_year, end_year)

    context = {
        'year_range': year_range,
        'default_year': current_year,
    }
    return render(request, 'hanwool/salary/prepayment_data.html', context)


# 법인카드관리
def cost_company_card_page(request):
    return render(request, 'hanwool/cost/company_card.html')

def company_card_data_page(request):
    current_year = date.today().year
    start_year = 2024
    end_year = current_year + 4
    year_range = range(start_year, end_year)

    context = {
        'year_range': year_range,
        'default_year': current_year,
    }
    return render(request, 'hanwool/cost/company_card_data.html', context)


# 공고비용관리
def cost_recruit_page(request):
    return render(request, 'hanwool/cost/recruit.html')

def recruit_data_manager_page(request):
    current_year = date.today().year
    start_year = 2024
    end_year = current_year + 4
    year_range = range(start_year, end_year)

    context = {
        'year_range': year_range,
        'default_year': current_year,
    }
    return render(request, 'hanwool/cost/recruit_data.html', context)

def recruit_data_page(request):
    current_year = date.today().year
    start_year = 2024
    end_year = current_year + 4
    year_range = range(start_year, end_year)

    context = {
        'year_range': year_range,
        'default_year': current_year,
    }
    return render(request, 'hanwool/cost/recruit_data_site.html', context)


def kpi_customer_page(request):
    current_year = date.today().year
    start_year = 2024
    end_year = current_year + 4
    year_range = range(start_year, end_year)

    context = {
        'year_range': year_range,
        'default_year': current_year,
    }
    return render(request, 'hanwool/kpi/customer.html', context)


def kpi_subsidiary_page(request):
    current_year = date.today().year
    start_year = 2024
    end_year = current_year + 4
    year_range = range(start_year, end_year)

    context = {
        'year_range': year_range,
        'default_year': current_year,
    }
    return render(request, 'hanwool/kpi/subsidiary.html', context)


def kpi_center_page(request):
    current_year = date.today().year
    start_year = 2024
    end_year = current_year + 4
    year_range = range(start_year, end_year)

    context = {
        'year_range': year_range,
        'default_year': current_year,
    }
    return render(request, 'hanwool/kpi/center.html', context)


def daily_report_page(request):
    current_year = date.today().year
    start_year = 2024
    end_year = current_year + 4
    year_range = range(start_year, end_year)

    context = {
        'year_range': year_range,
        'default_year': current_year,
    }
    return render(request, 'hanwool/daily_work/daily_report.html', context)


# 시스템관리 : 전자계약/서명관리
def daily_contract_manage(request):
    return render(request, 'hanwool/admin/daily_contract.html')

def general_contract_manage(request):
    return render(request, 'hanwool/admin/general_contract.html')

def view_daily_contract_document(request):
    context = {
        'pdf_url': request.GET.get("pdf_url")
    }
    return render(request, 'hanwool/daily_work/view_daily_contract.html', context)


def view_general_contract_document(request):
    context = {
        'pdf_url': request.GET.get("pdf_url")
    }
    return render(request, 'hanwool/general_work/view_daily_contract.html', context)

