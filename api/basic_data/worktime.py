from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from django.db import transaction, DatabaseError
from django.db.models import Q, OuterRef, Subquery, Max
from api.models import UserMaster, WorktimeMaster, CodeGroup, CodeMaster, EventMaster
from api.lib import Pagenation, get_excep_msg
from datetime import datetime, date, time, timedelta
import requests
import re
from django.db.models import F
from django.forms.models import model_to_dict
from collections import defaultdict
import calendar
from api.basic_data.notification import noti_create_fn


class Worktime_List(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')
        sch_team = request.GET.get('sch_team', '')

        qs = WorktimeMaster.objects.filter(company=request_user.company).order_by('-work_date', '-check_in')
        if not request_user.is_master:
            if request_user.team:
                qs = qs.select_related('created_by__team').filter(created_by__team=request_user.team)
            else:
                qs = qs.filter(created_by=request_user)

        # 부서 검색
        if sch_team:
            qs = qs.select_related('created_by__team').filter(created_by__team=sch_team)

        # 기간 검색
        if fr_date:
            if isinstance(fr_date, str):
                fr_date = datetime.strptime(fr_date, "%Y-%m-%d").date()
                fr_date = datetime.combine(fr_date, time(0, 0, 0))  # 00:00:00 설정
                qs = qs.filter(work_date__gte=fr_date)

        if to_date:
            if isinstance(to_date, str):
                to_date = datetime.strptime(to_date, "%Y-%m-%d").date()
                to_date = datetime.combine(to_date, time(23, 59, 59))  # 23:59:59 설정
                qs = qs.filter(work_date__lte=to_date)

        # 키워드 검색
        all_sch = request.GET.get("all_sch", '')
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_condition = (
                        Q(created_by__name__icontains=keyword) |
                        Q(check_in_ip__icontains=keyword) |
                        Q(check_out_ip__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        late_time_filter = request.GET.get("late_time_filter", "").strip()
        if late_time_filter == "true":
            qs = qs.filter(late_time__isnull=False).exclude(late_time__exact="00:00:00")

        early_time_filter = request.GET.get("early_time_filter", "").strip()
        if early_time_filter == "true":
            qs = qs.filter(early_time__isnull=False).exclude(early_time__exact="00:00:00")

        if _page == '' or _size == '':
            results = [get_obj(row, request) for row in qs]
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

        results = [get_obj(row, request) for row in qs_ps]

        context = {
            'count': qs_ps.paginator.count,
            'previous': url_pre,
            'next': url_next,
            'results': results,
        }

        return JsonResponse(context, safe=False)


class Worktime_Create(View):
    @transaction.atomic
    def post(self, request):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        company_check_in = request_user.company.company_info.first().check_in
        d_today = date.today()

        # 이미 출근 기록이 있는 경우 중복 등록 방지
        if WorktimeMaster.objects.filter(
            created_by=request_user, work_date=d_today
        ).exists():
            return JsonResponse({'error': True, 'message': '이미 출근기록이 있습니다.'})

        try:
            check_in_time = datetime.now().time()
            now_dt = datetime.combine(d_today, check_in_time)
            company_dt = datetime.combine(d_today, company_check_in)
            late_time = (now_dt - company_dt) if now_dt > company_dt else timedelta()
            late_time_time = (datetime.min + late_time).time()
            if late_time_time == time(0, 0, 0):
                late_time_time = None
            check_in_ip = get_external_ip(request)

            WorktimeMaster.objects.create(
                company=request_user.company,
                created_by=request_user,
                updated_by=request_user,
                work_date=d_today,
                late_time=late_time_time,
                check_in=check_in_time,
                check_in_ip=check_in_ip,
                is_checkout=False,
            )
        except Exception as e:
            print('출근 등록 오류:', e)
            return JsonResponse({'error': True, 'message': '출근 등록 중 오류가 발생했습니다.'})

        return JsonResponse({'error': False, 'message': '출근이 등록되었습니다.'})


class Worktime_Update(View):
    @transaction.atomic
    def post(self, request):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        today = date.today()

        try:
            obj = WorktimeMaster.objects.filter(
                created_by=request_user, work_date=today
            ).last()

            if not obj:
                return JsonResponse({'error': True, 'message': '오늘 등록한 출근 기록이 없습니다.'})

            if obj.is_checkout:
                return JsonResponse({'error': True, 'message': '이미 퇴근이 처리되었습니다.'})

            now = datetime.now()
            check_out_time = now.time()
            check_out_dt = now
            check_out_ip = get_external_ip(request)

            # 실제 출근 시간
            check_in_dt = datetime.combine(today, obj.check_in)
            work_duration = check_out_dt - check_in_dt  # timedelta

            # 실제 근무시간이 5시간 이상인 경우, 점심시간 1시간 차감
            if work_duration.total_seconds() >= 5 * 3600:
                work_duration -= timedelta(hours=1)

            # 조기퇴근 시간 계산 (정규 근무시간 8시간 기준)
            early_duration = timedelta(hours=8) - work_duration
            if early_duration.total_seconds() < 0:
                early_time_value = None
            else:
                early_seconds = int(early_duration.total_seconds())
                early_hours, early_remainder = divmod(early_seconds, 3600)
                early_minutes = early_remainder // 60
                early_time_value = time(early_hours, early_minutes)

            # 근무 시간 계산
            total_seconds = int(work_duration.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes = remainder // 60
            work_time_value = time(hours, minutes)

            obj.check_out = check_out_time
            obj.check_out_ip = check_out_ip
            obj.work_time = work_time_value
            obj.early_time = early_time_value
            obj.is_checkout = True
            obj.updated_by = request_user
            obj.save()

        except WorktimeMaster.DoesNotExist:
            return JsonResponse({'error': True, 'message': '출근 기록이 없습니다.'})
        except Exception as e:
            print('퇴근 등록 오류:', e)
            return JsonResponse({'error': True, 'message': '퇴근 등록 중 오류가 발생했습니다.'})

        return JsonResponse({'error': False, 'message': '퇴근이 등록되었습니다.'})


class Worktime_Admin(View):
    @transaction.atomic
    def post(self, request):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')
            check_out_time_str = request.POST.get('check_out_time', '')
            check_out_type = request.POST.get('check_out_type', '')

            obj = get_object_or_404(WorktimeMaster, id=int(pk))

            if not obj:
                return JsonResponse({'error': True, 'message': '데이터베이스에서 선택 항목을 찾을 수 없습니다.'})

            if check_out_type == "checkout_byadmin":
                if check_out_time_str:
                    check_out_time = datetime.strptime(check_out_time_str, "%H:%M").time()
                else:
                    return JsonResponse({"error": "퇴근 시간이 비어 있습니다."}, status=400)
                ip = "관리자 퇴근처리"
                is_checkout = True

                check_out_dt = datetime.combine(obj.work_date, check_out_time)
                check_in_dt = datetime.combine(obj.work_date, obj.check_in)
                work_duration = check_out_dt - check_in_dt

                # 실제 근무시간이 5시간 이상인 경우, 점심시간 1시간 차감
                if work_duration.total_seconds() >= 5 * 3600:
                    work_duration -= timedelta(hours=1)

                # 조기퇴근 시간 계산 (정규 근무시간 8시간 기준)
                early_duration = timedelta(hours=8) - work_duration
                if early_duration.total_seconds() < 0:
                    early_time_value = None
                else:
                    early_seconds = int(early_duration.total_seconds())
                    early_hours, early_remainder = divmod(early_seconds, 3600)
                    early_minutes = early_remainder // 60
                    early_time_value = time(early_hours, early_minutes)

                # 근무 시간 계산
                total_seconds = int(work_duration.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes = remainder // 60
                work_time_value = time(hours, minutes)

                # 관리자 퇴근처리 - 알림센터 메세지 전송
                noti_create_fn(
                    content=f"[{obj.work_date}] 총 근무시간 {work_time_value}으로 저장",
                    user=obj.created_by,
                    url=f"/worktime/list",
                    noti_type="worktime_byadmin"
                )

            elif check_out_type == "checkout_cancel":
                check_out_time = None
                ip = None
                work_time_value = None
                early_time_value = None
                is_checkout = False

                # 관리자 퇴근취소 - 알림센터 메세지 전송
                noti_create_fn(
                    content=f"[{obj.work_date}]",
                    user=obj.created_by,
                    url=f"/worktime/list",
                    noti_type="worktime_cancel"
                )

            obj.check_out = check_out_time
            obj.check_out_ip = ip
            obj.work_time = work_time_value
            obj.early_time = early_time_value
            obj.is_checkout = is_checkout
            obj.updated_by = request_user
            obj.save()

        except WorktimeMaster.DoesNotExist:
            return JsonResponse({'error': True, 'message': '출근 기록이 없습니다.'})
        except Exception as e:
            print('퇴근 등록 오류:', e)
            return JsonResponse({'error': True, 'message': '퇴근 등록 중 오류가 발생했습니다.'})

        return JsonResponse({'error': False, 'message': '퇴근이 등록되었습니다.'})


class Worktime_Delete(View):
    @transaction.atomic
    def post(self, request):
        pk = request.POST.get('pk')

        if not pk:
            return JsonResponse({'error': True, 'message': '잘못된 요청입니다.'})

        try:
            obj = get_object_or_404(WorktimeMaster, pk=int(pk))

            # 알림센터 메세지 전송
            noti_create_fn(
                content=f"[{obj.work_date}]",
                user=obj.created_by,
                url=f"/worktime/list",
                noti_type="worktime_deleted"
            )

            obj.delete()

        except Exception as e:
            print('삭제 실패:', e)
            return JsonResponse({'error': True, 'message': '사용중인 데이터입니다. 관련 데이터를 먼저 삭제해주세요.'})

        return JsonResponse({'error': False, 'id': pk})


def get_obj(obj, request):
    request_user_company = request.user.company
    qs = WorktimeMaster.objects.filter(company=request_user_company)

    # 휴가, 출장 정보 끌어오기
    event = EventMaster.objects.filter(
        company=request_user_company,
        created_by=obj.created_by,
        change_type__in=['휴가', '출장'],
        start_date__date__lte=obj.work_date,
        end_date__date__gte=obj.work_date
    ).first()

    # 주간 누적 근무시간 계산
    week_start = obj.work_date - timedelta(days=obj.work_date.weekday())  # 월요일
    week_end = week_start + timedelta(days=6)  # 일요일
    weekly_qs = qs.filter(created_by=obj.created_by, work_date__range=[week_start, week_end])
    total_seconds = sum([
        (wt.work_time.hour * 3600 + wt.work_time.minute * 60 + wt.work_time.second)
        for wt in weekly_qs if wt.work_time
    ])
    # 시간, 분, 초 포맷으로 변경 (그렇지 않으면 프론트에서 1 day, 7:06:00" 같은 형식으로 나옴)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    weekly_total = f"{hours:02}:{minutes:02}:{seconds:02}"

    # 출근 IP 위치
    check_in_ip_place = ''
    if obj.check_in_ip:
        code_obj = CodeMaster.objects.filter(
            group=CodeGroup.IP_ADDRESS,
            company=request_user_company,
            desc1=obj.check_in_ip
        ).first()
        check_in_ip_place = code_obj.name if code_obj else ''

    # 퇴근 IP 위치
    check_out_ip_place = ''
    if obj.check_out_ip:
        code_obj = CodeMaster.objects.filter(
            group=CodeGroup.IP_ADDRESS,
            company=request_user_company,
            desc1=obj.check_out_ip
        ).first()
        check_out_ip_place = code_obj.name if code_obj else ''

    return {
        'id': obj.id,
        'work_date': obj.work_date if obj.work_date is not None else '',
        'check_in': obj.check_in.strftime('%H:%M') if obj.check_in else '',
        'check_out': obj.check_out.strftime('%H:%M') if obj.check_out else '',
        'work_time': obj.work_time.strftime('%H:%M') if obj.work_time else '',
        'late_time': obj.late_time.strftime('%H:%M') if obj.late_time else '',
        'over_time': obj.over_time.strftime('%H:%M') if obj.over_time else '',
        'early_time': obj.early_time.strftime('%H:%M') if obj.early_time else '',
        'check_in_ip': obj.check_in_ip if obj.check_in_ip else '',
        'check_in_ip_place': check_in_ip_place if obj.check_in_ip else '',
        'check_out_ip': obj.check_out_ip if obj.check_out_ip else '',
        'check_out_ip_place': check_out_ip_place if obj.check_out_ip else '',
        'is_checkout': obj.is_checkout,
        'created_by': {
            'id': obj.created_by.id,
            'name': obj.created_by.name,
            'profile_image': obj.created_by.profile_image.url if obj.created_by.profile_image else '',
            'team': obj.created_by.team.name if obj.created_by.team else '',
            'job_level': obj.created_by.job_level.name if obj.created_by.job_level else '',
        } if obj.created_by else '',
        'updated_by': {
            'id': obj.updated_by.id,
            'name': obj.updated_by.name,
            'profile_image': obj.updated_by.profile_image.url if obj.updated_by.profile_image else '',
            'team': obj.updated_by.team.name if obj.updated_by.team else '',
            'job_level': obj.updated_by.job_level.name if obj.updated_by.job_level else '',
        } if obj.updated_by else '',
        'created_at': obj.created_at.strftime('%Y-%m-%d %H:%M') if obj.created_at else '',
        'updated_at': obj.updated_at.strftime('%Y-%m-%d %H:%M') if obj.updated_at else '',
        'company': obj.company.company_info.first().company_name if obj.company.company_info.exists() else '',
        'event': {
            'annual_leave_days': float(event.annual_leave_days) if event and event.annual_leave_days else None,
            'change_type': event.change_type if event and event.change_type else None,
            'start_datetime': event.start_date.strftime('%Y-%m-%d %H:%M') if event and event.start_date else '',
            'end_datetime': event.end_date.strftime('%Y-%m-%d %H:%M') if event and event.end_date else '',
        } if event else None,
        'weekly_total_work_time': str(weekly_total),
    }


# 로컬에서는 문제 없는데 aws에서 check_out_ip가 check_in_ip를 따라가는 문제 발생
# def get_external_ip():
#     try:
#         res = requests.get('https://ipinfo.io/json', timeout=3)
#         if res.status_code == 200:
#             data = res.json()
#             return data.get('ip', '')
#     except Exception as e:
#         print("ipinfo.io 조회 실패:", e)
#     return ''

# 클라우드용 ip체크 함수
def get_external_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# 전직원 목록이 구성된 후 근태데이터를 분배하는 클래스
class Worktime_daily_report(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        fr_date = request.GET.get('fr_date', '')  # fr_date 기준으로 하루만 필터

        base_qs = WorktimeMaster.objects.filter(company=request_user.company).order_by('-work_date', '-check_in')

        # 기간 검색
        if fr_date:
            if isinstance(fr_date, str):
                fr_date = datetime.strptime(fr_date, "%Y-%m-%d").date()
                fr_date = datetime.combine(fr_date, time(0, 0, 0))
                base_qs = base_qs.filter(work_date__gte=fr_date)
                base_qs = base_qs.filter(work_date__lte=fr_date)

        # 키워드 검색
        all_sch = request.GET.get("all_sch", '')
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_condition = (
                        Q(created_by__name__icontains=keyword) |
                        Q(created_by__team__name__icontains=keyword) |
                        Q(check_in_ip__icontains=keyword) |
                        Q(check_out_ip__icontains=keyword)
                    )
                    search_conditions |= search_condition
            base_qs = base_qs.filter(search_conditions)

        late_time_filter = request.GET.get("late_time_filter", "").strip()
        if late_time_filter == "true":
            base_qs = base_qs.filter(late_time__isnull=False).exclude(late_time__exact="00:00:00")

        early_time_filter = request.GET.get("early_time_filter", "").strip()
        if early_time_filter == "true":
            base_qs = base_qs.filter(early_time__isnull=False).exclude(early_time__exact="00:00:00")

        # 모든 직원 기준 리스트 생성
        qs_users = (UserMaster.objects.filter(company=request_user.company, is_staff=1, is_delete=0, is_superuser=0)
                    .order_by('team_id', F('seq_order').asc(nulls_last=True), 'join_date'))

        results = []
        week_start = fr_date - timedelta(days=fr_date.weekday())  # 월요일
        week_end = week_start + timedelta(days=6)  # 일요일

        for user in qs_users:
            worktime = base_qs.filter(created_by=user).first()

            # 주간 누적 근무시간 계산
            wt_qs = WorktimeMaster.objects.filter(company=request_user.company)
            weekly_qs = wt_qs.filter(created_by=request_user, work_date__range=[week_start, week_end])
            total_seconds = sum([
                (wt.work_time.hour * 3600 + wt.work_time.minute * 60 + wt.work_time.second)
                for wt in weekly_qs if wt.work_time
            ])
            # 시간, 분, 초 포맷으로 변경 (그렇지 않으면 프론트에서 1 day, 7:06:00" 같은 형식으로 나옴)
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            weekly_total = f"{hours:02}:{minutes:02}:{seconds:02}"

            # 휴가 데이터 가져오기
            event = EventMaster.objects.filter(
                company=request_user.company,
                created_by=user,
                change_type='휴가',
                start_date__date__lte=fr_date,
                end_date__date__gte=fr_date
            ).first()

            if worktime:
                obj = get_obj(worktime, request)
            else:
                obj = {
                    'id': None,
                    'work_date': '',
                    'check_in': '',
                    'check_out': '',
                    'work_time': '',
                    'late_time': '',
                    'over_time': '',
                    'early_time': '',
                    'check_in_ip': '',
                    'check_in_ip_place': '',
                    'check_out_ip': '',
                    'check_out_ip_place': '',
                    'is_checkout': False,
                    'created_by': {
                        'id': user.id,
                        'name': user.name,
                        'profile_image': user.profile_image.url if user.profile_image else '',
                        'team': user.team.name if user.team else '',
                        'job_level': user.job_level.name if user.job_level else '',
                    },
                    'updated_by': '',
                    'created_at': '',
                    'updated_at': '',
                    'company': user.company.company_info.first().company_name if user.company.company_info.exists() else '',
                    'event': event.change_type if event and event.change_type else None,
                    'weekly_total_work_time': str(weekly_total),
                    'status': 'no_workdata'
                }
            results.append(obj)

        context = {'results': results}
        return JsonResponse(context, safe=False)


# 근태통계 부분
class WorktimeReport_List(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': '인증되지 않은 사용자입니다.'}, status=401)

        request_user = get_object_or_404(UserMaster, id=request.user.id)
        year_sch = request.GET.get('year_sch', '')
        month_sch = request.GET.get('month_sch', '')
        WEEKDAY = ['월', '화', '수', '목', '금', '토', '일']

        try:
            year_sch = int(year_sch)
        except (ValueError, TypeError):
            return JsonResponse({'error': '기준연도에 오류가 있습니다.'}, status=400)

        try:
            month_sch = int(month_sch)
        except (ValueError, TypeError):
            month_sch = 0

        if month_sch:
            last_day = calendar.monthrange(year_sch, month_sch)[1]
            start_date = date(year_sch, month_sch, 1)
            end_date = date(year_sch, month_sch, last_day)
        else:
            last_day = 31
            start_date = date(year_sch, 1, 1)
            end_date = date(year_sch + 1, 1, 1)

        qs = WorktimeMaster.objects.filter(
            company=request_user.company,
            work_date__gte=start_date,
            work_date__lt=end_date
        )

        all_users = UserMaster.objects.filter(
            company=request_user.company,
            is_staff=1,
            is_delete=0,
            is_superuser=0
        ).order_by('team_id', F('seq_order').asc(nulls_last=True), 'join_date')

        if not request_user.is_master:
            if request_user.team:
                all_users = all_users.select_related('team').filter(team=request_user.team)
            else:
                all_users = all_users.filter(id=request_user.id)

        # 부서 검색
        sch_team = request.GET.get('sch_team', '')
        if sch_team:
            all_users = all_users.select_related('team').filter(team=sch_team)

        all_sch = request.GET.get("all_sch", '')
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_conditions |= (
                        Q(name__icontains=keyword) |
                        Q(job_level__name__icontains=keyword)
                    )
            all_users = all_users.filter(search_conditions)

        user_ids = [user.id for user in all_users]
        qs = qs.filter(created_by__id__in=user_ids)

        user_data = {}
        for user in all_users:
            user_data[user.id] = {
                "user_id": user.id,
                "user_name": user.name,
                "job_level": user.job_level.name if user.job_level else "",
                "team": user.team.name if user.team else "",
                "profile_image": user.profile_image.url if user.profile_image and hasattr(user.profile_image, 'url') else "",
                "details": [None] * last_day
            }

        workday_tracker = defaultdict(int)
        worktime_tracker = defaultdict(timedelta)

        qs = qs.order_by('created_by_id', 'work_date')
        for wt in qs:
            user_id = wt.created_by.id
            day_idx = wt.work_date.day - 1
            if day_idx >= last_day:
                continue

            if wt.check_in is None and wt.check_out is None:
                status = "미출근"
            elif wt.check_in and not wt.check_out:
                status = "퇴근미처리"
            elif wt.late_time and wt.early_time:
                status = "지각+조퇴"
            elif wt.late_time:
                status = "지각"
            elif wt.early_time:
                status = "조퇴"
            else:
                status = "정상"

            if status != "미출근":
                workday_tracker[user_id] += 1

            if wt.work_time:
                worktime_tracker[user_id] += timedelta(
                    hours=wt.work_time.hour,
                    minutes=wt.work_time.minute,
                    seconds=wt.work_time.second
                )

            user_dict = user_data[user_id]
            user_dict["details"][day_idx] = {
                "status": status,
                "date": wt.work_date.strftime("%Y-%m-%d"),
                "weekday": WEEKDAY[wt.work_date.weekday()],
                "check_in": wt.check_in.strftime("%H:%M") if wt.check_in else "",
                "check_out": wt.check_out.strftime("%H:%M") if wt.check_out else "",
                "work_time": wt.work_time.strftime("%H:%M") if wt.work_time else "",
            }

        leave_category = CodeMaster.objects.filter(company=request_user.company, name="휴가").last()
        leave_qs = EventMaster.objects.filter(
            company=request_user.company,
            category=leave_category,
            start_date__lte=end_date,
            end_date__gte=start_date
        ).exclude(change_type__in=["연차 추가", "연차 삭감"])

        for event in leave_qs:
            user = event.created_by
            if not user or user.id not in user_data:
                continue

            current = event.start_date
            while current <= event.end_date:
                if current.year != year_sch or (month_sch and current.month != month_sch):
                    current += timedelta(days=1)
                    continue

                day_idx = current.day - 1
                if 0 <= day_idx < last_day:
                    user_dict = user_data[user.id]
                    if not user_dict["details"][day_idx]:
                        user_dict["details"][day_idx] = {
                            "status": "휴가",
                            "date": current.strftime("%Y-%m-%d"),
                            "weekday": WEEKDAY[current.weekday()],
                            "check_in": "",
                            "check_out": ""
                        }
                current += timedelta(days=1)

        total_possible_days = 0
        if month_sch:
            _, last_day_of_month = calendar.monthrange(year_sch, month_sch)
            for d in range(1, last_day_of_month + 1):
                weekday = date(year_sch, month_sch, d).weekday()
                if weekday < 5:
                    total_possible_days += 1

        for user_id, user_dict in user_data.items():
            workday_count = workday_tracker[user_id]
            work_seconds = worktime_tracker[user_id].total_seconds()
            user_dict["month_workdays"] = workday_count
            user_dict["total_workdays"] = total_possible_days
            user_dict["month_workhours"] = round(min(work_seconds / 3600, 209), 1)
            user_dict["total_workhours"] = total_possible_days * 8

        results = list(user_data.values())

        context = {
            'count': len(results),
            'previous': None,
            'next': None,
            'results': results,
        }

        return JsonResponse(context, safe=False)


# 페이지내이션 포함된 코드(사용안할듯)
# class WorktimeReport_List(View):
#     @transaction.atomic
#     def get(self, request, *args, **kwargs):
#         if not request.user.is_authenticated:
#             return JsonResponse({'error': '인증되지 않은 사용자입니다.'}, status=401)
#
#         request_user = get_object_or_404(UserMaster, id=request.user.id)
#         _page = request.GET.get('page', '1')
#         _size = request.GET.get('page_size', '20')
#         year_sch = request.GET.get('year_sch', '')
#         month_sch = request.GET.get('month_sch', '')
#         WEEKDAY = ['월', '화', '수', '목', '금', '토', '일']
#
#         # 연도, 월 파싱
#         try:
#             year_sch = int(year_sch)
#         except (ValueError, TypeError):
#             return JsonResponse({'error': '기준연도에 오류가 있습니다.'}, status=400)
#
#         try:
#             month_sch = int(month_sch)
#         except (ValueError, TypeError):
#             month_sch = 0
#
#         # 마지막 일 계산 및 날짜 범위 설정
#         if month_sch:
#             last_day = calendar.monthrange(year_sch, month_sch)[1]
#             start_date = date(year_sch, month_sch, 1)
#             end_date = date(year_sch, month_sch, last_day)
#         else:
#             last_day = 31
#             start_date = date(year_sch, 1, 1)
#             end_date = date(year_sch + 1, 1, 1)
#
#         # 근태 데이터 쿼리
#         qs = WorktimeMaster.objects.filter(
#             company=request_user.company,
#             work_date__gte=start_date,
#             work_date__lt=end_date
#         )
#
#         # 사용자 목록
#         all_users = UserMaster.objects.filter(
#             company=request_user.company,
#             is_staff=1,
#             is_delete=0,
#             is_superuser=0
#         ).order_by('team_id', F('seq_order').asc(nulls_last=True), 'join_date')
#
#         if not request_user.is_master:
#             all_users = all_users.filter(id=request_user.id)
#
#         # 검색 필터
#         all_sch = request.GET.get("all_sch", '')
#         if all_sch:
#             search_keywords = all_sch.split(',')
#             search_conditions = Q()
#             for keyword in search_keywords:
#                 keyword = keyword.strip()
#                 if keyword:
#                     search_conditions |= (
#                         Q(name__icontains=keyword) |
#                         Q(team__name__icontains=keyword) |
#                         Q(job_level__name__icontains=keyword)
#                     )
#             all_users = all_users.filter(search_conditions)
#
#         user_ids = [user.id for user in all_users]
#         qs = qs.filter(created_by__id__in=user_ids)
#
#         # 페이지네이션
#         qs_ps = Pagenation(qs, _size, _page)
#         pre = int(_page) - 1
#         next = int(_page) + 1
#         url_pre = f"/?page_size={_size}&page={pre}" if pre > 0 else None
#         url_next = f"/?page_size={_size}&page={next}" if next <= qs_ps.paginator.num_pages else None
#
#         # 사용자별 기본 구조 초기화
#         user_data = {}
#         for user in all_users:
#             user_data[user.id] = {
#                 "user_id": user.id,
#                 "user_name": user.name,
#                 "job_level": user.job_level.name if user.job_level else "",
#                 "team": user.team.name if user.team else "",
#                 "profile_image": user.profile_image.url if user.profile_image and hasattr(user.profile_image, 'url') else "",
#                 "details": [None] * last_day
#             }
#
#         workday_tracker = defaultdict(int)
#         worktime_tracker = defaultdict(timedelta)
#
#         # 근태 데이터 적용
#         qs = qs.order_by('created_by_id', 'work_date')
#         for wt in qs:
#             user_id = wt.created_by.id
#             day_idx = wt.work_date.day - 1
#             if day_idx >= last_day:
#                 continue
#
#             if wt.check_in is None and wt.check_out is None:
#                 status = "미출근"
#             elif wt.check_in and not wt.check_out:
#                 status = "퇴근미처리"
#             elif wt.late_time and wt.early_time:
#                 status = "지각+조퇴"
#             elif wt.late_time:
#                 status = "지각"
#             elif wt.early_time:
#                 status = "조퇴"
#             else:
#                 status = "정상"
#
#             if status != "미출근":
#                 workday_tracker[user_id] += 1
#
#             if wt.work_time:
#                 worktime_tracker[user_id] += timedelta(
#                     hours=wt.work_time.hour,
#                     minutes=wt.work_time.minute,
#                     seconds=wt.work_time.second
#                 )
#
#             user_dict = user_data[user_id]
#             user_dict["details"][day_idx] = {
#                 "status": status,
#                 "date": wt.work_date.strftime("%Y-%m-%d"),
#                 "weekday": WEEKDAY[wt.work_date.weekday()],
#                 "check_in": wt.check_in.strftime("%H:%M") if wt.check_in else "",
#                 "check_out": wt.check_out.strftime("%H:%M") if wt.check_out else "",
#                 "work_time": wt.work_time.strftime("%H:%M") if wt.work_time else "",
#             }
#
#         leave_category = CodeMaster.objects.filter(company=request_user.company, name="휴가").last()
#         leave_qs = EventMaster.objects.filter(
#             company=request_user.company,
#             category=leave_category,
#             start_date__lte=end_date,
#             end_date__gte=start_date
#         )
#
#         for event in leave_qs:
#             user = event.created_by
#             if not user or user.id not in user_data:
#                 continue
#
#             current = event.start_date
#             while current <= event.end_date:
#                 if current.year != year_sch or (month_sch and current.month != month_sch):
#                     current += timedelta(days=1)
#                     continue
#
#                 day_idx = current.day - 1
#                 if 0 <= day_idx < last_day:
#                     user_dict = user_data[user.id]
#                     if not user_dict["details"][day_idx]:
#                         user_dict["details"][day_idx] = {
#                             "status": "휴가",
#                             "date": current.strftime("%Y-%m-%d"),
#                             "weekday": WEEKDAY[current.weekday()],
#                             "check_in": "",
#                             "check_out": ""
#                         }
#                 current += timedelta(days=1)
#
#         total_possible_days = 0
#         if month_sch:
#             _, last_day_of_month = calendar.monthrange(year_sch, month_sch)
#             for d in range(1, last_day_of_month + 1):
#                 weekday = date(year_sch, month_sch, d).weekday()
#                 if weekday < 5:
#                     total_possible_days += 1
#
#         for user_id, user_dict in user_data.items():
#             workday_count = workday_tracker[user_id]
#             work_seconds = worktime_tracker[user_id].total_seconds()
#             user_dict["month_workdays"] = workday_count
#             user_dict["total_workdays"] = total_possible_days
#             user_dict["month_workhours"] = round(min(work_seconds / 3600, 209), 1)
#             user_dict["total_workhours"] = total_possible_days * 8
#
#         results = list(user_data.values())
#
#         context = {
#             'count': qs_ps.paginator.count,
#             'previous': url_pre,
#             'next': url_next,
#             'results': results,
#         }
#
#         return JsonResponse(context, safe=False)
