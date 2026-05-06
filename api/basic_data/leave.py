from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q
from api.models import UserMaster,EventMaster, CodeMaster
from api.lib import Pagenation, get_excep_msg
from datetime import datetime, date, time
from django.db.models import Sum
from django.db.models.functions import ExtractYear, ExtractMonth
from decimal import Decimal
from django.utils import timezone
from api.basic_data.notification import noti_create_fn


class LeaveManage_List(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')
        user_gantt = request.GET.get('user_gantt', '')

        # 캘린더 이벤트에서 휴가 리스트만 가져오기
        leave_category = CodeMaster.objects.filter(company=request_user.company, name="휴가").last()
        qs = (
            EventMaster.objects.filter(company=request_user.company, category=leave_category)
            .select_related(
                'category',
                'approval',
                'created_by',
                'created_by__team',
                'created_by__job_level',
            )
            .order_by('-start_date')
        )

        # 일반 사용자는 자신의 기록만 볼 수 있음
        if request_user.is_authenticated:
            if not (request_user.is_master or request_user.is_superuser):
                qs = qs.filter(created_by=request_user)

        else:
            qs = qs.none()

        if user_gantt == 'true':
            qs = (
                EventMaster.objects.filter(company=request_user.company, category=leave_category)
                .select_related(
                    'category',
                    'approval',
                    'created_by',
                    'created_by__team',
                    'created_by__job_level',
                )
                .order_by('-start_date')
            )

        # 기간 검색
        if fr_date:
            if isinstance(fr_date, str):
                fr_date = datetime.strptime(fr_date, "%Y-%m-%d").date()
                fr_date = datetime.combine(fr_date, time(0, 0, 0))  # 00:00:00 설정
                qs = qs.filter(start_date__gte=fr_date)

        if to_date:
            if isinstance(to_date, str):
                to_date = datetime.strptime(to_date, "%Y-%m-%d").date()
                to_date = datetime.combine(to_date, time(23, 59, 59))  # 23:59:59 설정
                qs = qs.filter(start_date__lte=to_date)

        # 키워드 검색
        all_sch = request.GET.get("all_sch", '')
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_condition = (
                        Q(title__icontains=keyword) |
                        Q(desc__icontains=keyword) |
                        Q(change_type__icontains=keyword) |
                        Q(created_by__name__icontains=keyword) |
                        Q(created_by__team__name__icontains=keyword) |
                        Q(approval__status__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

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


class LeaveManage_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            change_type = request.POST.get('change_type', '')
            change_user = request.POST.get('change_user', '')
            annual_leave_days = request.POST.get('annual_leave_days', '')
            change_reason = request.POST.get('change_reason', '')

            start_date = request.POST.get('start_date', None)
            if start_date:
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
            else:
                start_date = None

            change_user = UserMaster.objects.filter(id=change_user).first()
            leave_category = CodeMaster.objects.filter(company=change_user.company, name="휴가").last()

            obj = EventMaster.objects.create(
                start_date=start_date,
                end_date=start_date,
                change_reason=change_reason,
                annual_leave_days=annual_leave_days,
                change_type=change_type,
                category=leave_category,

                created_by=change_user,
                updated_by=change_user,
                created_at=timezone.now(),
                updated_at=timezone.now(),
                company=change_user.company,
            )

            # 알림센터 메세지 전송
            if change_type == "연차 추가":
                noti_create_fn(
                    content=f"[{obj.start_date.date()} {obj.change_type}] {obj.change_reason}",
                    user=obj.created_by,
                    url=f"/leave/manage",
                    noti_type="leave_create"
                )

            elif change_type == "연차 삭감":
                noti_create_fn(
                    content=f"[{obj.start_date.date()} {obj.change_type}] {obj.change_reason}",
                    user=obj.created_by,
                    url=f"/leave/manage",
                    noti_type="leave_delete"
                )

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class LeaveManage_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            pk = request.POST.get('pk')
            annual_leave_days = request.POST.get('annual_leave_days', '')
            change_reason = request.POST.get('change_reason', '')

            obj = get_object_or_404(EventMaster, pk=int(pk))
            obj.annual_leave_days = annual_leave_days
            obj.change_reason = change_reason
            obj.updated_at = timezone.now()
            obj.save()

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class LeaveManage_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = EventMaster.objects.get(pk=int(pk))
            obj.delete()

            context = {'success': True}
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


def get_obj(obj):
    return {
        'id': obj.id,
        'title': obj.title if obj.title is not None else '',
        'start_date': obj.start_date.date() if obj.start_date is not None else '',
        'start_datetime': obj.start_date.strftime('%Y-%m-%d %H:%M') if obj.start_date is not None else '',
        'end_date': obj.end_date.date() if obj.end_date is not None else '',
        'end_datetime': obj.end_date.strftime('%Y-%m-%d %H:%M') if obj.end_date is not None else '',
        'annual_leave_days': obj.annual_leave_days if obj.annual_leave_days is not None else '',
        'desc': obj.desc if obj.desc is not None else '',
        'category': obj.category.name if obj.category is not None else '',
        'change_reason': obj.change_reason if obj.change_reason else '',
        'change_type': obj.change_type if obj.change_type else '',
        'approval': obj.approval.id if obj.approval is not None else '',
        'apv_status': obj.approval.status if obj.approval is not None else '',
        'apv_category_id': obj.approval.category if obj.approval is not None else '',
        'created_by': {
            'id': obj.created_by.id,
            'name': obj.created_by.name,
            'profile_image': obj.created_by.profile_image.url if obj.created_by.profile_image else '',
            'team': obj.created_by.team.name if obj.created_by.team else '',
            'job_level': obj.created_by.job_level.name if obj.created_by.job_level else '',
        } if obj.created_by else '',
        'created_at': obj.created_at.date() if obj.created_at is not None else '',
        'updated_at': obj.updated_at.date() if obj.updated_at is not None else '',
    }


# 연차통계 부분
class LeaveReport_List(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        year_sch = request.GET.get('year_sch', '')
        try:
            year_sch = int(year_sch)
        except (ValueError, TypeError):
            return JsonResponse({'error': '기준연도에 오류가 있습니다.'}, status=400)

        start_date = date(1, 1, 1)  # 모든 데이터를 가져오기 위해 시작 날짜를 초기화
        end_date = date(year_sch + 1, 12, 31)  # 다음 년도까지 데이터 가져오기

        # 캘린더 이벤트에서 휴가 리스트만 가져오기
        leave_category = CodeMaster.objects.filter(company=request_user.company, name="휴가").last()
        qs = EventMaster.objects.filter(
            company=request_user.company,
            category=leave_category,
            start_date__gte=start_date,
            end_date__lte=end_date
        )

        # 모든 사용자 가져오기
        all_users = (
            UserMaster.objects
            .filter(work_type="관리직", company=request_user.company, is_staff=True)
            .select_related('team', 'job_level')
            .order_by('join_date')
        )

        # 사용자의 권한에 따라 필터링 (일반사용자는 본인것만 보기)
        if request_user.is_authenticated:
            if not request_user.is_master:
                all_users = all_users.filter(id=request_user.id)
        else:
            qs = qs.none()

        # 키워드 검색
        all_sch = request.GET.get("all_sch", '')
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_condition = (
                        Q(name__icontains=keyword) |
                        Q(team__name__icontains=keyword) |
                        Q(job_level__name__icontains=keyword)
                    )
                    search_conditions |= search_condition
            all_users = all_users.filter(search_conditions)

        # 사용자 정보와 이벤트 데이터 필터
        user_ids = [user.id for user in all_users]
        qs = qs.filter(created_by__id__in=user_ids)

        # 모든 이전 데이터 leave_balance 계산
        previous_summary = (
            qs.filter(start_date__lt=date(year_sch, 1, 1))
            .values('created_by', 'change_type')
            .annotate(total_leave_count=Sum('annual_leave_days'))
        )

        user_initial_balances = {user.id: 0 for user in all_users}
        for row in previous_summary:
            created_by_id = row['created_by']
            if row['change_type'] == '연차 추가':
                user_initial_balances[created_by_id] += row['total_leave_count'] or 0
            else:
                user_initial_balances[created_by_id] -= row['total_leave_count'] or 0

        # leave_balance 계산 (현재 연도)
        summary = (
            qs.filter(start_date__year=year_sch)
            .annotate(
                year=ExtractYear('start_date'),
                month=ExtractMonth('start_date')
            )
            .values('year', 'month', 'created_by', 'change_type')
            .annotate(total_leave_count=Sum('annual_leave_days'))
            .order_by('created_by', 'year', 'month')
        )

        results = {user.id: {} for user in all_users}
        user_join_dates = {user.id: user.join_date for user in all_users}
        user_name = {user.id: user.name for user in all_users}
        team = {user.id: user.team.name if user.team else None for user in all_users}
        job_level = {user.id: user.job_level.name if user.job_level else None for user in all_users}
        profile_image = {user.id: user.profile_image.url for user in all_users}

        for row in summary:
            created_by_id = row['created_by']
            year = row['year']
            month = row['month']
            total_period = row['total_leave_count'] or 0

            if (year, month) not in results[created_by_id]:
                results[created_by_id][(year, month)] = 0
            if row['change_type'] == '연차 추가':
                results[created_by_id][(year, month)] += total_period
            else:
                results[created_by_id][(year, month)] -= total_period

        # 결과 데이터 포맷팅
        formatted_results = []
        next_year_initial_balances = {}

        for created_by_id, monthly_data in results.items():
            balance = Decimal(user_initial_balances.get(created_by_id, 0))
            initial_balance = balance  # 초기 값 저장
            details = []

            for month in range(1, 13):
                total_period = monthly_data.get((year_sch, month), 0)

                # 초기 잔여 휴가 포함하여 계산
                balance += Decimal(total_period)

                details.append({
                    'year': year_sch,
                    'month': month,
                    'total_leave_count': (f"+{total_period:.1f}" if total_period > 0 else (
                        f"{total_period:.1f}" if total_period != 0 else '0.0')) if total_period != 0 or (year_sch, month) in monthly_data else '',
                    'leave_balance': f"{balance:.1f}",
                    'no_data': total_period == 0 and (year_sch, month) not in monthly_data
                })

            # 현재 연도 잔여값을 내년 초기 값으로 저장
            next_year_initial_balances[created_by_id] = balance
            today = datetime.today().date()

            formatted_results.append({
                'created_by': created_by_id,
                'user_name': user_name.get(created_by_id, 'Unknown'),
                'team': team.get(created_by_id, 'Unknown'),
                'job_level': job_level.get(created_by_id, 'Unknown'),
                'profile_image': profile_image.get(created_by_id, 'Unknown'),
                'join_date': user_join_dates.get(created_by_id),
                'working_years': (today - user_join_dates.get(created_by_id)).days // 365,
                'details': details,
                'leave_balance': f"{balance:.1f}",
                'initial_balance': f"{initial_balance:.1f}"
            })

        # 내년 데이터 처리 시 이월 값 초기화
        for created_by, balance in next_year_initial_balances.items():
            # 잔여값이 None인 경우 기본값 설정
            user_initial_balances = {
                user: next_year_initial_balances.get(user, Decimal(0))
                for user in user_initial_balances
            }

        # Pagination
        qs_ps = Pagenation(formatted_results, _size, _page)

        pre = int(_page) - 1
        url_pre = "/?page_size=" + _size + "&page=" + str(pre)
        if pre < 1:
            url_pre = None

        next = int(_page) + 1
        url_next = "/?page_size=" + _size + "&page=" + str(next)
        if next > qs_ps.paginator.num_pages:
            url_next = None

        results = [row for row in qs_ps]

        context = {
            'count': qs_ps.paginator.count,
            'previous': url_pre,
            'next': url_next,
            'results': results,
        }

        return JsonResponse(context, safe=False)
