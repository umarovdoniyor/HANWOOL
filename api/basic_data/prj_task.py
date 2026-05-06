from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from django.db import transaction, DatabaseError
from django.db.models import Q, OuterRef, Subquery, Max, F
from api.models import ProjectManage, UserMaster, TaskManage, CodeMaster
from datetime import datetime, date, time, timedelta
from api.lib import Pagenation, get_excep_msg
from django.utils import timezone


class Task_Read(View):
    def get(self, request, *args, **kwargs):
        user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')
        sch_status = request.GET.get('sch_status', '')
        sch_tasker = request.GET.get('sch_tasker', '')
        sch_team = request.GET.get('sch_team', '')
        prj_id = request.GET.get('prj_id', '')

        if prj_id == "all":
            qs = TaskManage.objects.filter(company=request.user.company).order_by('prj', 'plan_start', 'plan_end', '-id')
        else:
            qs = TaskManage.objects.filter(company=request.user.company, prj_id=prj_id).order_by('plan_start', 'plan_end', '-id')

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
                        Q(detail__icontains=keyword) |
                        Q(tasker_comment__icontains=keyword) |
                        Q(planner_comment__icontains=keyword) |
                        Q(planner__name__icontains=keyword) |
                        Q(cat1__name__icontains=keyword) |
                        Q(cat2__name__icontains=keyword) |
                        Q(cat3__name__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        # 업무담당자 필터
        if sch_tasker:
            qs = qs.filter(tasker_id=sch_tasker)

        # sch_team 필터
        if sch_team:
            qs = qs.filter(tasker__team_id=sch_team)

        # sch_mytask 필터
        sch_mytask = request.GET.get("sch_mytask", "").strip()
        if sch_mytask == "true":
            qs = qs.filter(tasker=request.user)

        # sort_tasker 정렬
        sort_tasker = request.GET.get("sort_tasker", "").strip()
        if sort_tasker == "true":
            qs = qs.order_by('tasker', 'prj', 'plan_start', 'plan_end', '-id')

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


class Task_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            prj_id = request.POST.get('prj_id', '')  # prj_id 연결
            code = request.POST.get('code', '')
            title = request.POST.get('title', '')
            tasker_comment = request.POST.get('tasker_comment', '')
            planner_comment = request.POST.get('planner_comment', '')
            plan_start = request.POST.get('plan_start', None) or None
            plan_end = request.POST.get('plan_end', None) or None
            real_start = request.POST.get('real_start', None) or None
            real_end = request.POST.get('real_end', None) or None
            progress = request.POST.get('progress', None) or 0
            status = request.POST.get('status', '')
            detail = request.POST.get('detail', '')
            plan_time = request.POST.get('plan_time', None) or 0
            real_time = request.POST.get('real_time', None) or 0
            tasker = request.POST.get('tasker') or None
            planner = request.POST.get('planner') or None
            cat1 = request.POST.get('cat1') or None
            cat2 = request.POST.get('cat2') or None
            cat3 = request.POST.get('cat3') or None

            tasker = UserMaster.objects.filter(id=tasker).first() if tasker else None
            planner = UserMaster.objects.filter(id=planner).first() if planner else None
            cat1 = CodeMaster.objects.filter(id=cat1).first() if cat1 else None
            cat2 = CodeMaster.objects.filter(id=cat2).first() if cat2 else None
            cat3 = CodeMaster.objects.filter(id=cat3).first() if cat3 else None

            if not code:
                code = generate_unique_task_code(request.user.company)

            obj = TaskManage.objects.create(
                prj_id=prj_id,
                code=code,
                title=title,
                detail=detail,
                tasker_comment=tasker_comment,
                planner_comment=planner_comment,

                plan_start=plan_start,
                plan_end=plan_end,
                real_start=real_start,
                real_end=real_end,
                plan_time=plan_time,
                real_time=real_time,
                progress=progress,
                status=status,

                cat1=cat1 if cat1 else None,
                cat2=cat2 if cat2 else None,
                cat3=cat3 if cat3 else None,
                tasker=tasker if tasker else None,
                planner=planner if planner else None,

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


class Task_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            pk = request.POST.get('pk', '')
            title = request.POST.get('title', '')
            tasker_comment = request.POST.get('tasker_comment', '')
            planner_comment = request.POST.get('planner_comment', '')
            plan_start = request.POST.get('plan_start', None) or None
            plan_end = request.POST.get('plan_end', None) or None
            real_start = request.POST.get('real_start', None) or None
            real_end = request.POST.get('real_end', None) or None
            progress = request.POST.get('progress', None) or 0
            status = request.POST.get('status', '')
            detail = request.POST.get('detail', '')
            plan_time = request.POST.get('plan_time', None) or 0
            real_time = request.POST.get('real_time', None) or 0
            tasker = request.POST.get('tasker') or None
            planner = request.POST.get('planner') or None
            cat1 = request.POST.get('cat1') or None
            cat2 = request.POST.get('cat2') or None
            cat3 = request.POST.get('cat3') or None

            tasker = UserMaster.objects.filter(id=tasker).first() if tasker else None
            planner = UserMaster.objects.filter(id=planner).first() if planner else None
            cat1 = CodeMaster.objects.filter(id=cat1).first() if cat1 else None
            cat2 = CodeMaster.objects.filter(id=cat2).first() if cat2 else None
            cat3 = CodeMaster.objects.filter(id=cat3).first() if cat3 else None

            obj = get_object_or_404(TaskManage, pk=int(pk))
            obj.title = title
            obj.detail = detail
            obj.tasker_comment = tasker_comment
            obj.planner_comment = planner_comment

            obj.plan_start = plan_start
            obj.plan_end = plan_end
            obj.real_start = real_start
            obj.real_end = real_end
            obj.plan_time = plan_time
            obj.real_time = real_time
            obj.progress = progress
            obj.status = status

            obj.cat1 = cat1 if cat1 else None
            obj.cat2 = cat2 if cat2 else None
            obj.cat3 = cat3 if cat3 else None
            obj.tasker = tasker if tasker else None
            obj.planner = planner if planner else None

            obj.updated_at = timezone.now().date()
            obj.updated_by = request.user
            obj.save()

            return JsonResponse({'result': 'ok', 'id': obj.id})

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class Task_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(TaskManage, pk=int(pk))
            obj.delete()

            context = {'success': True}
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


def get_obj(obj):
    project = ProjectManage.objects.filter(id=obj.prj_id).first()

    return {
        'id': obj.id,
        'prj_id': obj.prj.id if obj.prj else '',
        'code': obj.code or '',
        'title': obj.title or '',
        'detail': obj.detail or '',
        'tasker_comment': obj.tasker_comment or '',
        'planner_comment': obj.planner_comment or '',
        'cat1_id': obj.cat1.id if obj.cat1 else '',
        'cat1_name': obj.cat1.name if obj.cat1 else '',
        'cat2_id': obj.cat2.id if obj.cat2 else '',
        'cat2_name': obj.cat2.name if obj.cat2 else '',
        'cat3_id': obj.cat3.id if obj.cat3 else '',
        'cat3_name': obj.cat3.name if obj.cat3 else '',
        'tasker': get_user_info(obj.tasker) if obj.tasker else '',
        'planner': get_user_info(obj.planner) if obj.planner else '',
        'plan_start': obj.plan_start.strftime('%Y-%m-%d') if obj.plan_start else '',
        'plan_end': obj.plan_end.strftime('%Y-%m-%d') if obj.plan_end else '',
        'real_start': obj.real_start.strftime('%Y-%m-%d') if obj.real_start else '',
        'real_end': obj.real_end.strftime('%Y-%m-%d') if obj.real_end else '',
        'plan_time': str(obj.plan_time) if obj.plan_time else '',
        'real_time': str(obj.real_time) if obj.real_time else '',
        'progress': obj.progress or '',
        'status': obj.status or '',
        'total_days': obj.total_days or '',
        'remaining_days': obj.remaining_days or '',
        'project': {
            'id': project.id,
            'title': project.title,
        } if project else '',

        'created_by': get_user_info(obj.created_by) if obj.created_by else '',
        'updated_by': get_user_info(obj.updated_by) if obj.updated_by else '',
        'created_at': obj.created_at.strftime('%Y-%m-%d') if obj.created_at else '',
        'updated_at': obj.updated_at.strftime('%Y-%m-%d') if obj.updated_at else '',
    }

def get_user_info(user):
    if not user:
        return {}

    return {
        'id': getattr(user, 'id', ''),
        'name': getattr(user, 'name', ''),
        'profile_image': user.profile_image.url if getattr(user, 'profile_image', None) else '',
        'team': getattr(getattr(user, 'team', None), 'name', ''),
        'job_level': getattr(getattr(user, 'job_level', None), 'name', ''),
    }

def generate_unique_task_code(company):
    prefix = "TASK-"
    order = "00000001"

    latest = (
        TaskManage.objects.filter(company=company, code__startswith=prefix)
        .order_by("-code")
        .first()
    )

    if latest and latest.code:
        try:
            num = latest.code.replace(prefix, "")
            if num.isdigit():
                order = str(int(num) + 1).zfill(8)
        except (ValueError, AttributeError):
            pass

    return prefix + order


def time_str_to_float(time_str):
    if not time_str or ':' not in time_str:
        return None
    try:
        hours, minutes = map(int, time_str.strip().split(':'))
        return round(hours + minutes / 60, 2)  # 소수 둘째 자리까지
    except:
        return None


class Task_Date_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        pk = request.POST.get('pk', '')  # 수정하려는 Task
        if not pk:
            return JsonResponse({'error': True, 'message': "수정할 항목이 지정되지 않았습니다."})

        change_type = request.POST.get('change_type', '')
        plan_start = request.POST.get('plan_start', None) or None
        plan_end = request.POST.get('plan_end', None) or None
        real_start = request.POST.get('real_start', None) or None
        real_end = request.POST.get('real_end', None) or None

        d_today = datetime.today().strftime('%Y-%m-%d')  # 오늘날짜

        try:
            with transaction.atomic():
                obj = TaskManage.objects.get(id=int(pk))

                if change_type == "plan_date":
                    obj.plan_start = plan_start
                    obj.plan_end = plan_end
                else:
                    obj.real_start = real_start
                    obj.real_end = real_end

                obj.updated_at = d_today
                obj.updated_by = request.user
                obj.save()

                return JsonResponse({'result': 'ok', 'id': obj.id})

        except Exception as e:
            transaction.set_rollback(True)
            msg = f"An unexpected error occurred: {str(e)}"
            return JsonResponse({'error': True, 'message': msg})


# 사용자 간트
class User_Gantt_Read(View):
    def get(self, request, *args, **kwargs):
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')
        sch_tasker = request.GET.get('sch_tasker', '')
        sch_team = request.GET.get('sch_team', '')
        all_sch = request.GET.get("all_sch", '')

        users_qs = (UserMaster.objects.filter(company=request.user.company, is_staff=1, is_delete=0, is_superuser=0)
                 .order_by('team_id', F('seq_order').asc(nulls_last=True), 'join_date'))

        task_qs = TaskManage.objects.select_related('tasker', 'prj', 'cat1', 'cat2', 'cat3').order_by('real_start')

        # 기간 검색 (기간을 포함하는 방식)
        if fr_date and to_date:
            task_qs = task_qs.filter(
                Q(real_start__lte=to_date) & Q(real_end__gte=fr_date)
            )
        elif fr_date:
            task_qs = task_qs.filter(real_end__gte=fr_date)
        elif to_date:
            task_qs = task_qs.filter(real_start__lte=to_date)

        # 부서 검색
        if sch_team:
            users_qs = users_qs.filter(team_id=sch_team)

        # 담당자 검색
        if sch_tasker:
            users_qs = users_qs.filter(id=sch_tasker)

        # 키워드 검색
        if all_sch:
            for keyword in all_sch.split(','):
                keyword = keyword.strip()
                task_qs = task_qs.filter(
                    Q(code__icontains=keyword) |
                    Q(title__icontains=keyword) |
                    Q(detail__icontains=keyword) |
                    Q(prj__code__icontains=keyword) |
                    Q(prj__title__icontains=keyword)
                )

        task_map = {}
        for task in task_qs:
            if task.tasker_id not in task_map:
                task_map[task.tasker_id] = []

            task_map[task.tasker_id].append({
                'id': task.id,
                'title': task.title,
                'code': task.code,
                'detail': task.detail or '',
                'tasker_comment': task.tasker_comment or '',
                'planner_comment': task.planner_comment or '',
                'status': task.status,
                'progress': task.progress,
                'plan_start': task.plan_start.strftime('%Y-%m-%d') if task.plan_start else '',
                'plan_end': task.plan_end.strftime('%Y-%m-%d') if task.plan_end else '',
                'real_start': task.real_start.strftime('%Y-%m-%d') if task.real_start else '',
                'real_end': task.real_end.strftime('%Y-%m-%d') if task.real_end else '',
                'plan_time': str(task.plan_time or ''),
                'real_time': str(task.real_time or ''),
                'cat1_id': task.cat1.id if task.cat1 else '',
                'cat1_name': task.cat1.name if task.cat1 else '',
                'cat2_id': task.cat2.id if task.cat2 else '',
                'cat2_name': task.cat2.name if task.cat2 else '',
                'cat3_id': task.cat3.id if task.cat3 else '',
                'cat3_name': task.cat3.name if task.cat3 else '',
                'project': {
                    'id': task.prj.id if task.prj else '',
                    'title': task.prj.title if task.prj else ''
                },
                'tasker': {
                    'id': task.tasker.id,
                    'name': task.tasker.name,
                    'profile_image': task.tasker.profile_image.url if task.tasker.profile_image else '',
                    'team': task.tasker.team.name if task.tasker.team else '',
                    'job_level': task.tasker.job_level.name if task.tasker.job_level else ''
                } if task.tasker else {},
                'planner': {
                    'id': task.planner.id,
                    'name': task.planner.name,
                    'profile_image': task.planner.profile_image.url if task.planner.profile_image else '',
                    'team': task.planner.team.name if task.planner.team else '',
                    'job_level': task.planner.job_level.name if task.planner.job_level else ''
                } if task.planner else {},
            })

        users_qs_ps = Pagenation(users_qs, _size, _page)

        pre = int(_page) - 1
        url_pre = f"/?page_size={_size}&page={pre}" if pre > 0 else None
        next = int(_page) + 1
        url_next = f"/?page_size={_size}&page={next}" if next <= users_qs_ps.paginator.num_pages else None

        results = []
        for user in users_qs_ps:
            results.append({
                'id': user.id,
                'name': user.name,
                'team': user.team.name if user.team else '',
                'job_level': user.job_level.name if user.job_level else '',
                'profile_image': user.profile_image.url if user.profile_image else '',
                'tasks': task_map.get(user.id, [])
            })

        return JsonResponse({
            'count': users_qs_ps.paginator.count,
            'previous': url_pre,
            'next': url_next,
            'results': results
        }, safe=False)