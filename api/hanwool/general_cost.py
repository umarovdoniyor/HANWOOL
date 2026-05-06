from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, OuterRef, Subquery, Max, Sum
from api.models import UserMaster, GeneralCost
from api.lib import Pagenation, get_excep_msg
from datetime import datetime, date
from collections import defaultdict
from django.utils import timezone
from api.factory.factory_lib import get_user_info, to_float
from django.db.models.functions import TruncDate, TruncMonth


class GeneralCost_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')

        qs = GeneralCost.objects.filter(company=request_user.company).order_by('-date')

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
            qs = qs.filter(date__gte=fr_date)
        if to_date:
            qs = qs.filter(date__lte=to_date)

        # sch_subsidiary 필터
        sch_subsidiary = request.GET.get('sch_subsidiary', '')
        if sch_subsidiary:
            qs = qs.filter(subsidiary_id=sch_subsidiary)

        # sch_cost_type 필터
        sch_cost_type = request.GET.get('sch_cost_type', '')
        if sch_cost_type:
            qs = qs.filter(cost_type=sch_cost_type)

        # sch_cost_account 필터
        sch_cost_account = request.GET.get('sch_cost_account', '')
        if sch_cost_account:
            qs = qs.filter(cost_account_id=sch_cost_account)

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


class GeneralCost_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)

            subsidiary_id = request.POST.get('subsidiary', '')
            subsidiary_id = int(subsidiary_id) if subsidiary_id.isdigit() else None
            cost_type = request.POST.get('cost_type', '')
            cost_account = request.POST.get('cost_account', '')
            cost_account = int(cost_account) if cost_account.isdigit() else None
            date = request.POST.get('date', None) or None
            price = to_float(request.POST.get('price'))
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')

            obj = GeneralCost.objects.create(
                subsidiary_id=subsidiary_id,
                cost_type=cost_type,
                cost_account_id=cost_account,
                date=date,
                price=price,
                desc1=desc1,
                desc2=desc2,

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


class GeneralCost_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            subsidiary_id = request.POST.get('subsidiary', '')
            subsidiary_id = int(subsidiary_id) if subsidiary_id.isdigit() else None
            cost_type = request.POST.get('cost_type', '')
            cost_account = request.POST.get('cost_account', '')
            cost_account = int(cost_account) if cost_account.isdigit() else None
            date = request.POST.get('date', None) or None
            price = to_float(request.POST.get('price'))
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')

            obj = get_object_or_404(GeneralCost, pk=int(pk))

            obj.subsidiary_id = subsidiary_id
            obj.cost_type = cost_type
            obj.cost_account_id = cost_account
            obj.date = date
            obj.price = price
            obj.desc1 = desc1
            obj.desc2 = desc2

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class GeneralCost_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(GeneralCost, pk=int(pk))
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
        'subsidiary_id': obj.subsidiary.id if obj.subsidiary is not None else '',
        'subsidiary_name': obj.subsidiary.name if obj.subsidiary is not None else '',
        'cost_type': obj.cost_type or '',
        'cost_account_id': obj.cost_account.id if obj.cost_account else '',
        'cost_account_name': obj.cost_account.name if obj.cost_account else '',
        'date': obj.date or '',
        'price': obj.price or '',
        'desc1': obj.desc1 or '',
        'desc2': obj.desc2 or '',

        'created_by': get_user_info(obj.created_by) if obj.created_by else '',
        'updated_by': get_user_info(obj.updated_by) if obj.updated_by else '',
        'created_at': obj.created_at.strftime('%Y-%m-%d') if obj.created_at else '',
        'updated_at': obj.updated_at.strftime('%Y-%m-%d') if obj.updated_at else '',
        'company_id': obj.company.id if obj.company is not None else '',
        'company_name': obj.company.company_info.first().company_name if obj.company.company_info.exists() else '',
    }


# 고정/변동비 통계
class GeneralCost_Data(View):
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

        qs = GeneralCost.objects.filter(date__gte=start_date, date__lte=end_date,company=request_user.company).order_by('-date', '-id')

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

        # sch_cost_type 필터
        sch_cost_type = request.GET.get('sch_cost_type', '')
        if sch_cost_type:
            qs = qs.filter(cost_type=sch_cost_type)

        # sch_cost_account 필터
        sch_cost_account = request.GET.get('sch_cost_account', '')
        if sch_cost_account:
            qs = qs.filter(cost_account_id=sch_cost_account)

        # 월별 합계 (그래프용)
        monthly_summary_qs = qs.annotate(month=TruncMonth('date')) \
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

        # 월별/사업장별 통계처리
        monthly_subsidiary_qs = qs.annotate(month=TruncMonth('date')) \
            .values('month', 'subsidiary__id', 'subsidiary__name') \
            .annotate(total_price=Sum('price')) \
            .order_by('month', 'subsidiary__name')

        monthly_subsidiary_summary = defaultdict(list)
        for row in monthly_subsidiary_qs:
            month_key = row['month'].strftime('%y/%m')
            monthly_subsidiary_summary[month_key].append({
                'subsidiary__id': row['subsidiary__id'],
                'subsidiary__name': row['subsidiary__name'],
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
            'monthly_subsidiary_summary': monthly_subsidiary_summary,  # 사업장별 월별 합계 (테이블용)
        }

        return JsonResponse(context, safe=False)


def get_obj_cost(obj):
    return {
        'id': obj.id,
        'desc1': obj.desc1,
        'desc2': obj.desc2,
        'price': obj.price,
    }
