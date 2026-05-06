from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, OuterRef, Subquery, Max, Sum, F
from api.models import UserMaster, Recruit
from api.lib import Pagenation, get_excep_msg
from datetime import datetime, date
from collections import defaultdict
from django.utils import timezone
from api.factory.factory_lib import get_user_info
from django.db.models.functions import TruncDate, TruncMonth
from django.conf import settings


class Recruit_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')

        qs = Recruit.objects.filter(company=request_user.company).order_by('-start_date')
        
        # 키워드 검색
        all_sch = request.GET.get("all_sch", '')
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_condition = (
                            Q(desc1__icontains=keyword) |
                            Q(desc2__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        # 기간 검색
        if fr_date:
            qs = qs.filter(start_date__gte=fr_date)
        if to_date:
            qs = qs.filter(end_date__lte=to_date)

        # sch_work_type 필터
        sch_work_type = request.GET.get('sch_work_type', '')
        if sch_work_type:
            qs = qs.filter(work_type=sch_work_type)

        # sch_user 필터
        sch_user = request.GET.get('sch_user', '')
        if sch_user:
            qs = qs.filter(user_id=sch_user)

        # sch_customer 필터
        sch_customer = request.GET.get('sch_customer', '')
        if sch_customer:
            qs = qs.filter(customer_id=sch_customer)

        # sch_recruit_site 필터
        sch_recruit_site = request.GET.get('sch_recruit_site', '')
        if sch_recruit_site:
            qs = qs.filter(recruit_site_id=sch_recruit_site)

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


class Recruit_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)

            user = request.POST.get('user', '')
            user = int(user) if user.isdigit() else None
            subsidiary = request.POST.get('subsidiary', '')
            subsidiary = int(subsidiary) if subsidiary.isdigit() else None
            recruit_site = request.POST.get('recruit_site', '')
            recruit_site = int(recruit_site) if recruit_site.isdigit() else None
            customer = request.POST.get('customer', '')
            customer = int(customer) if customer.isdigit() else None
            start_date_str = request.POST.get('start_date', '')
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else None
            end_date_str = request.POST.get('end_date', '')
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else None
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')
            price = request.POST.get('price', '')
            work_type = request.POST.get('work_type', '')
            price = float(price) if price else 0

            obj = Recruit.objects.create(
                user_id=user,
                subsidiary_id=subsidiary,
                recruit_site_id=recruit_site,
                customer_id=customer,
                start_date=start_date,
                end_date=end_date,
                desc1=desc1,
                desc2=desc2,
                price=price,
                work_type = work_type,

                created_by=request_user,
                updated_by=request_user,
                created_at=timezone.now().date(),
                updated_at=timezone.now().date(),
                company=request_user.company,
            )

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class Recruit_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            user = request.POST.get('user', '')
            user = int(user) if user.isdigit() else None
            subsidiary = request.POST.get('subsidiary', '')
            subsidiary = int(subsidiary) if subsidiary.isdigit() else None
            recruit_site = request.POST.get('recruit_site', '')
            recruit_site = int(recruit_site) if recruit_site.isdigit() else None
            customer = request.POST.get('customer', '')
            customer = int(customer) if customer.isdigit() else None
            start_date_str = request.POST.get('start_date', '')
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else None
            end_date_str = request.POST.get('end_date', '')
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else None
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')
            price = request.POST.get('price', '')
            work_type = request.POST.get('work_type', '')
            price = float(price) if price else 0

            obj = get_object_or_404(Recruit, pk=int(pk))

            obj.user_id = user
            obj.recruit_site_id = recruit_site
            obj.subsidiary_id = subsidiary
            obj.customer_id = customer
            obj.start_date = start_date
            obj.end_date = end_date
            obj.desc1 = desc1
            obj.desc2 = desc2
            obj.price = price
            obj.work_type = work_type

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class Recruit_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(Recruit, pk=int(pk))
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
        'user': get_user_info(obj.user) if obj.user else '',
        'subsidiary_id': obj.subsidiary.id if obj.subsidiary else '',
        'subsidiary_name': obj.subsidiary.name if obj.subsidiary else '',
        'recruit_site_id': obj.recruit_site.id if obj.recruit_site else '',
        'recruit_site_name': obj.recruit_site.name if obj.recruit_site else '',
        'customer_id': obj.customer.id if obj.customer else '',
        'customer_name': obj.customer.name if obj.customer else '',
        'start_date': obj.start_date.strftime('%Y-%m-%d') if obj.start_date else '',
        'end_date': obj.end_date.strftime('%Y-%m-%d') if obj.end_date else '',
        'work_type': obj.work_type or '',
        'desc1': obj.desc1 or '',
        'desc2': obj.desc2 or '',
        'price': obj.price or '',

        'created_by': get_user_info(obj.created_by) if obj.created_by else '',
        'updated_by': get_user_info(obj.updated_by) if obj.updated_by else '',
        'created_at': obj.created_at.strftime('%Y-%m-%d') if obj.created_at else '',
        'updated_at': obj.updated_at.strftime('%Y-%m-%d') if obj.updated_at else '',
        'company_id': obj.company.id if obj.company is not None else '',
        'company_name': obj.company.company_info.first().company_name if obj.company.company_info.exists() else '',
    }


