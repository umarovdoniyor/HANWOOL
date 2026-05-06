from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from django.db import transaction, DatabaseError
from django.db.models import Q, OuterRef, Subquery, Max, Count
from api.models import ProjectManage, EventMaster, UserMaster, TaskManage, CodeMaster
from datetime import datetime, date, time
from django.db.models import Min, Max, Sum
from django.views.decorators.http import require_GET
from django.utils.decorators import method_decorator
from django.utils.dateparse import parse_date
from api.lib import Pagenation, get_excep_msg
from django.utils import timezone


class Project_Read(View):
    def get(self, request, *args, **kwargs):
        user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')
        sch_cat1 = request.GET.get('sch_cat1', '')
        sch_status = request.GET.get('sch_status', '')
        sch_manager = request.GET.get('sch_manager', '')

        qs = ProjectManage.objects.filter(company=request.user.company).annotate(
            real_start_min=Min('prj__real_start'),
            real_end_max=Max('prj__real_end'),
            plan_time_sum=Sum('prj__plan_time'),
            real_time_sum=Sum('prj__real_time'),
        ).order_by('plan_start', '-id')

        # 사용여부 필터
        if sch_status == "진행":
            qs = qs.filter(status="진행")
        elif sch_status == "완료":
            qs = qs.filter(status="완료")
        elif sch_status == "중단":
            qs = qs.filter(status="중단")
        elif sch_status == "대기":
            qs = qs.filter(status="대기")

        # 기간 검색 (기간을 포함하는 방식)
        if fr_date and to_date:
            qs = qs.filter(
                Q(plan_start__lte=to_date) & Q(plan_end__gte=fr_date)
            )
        elif fr_date:
            qs = qs.filter(plan_end__gte=fr_date)
        elif to_date:
            qs = qs.filter(plan_start__lte=to_date)

        # 키워드 검색
        all_sch = request.GET.get("all_sch", '')
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_condition = (
                        Q(code__icontains=keyword) |
                        Q(title__icontains=keyword) |
                        Q(customer__icontains=keyword) |
                        Q(detail__icontains=keyword) |
                        Q(desc1__icontains=keyword) |
                        Q(desc2__icontains=keyword) |
                        Q(desc3__icontains=keyword) |
                        Q(cat2__name__icontains=keyword) |
                        Q(cat3__name__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        # 프로젝트 매니저 필터
        if sch_manager:
            qs = qs.filter(manager_id=sch_manager)

        if sch_cat1:
            qs = qs.filter(cat1=sch_cat1)

        if _page == '' or _size == '':
            results = [get_obj(row) for row in qs]
            context = {'results': results}
            return JsonResponse(context, safe=False)

        # Pagination
        qs_ps = Pagenation(qs, _size, _page)

        pre = int(_page) - 1
        url_pre = "/?page_size=" + _size + "&page=" + str(pre)
        if pre < 1:
            url_pre = None

        next = int(_page) + 1
        url_next = "/?page_size=" + _size + "&page=" + str(next)
        if next > qs_ps.paginator.num_pages:
            url_next = None

        results = [get_obj(row) for row in qs_ps]

        context = {
            'count': qs_ps.paginator.count,
            'previous': url_pre,
            'next': url_next,
            'results': results,
        }

        return JsonResponse(context, safe=False)


class Project_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            code = request.POST.get('code', '')
            title = request.POST.get('title', '')
            customer = request.POST.get('customer', '')
            plan_start = request.POST.get('plan_start', None) or None
            plan_end = request.POST.get('plan_end', None) or None
            progress = request.POST.get('progress', None) or 0
            status = request.POST.get('status', '')
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')
            desc3 = request.POST.get('desc3', '')
            detail = request.POST.get('detail', '')
            manager = request.POST.get('manager') or None
            cat1 = request.POST.get('cat1') or None
            cat2 = request.POST.get('cat2') or None
            cat3 = request.POST.get('cat3') or None

            manager = UserMaster.objects.filter(id=manager).first() if manager else None
            cat1 = CodeMaster.objects.filter(id=cat1).first() if cat1 else None
            cat2 = CodeMaster.objects.filter(id=cat2).first() if cat2 else None
            cat3 = CodeMaster.objects.filter(id=cat3).first() if cat3 else None

            if not code:
                code = generate_unique_project_code(request.user.company)

            obj = ProjectManage.objects.create(
                code=code,
                title=title,
                customer=customer,
                plan_start=plan_start,
                plan_end=plan_end,
                progress=progress,
                status=status,
                desc1=desc1,
                desc2=desc2,
                desc3=desc3,
                detail=detail,

                cat1=cat1 if cat1 else None,
                cat2=cat2 if cat2 else None,
                cat3=cat3 if cat3 else None,
                manager=manager if manager else None,

                created_by=request.user,
                updated_by=request.user,
                created_at=timezone.now().date(),
                updated_at=timezone.now().date(),
                company=request.user.company,
            )

            return JsonResponse({'result': 'ok', 'id': obj.id})

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class Project_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            pk = request.POST.get('pk', '')
            title = request.POST.get('title', '')
            customer = request.POST.get('customer', '')
            plan_start = request.POST.get('plan_start', None) or None
            plan_end = request.POST.get('plan_end', None) or None
            progress = request.POST.get('progress', None) or 0
            status = request.POST.get('status', '')
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')
            desc3 = request.POST.get('desc3', '')
            detail = request.POST.get('detail', '')
            manager = request.POST.get('manager') or None
            cat1 = request.POST.get('cat1') or None
            cat2 = request.POST.get('cat2') or None
            cat3 = request.POST.get('cat3') or None

            manager = UserMaster.objects.filter(id=manager).first() if manager else None
            cat1 = CodeMaster.objects.filter(id=cat1).first() if cat1 else None
            cat2 = CodeMaster.objects.filter(id=cat2).first() if cat2 else None
            cat3 = CodeMaster.objects.filter(id=cat3).first() if cat3 else None

            obj = get_object_or_404(ProjectManage, pk=int(pk))
            obj.title = title
            obj.customer = customer
            obj.plan_start = plan_start
            obj.plan_end = plan_end
            obj.progress = progress
            obj.status = status
            obj.desc1 = desc1
            obj.desc2 = desc2
            obj.desc3 = desc3
            obj.detail = detail

            obj.cat1 = cat1 if cat1 else None
            obj.cat2 = cat2 if cat2 else None
            obj.cat3 = cat3 if cat3 else None
            obj.manager = manager if manager else None

            obj.updated_at = timezone.now().date()
            obj.updated_by = request.user
            obj.save()

            return JsonResponse({'result': 'ok', 'id': obj.id})

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class Project_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(ProjectManage, pk=int(pk))
            obj.delete()

            context = {'success': True}
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


def get_obj(obj):
    member_qs = TaskManage.objects.filter(prj=obj).values_list('tasker', flat=True).distinct()
    members = [
        get_user_info(user) for user in UserMaster.objects.filter(id__in=member_qs)
    ]

    return {
        'id': obj.id,
        'title': obj.title or '',
        'code': obj.code or '',
        'customer': obj.customer or '',
        'detail': obj.detail or '',
        'desc1': obj.desc1 or '',
        'desc2': obj.desc2 or '',
        'desc3': obj.desc3 or '',
        'cat1_id': obj.cat1.id if obj.cat1 else '',
        'cat1_name': obj.cat1.name if obj.cat1 else '',
        'cat2_id': obj.cat2.id if obj.cat2 else '',
        'cat2_name': obj.cat2.name if obj.cat2 else '',
        'cat3_id': obj.cat3.id if obj.cat3 else '',
        'cat3_name': obj.cat3.name if obj.cat3 else '',
        'manager': get_user_info(obj.manager) if obj.manager else '',
        'members': members,
        'plan_start': obj.plan_start or '',
        'plan_end': obj.plan_end or '',
        'real_start': getattr(obj, 'real_start_min', ''),
        'real_end': getattr(obj, 'real_end_max', ''),
        'plan_time_sum': getattr(obj, 'plan_time_sum', ''),
        'real_time_sum': getattr(obj, 'real_time_sum', ''),
        'progress': obj.progress or '',
        'status': obj.status or '',
        'total_days': obj.total_days or '',
        'remaining_days': obj.remaining_days or '',
        'created_by': get_user_info(obj.created_by) if obj.created_by else '',
        'updated_by': get_user_info(obj.updated_by) if obj.updated_by else '',
        'created_at': obj.created_at.strftime('%Y-%m-%d') if obj.created_at else '',
        'updated_at': obj.updated_at.strftime('%Y-%m-%d') if obj.updated_at else '',
    }

def get_user_info(user):
    return {
        'id': user.id,
        'name': user.name,
        'profile_image': user.profile_image.url if user.profile_image and user.profile_image.name else '',
        'team': user.team.name if user.team else '',
        'job_level': user.job_level.name if user.job_level else '',
    }

def generate_unique_project_code(company):
    prefix = "PRJ-"
    order = "000001"

    latest = (
        ProjectManage.objects.filter(company=company, code__startswith=prefix)
        .order_by("-code")
        .first()
    )

    if latest and latest.code:
        try:
            num = latest.code.replace(prefix, "")
            if num.isdigit():
                order = str(int(num) + 1).zfill(6)
        except (ValueError, AttributeError):
            pass

    return prefix + order


class Company_Offday_Read(View):
    def get(self, request, *args, **kwargs):
        # 캘린더 이벤트에서 회사 휴무 리스트만 가져오기
        company_offday_category = CodeMaster.objects.filter(company=request.user.company, name="회사 휴무").last()
        if not company_offday_category:
            return None

        company_offday = set(
            EventMaster.objects.filter(company=request.user.company, category=company_offday_category)
            .order_by('start_date')
        )

        context = [
            {
                'id': company_offday.id,
                'name': company_offday.title,
                'start_date': company_offday.start_date,
                'end_date': company_offday.end_date,
            }
            for company_offday in company_offday
        ]

        return JsonResponse(context, safe=False)



@require_GET
def projects_by_users_fn(request):
    task_chart_sch_from = request.GET.get('task_chart_sch_from')
    date_from = parse_date(task_chart_sch_from) if task_chart_sch_from else None

    task_chart_sch_to = request.GET.get('task_chart_sch_to')
    date_to = parse_date(task_chart_sch_to) if task_chart_sch_to else None

    sch_department = request.GET.get('sch_department')
    sch_manager = request.GET.get('sch_manager')

    users = UserMaster.objects.filter(is_staff=True).exclude(etc="no_leave").order_by('department_position_id', 'orgchart_order')
    context = []

    for user in users:
        project_qs = ProjectManage.objects.filter(manager=user)
        task_qs = TaskManage.objects.filter(tasker=user)

        if sch_department:
            project_qs = project_qs.filter(manager__department_position_id=sch_department)
            task_qs = task_qs.filter(tasker__department_position_id=sch_department)

        if sch_manager:
            project_qs = project_qs.filter(manager_id=sch_manager)
            task_qs = task_qs.filter(tasker_id=sch_manager)

        if date_from and date_to:
            project_qs = project_qs.filter(plan_start__lte=date_to, plan_end__gte=date_from)
            task_qs = task_qs.filter(plan_start__lte=date_to, plan_end__gte=date_from)

        data = {
            'user': get_user_info(user),
            'project': {
                '대기': project_qs.filter(status='대기').count(),
                '진행': project_qs.filter(status='진행').count(),
                '완료': project_qs.filter(status='완료').count(),
                '중단': project_qs.filter(status='중단').count(),
                '전체': project_qs.count(),
            },
            'task': {
                '대기': task_qs.filter(status='대기').count(),
                '진행': task_qs.filter(status='진행').count(),
                '완료': task_qs.filter(status='완료').count(),
                '중단': task_qs.filter(status='중단').count(),
                '전체': task_qs.count(),
            }
        }
        context.append(data)

    return JsonResponse(context, safe=False)


def task_efficiency_data(request):
    time_eff_sch_from = request.GET.get('time_eff_sch_from')
    time_eff_sch_to = request.GET.get('time_eff_sch_to')
    sch_department = request.GET.get('sch_department')
    sch_manager = request.GET.get('sch_manager')

    qs = TaskManage.objects.filter(status="완료").exclude(plan_time__isnull=True).exclude(real_time__isnull=True)

    if sch_department:
        qs = qs.filter(tasker__department_position_id=sch_department)

    if sch_manager:
        qs = qs.filter(tasker_id=sch_manager)

    if time_eff_sch_from and time_eff_sch_to:
        qs = qs.filter(
            plan_start__gte=time_eff_sch_from,
            plan_start__lte=time_eff_sch_to
        )

    monthly_efficiency = [0 for _ in range(12)]  # 1월~12월
    monthly_counts = [0 for _ in range(12)]

    total_plan_time = 0
    total_real_time = 0

    for task in qs:
        if task.plan_time > 0 and task.plan_start:
            month_idx = task.plan_start.month - 1  # 0~11

            # 진짜 제대로된 초과/절감 계산
            efficiency = ((task.plan_time - task.real_time) / task.plan_time) * 100

            monthly_efficiency[month_idx] += efficiency
            monthly_counts[month_idx] += 1

            total_plan_time += task.plan_time
            total_real_time += task.real_time

    # 월별 평균
    monthly_average = []
    for total, count in zip(monthly_efficiency, monthly_counts):
        if count > 0:
            monthly_average.append(round(total / count, 1))
        else:
            monthly_average.append(0)

    # 전체 평균
    if total_plan_time > 0:
        overall_efficiency = ((total_plan_time - total_real_time) / total_plan_time) * 100
        overall_avg = round(overall_efficiency, 1)
    else:
        overall_avg = 0

    return JsonResponse({
        'average': overall_avg,
        'trend': monthly_average,
        'total_plan_time': round(total_plan_time, 1),
        'total_real_time': round(total_real_time, 1),
    })


@require_GET
def task_point_data(request):
    point_sch_from = request.GET.get('point_sch_from')
    point_sch_to = request.GET.get('point_sch_to')
    sch_department = request.GET.get('sch_department')
    sch_manager = request.GET.get('sch_manager')

    qs = TaskManage.objects.filter(status="완료").exclude(point__isnull=True)

    if sch_department:
        qs = qs.filter(tasker__department_position_id=sch_department)

    if sch_manager:
        qs = qs.filter(tasker_id=sch_manager)

    if point_sch_from and point_sch_to:
        qs = qs.filter(
            plan_start__gte=point_sch_from,
            plan_start__lte=point_sch_to
        )

    monthly_points = [0 for _ in range(12)]  # 1~12월
    monthly_counts = [0 for _ in range(12)]

    for task in qs:
        if task.plan_start:
            month_idx = task.plan_start.month - 1
            monthly_points[month_idx] += task.point
            monthly_counts[month_idx] += 1

    monthly_average = []
    for total, count in zip(monthly_points, monthly_counts):
        if count > 0:
            monthly_average.append(round(total / count, 1))
        else:
            monthly_average.append(0)

    all_values = [p for p in monthly_average if p > 0]
    overall_avg = round(sum(all_values) / len(all_values), 1) if all_values else 0

    return JsonResponse({
        'average': overall_avg,
        'trend': monthly_average
    })


@require_GET
def project_task_status_summary(request):
    data_sch_from = request.GET.get('data_sch_from')
    data_sch_to = request.GET.get('data_sch_to')
    sch_department = request.GET.get('sch_department')
    sch_manager = request.GET.get('sch_manager')

    project_qs = ProjectManage.objects.all()
    task_qs = TaskManage.objects.all()

    if sch_department:
        project_qs = project_qs.filter(manager__department_position_id=sch_department)
        task_qs = task_qs.filter(tasker__department_position_id=sch_department)

    if sch_manager:
        project_qs = project_qs.filter(manager_id=sch_manager)
        task_qs = task_qs.filter(tasker_id=sch_manager)

    if data_sch_from and data_sch_to:
        project_qs = project_qs.filter(plan_start__lte=data_sch_to, plan_end__gte=data_sch_from)
        task_qs = task_qs.filter(plan_start__lte=data_sch_to, plan_end__gte=data_sch_from)

    # 프로젝트 결과 생성
    project_status_counts = (project_qs.values('status').annotate(count=Count('id')))
    project_data = {'전체': project_qs.count()}
    for row in project_status_counts:
        project_data[row['status']] = row['count']

    # 태스크 결과 생성
    task_status_counts = (task_qs.values('status').annotate(count=Count('id')))
    task_data = {'전체': task_qs.count()}
    for row in task_status_counts:
        task_data[row['status']] = row['count']

    return JsonResponse({
        'project': project_data,
        'task': task_data,
    })