# 법인카드 통계
class RecruitManager_Data(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        a_year_filter = request.GET.get('a_year_filter', '')
        try:
            a_year_filter = int(a_year_filter)
        except (ValueError, TypeError):
            return JsonResponse({'error': '기준연도에 오류가 있습니다.'}, status=400)

        start_date = date(a_year_filter, 1, 1)  # 선택연도의 1월 1일
        end_date = date(a_year_filter, 12, 31)  # 선택연도의 12월 31일

        qs = Recruit.objects.filter(start_date__gte=start_date, end_date__lte=end_date,
                                    company=request_user.company).order_by('-start_date', '-id')

        # 키워드 검색
        all_sch = request.GET.get("all_sch", '')
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_condition = (
                            Q(desc1__icontains=keyword) |
                            Q(desc2__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        # sch_customer 필터
        sch_customer = request.GET.get('sch_customer', '')
        if sch_customer:
            qs = qs.filter(customer_id=sch_customer)

        # 월별 통계처리
        monthly_summary_qs = qs.annotate(month=TruncMonth('start_date')) \
            .values('month') \
            .annotate(total_price=Sum('price')) \
            .order_by('month')

        monthly_summary = [
            {
                'month': item['month'].strftime('%y/%m'),
                'total_price': item['total_price'] or 0
            }
            for item in monthly_summary_qs
        ]

        # 사용자별/월별 통계처리 (id 기준 합산)
        monthly_user_qs = (
            qs.annotate(month=TruncMonth('start_date'))
            .values('month', 'user__id')  # id 기준 그룹
            .annotate(
                total_price=Sum('price'),
                user_name=F('user__name'),  # 이름
                user_job_level=F('user__job_level__name'),  # 직급
                user_profile_image=F('user__profile_image')  # 프로필 이미지
            )
            .order_by('month', 'user_name')
        )

        monthly_user_summary = defaultdict(list)
        for row in monthly_user_qs:
            month_key = row['month'].strftime('%y/%m')

            profile_url = ''
            if row['user_profile_image']:
                # 절대경로 생성
                profile_url = request.build_absolute_uri(
                    settings.MEDIA_URL + str(row['user_profile_image'])
                )

            monthly_user_summary[month_key].append({
                'user_id': row['user__id'],
                'user_name': row['user_name'] or '',
                'user_job_level': row['user_job_level'] or '',
                'user_profile_image': profile_url,
                'total_price': row['total_price'] or 0
            })

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

        results = [get_obj_cost(row) for row in qs_ps]

        context = {
            'count': qs_ps.paginator.count,
            'previous': url_pre,
            'next': url_next,
            'results': results,
            'monthly_summary': monthly_summary,  # 월별 합계 (그래프용)
            'monthly_user_summary': monthly_user_summary,  # 사람별 월별 합계 (테이블용)
        }

        return JsonResponse(context, safe=False)


class Recruit_Data(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        a_year_filter = request.GET.get('a_year_filter', '')
        try:
            a_year_filter = int(a_year_filter)
        except (ValueError, TypeError):
            return JsonResponse({'error': '기준연도에 오류가 있습니다.'}, status=400)

        start_date = date(a_year_filter, 1, 1)  # 선택연도의 1월 1일
        end_date = date(a_year_filter, 12, 31)  # 선택연도의 12월 31일

        qs = Recruit.objects.filter(start_date__gte=start_date, end_date__lte=end_date,
                                    company=request_user.company).order_by('-start_date', '-id')

        # 키워드 검색
        all_sch = request.GET.get("all_sch", '')
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_condition = (
                            Q(desc1__icontains=keyword) |
                            Q(desc2__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        # sch_customer 필터
        sch_customer = request.GET.get('sch_customer', '')
        if sch_customer:
            qs = qs.filter(customer_id=sch_customer)

        # 월별 통계처리
        monthly_summary_qs = qs.annotate(month=TruncMonth('start_date')) \
            .values('month') \
            .annotate(total_price=Sum('price')) \
            .order_by('month')

        monthly_summary = [
            {
                'month': item['month'].strftime('%y/%m'),
                'total_price': item['total_price'] or 0
            }
            for item in monthly_summary_qs
        ]

        # 카드별/월별 통계처리
        monthly_card_qs = qs.annotate(month=TruncMonth('start_date')) \
            .values('month', 'recruit_site__id', 'recruit_site__name') \
            .annotate(total_price=Sum('price')) \
            .order_by('month', 'recruit_site__name')

        monthly_card_summary = defaultdict(list)
        for row in monthly_card_qs:
            month_key = row['month'].strftime('%y/%m')
            monthly_card_summary[month_key].append({
                'recruit_site__id': row['recruit_site__id'],
                'recruit_site__name': row['recruit_site__name'],
                'total_price': row['total_price'] or 0
            })

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

        results = [get_obj_cost(row) for row in qs_ps]

        context = {
            'count': qs_ps.paginator.count,
            'previous': url_pre,
            'next': url_next,
            'results': results,
            'monthly_summary': monthly_summary,  # 월별 합계 (그래프용)
            'monthly_card_summary': monthly_card_summary,  # 사람별 월별 합계 (테이블용)
        }

        return JsonResponse(context, safe=False)


def get_obj_cost(obj):
    return {
        'id': obj.id,
        'desc1': obj.desc1,
        'desc2': obj.desc2,
        'price': obj.price,
    }
