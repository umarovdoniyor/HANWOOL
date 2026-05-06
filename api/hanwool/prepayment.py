from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, OuterRef, Subquery, Max, Sum
from api.models import UserMaster, GeneralCost, PrePayment
from api.lib import Pagenation, get_excep_msg
from datetime import datetime, date
from collections import defaultdict
from django.utils import timezone
from api.factory.factory_lib import get_user_info, to_float
from django.db.models.functions import TruncDate, TruncMonth


class PrePayment_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')

        qs = PrePayment.objects.filter(company=request_user.company).order_by('-date')

        # 키워드 검색
        all_sch = request.GET.get("all_sch", '')
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_condition = (
                        Q(user__name__icontains=keyword) |
                        Q(bank__name__icontains=keyword) |
                        Q(account_code__icontains=keyword) |
                        Q(account_name__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        # 기간 검색
        if fr_date:
            qs = qs.filter(date__gte=fr_date)
        if to_date:
            qs = qs.filter(date__lte=to_date)

        # sch_customer 필터
        sch_customer = request.GET.get('sch_customer', '')
        if sch_customer:
            qs = qs.filter(customer_id=sch_customer)

        # sch_price_result 필터 (처리유무)
        sch_price_result = request.GET.get('sch_price_result', '')
        if sch_price_result:
            qs = qs.filter(price_result=sch_price_result)

        # sch_deduct_result 필터 (정산확인)
        sch_deduct_result = request.GET.get('sch_deduct_result', '')
        if sch_deduct_result:
            qs = qs.filter(deduct_result=sch_deduct_result)

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


class PrePayment_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)

            customer = request.POST.get('customer', '')
            customer = int(customer) if customer.isdigit() else None
            user = request.POST.get('user', '')
            user = int(user) if user.isdigit() else None
            bank = request.POST.get('bank', None)
            bank = int(bank) if bank.isdigit() else None

            date = request.POST.get('date', None) or None
            account_code = request.POST.get('account_code', '')
            account_name = request.POST.get('account_name', '')
            price = to_float(request.POST.get('price'))
            deduct = to_float(request.POST.get('deduct'))
            price_result = request.POST.get('price_result', '')
            deduct_result = request.POST.get('deduct_result', '')

            obj = PrePayment.objects.create(
                customer_id=customer,
                user_id=user,
                bank_id=bank,
                date=date,
                account_code=account_code,
                account_name=account_name,
                price=price,
                deduct=deduct,
                price_result=price_result,
                deduct_result=deduct_result,

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


class PrePayment_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            customer = request.POST.get('customer', '')
            customer = int(customer) if customer.isdigit() else None
            user = request.POST.get('user', '')
            user = int(user) if user.isdigit() else None
            bank = request.POST.get('bank', None)
            bank = int(bank) if bank.isdigit() else None

            date = request.POST.get('date', None) or None
            account_code = request.POST.get('account_code', '')
            account_name = request.POST.get('account_name', '')
            price = to_float(request.POST.get('price'))
            deduct = to_float(request.POST.get('deduct'))
            price_result = request.POST.get('price_result', '')
            deduct_result = request.POST.get('deduct_result', '')

            obj = get_object_or_404(PrePayment, pk=int(pk))

            obj.customer_id = customer
            obj.user_id = user
            obj.bank_id = bank
            obj.date = date
            obj.account_code = account_code
            obj.account_name = account_name
            obj.price = price
            obj.deduct = deduct
            obj.price_result = price_result
            obj.deduct_result = deduct_result

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class PrePayment_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(PrePayment, pk=int(pk))
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

        'customer_id': obj.customer.id if obj.customer is not None else '',
        'customer_name': obj.customer.name if obj.customer is not None else '',
        'user': get_user_info(obj.user) if obj.user else '',
        'bank_id': obj.bank.id if obj.bank is not None else '',
        'bank_name': obj.bank.name if obj.bank is not None else '',

        'date': obj.date or '',
        'account_code': obj.account_code or '',
        'account_name': obj.account_name or '',
        'price': obj.price or '',
        'deduct': obj.deduct or '',
        'price_result': obj.price_result or '',
        'deduct_result': obj.deduct_result or '',

        'created_by': get_user_info(obj.created_by) if obj.created_by else '',
        'updated_by': get_user_info(obj.updated_by) if obj.updated_by else '',
        'created_at': obj.created_at.strftime('%Y-%m-%d') if obj.created_at else '',
        'updated_at': obj.updated_at.strftime('%Y-%m-%d') if obj.updated_at else '',
        'company_id': obj.company.id if obj.company is not None else '',
        'company_name': obj.company.company_info.first().company_name if obj.company.company_info.exists() else '',
    }


# 가불금 통계
class PrePayment_Data(View):
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

        qs = PrePayment.objects.filter(date__gte=start_date, date__lte=end_date,company=request_user.company).order_by('-date', '-id')

        # 키워드 검색
        all_sch = request.GET.get("all_sch", '')
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_condition = (
                        Q(user__name__icontains=keyword) |
                        Q(bank__name__icontains=keyword) |
                        Q(account_code__icontains=keyword) |
                        Q(account_name__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        # 월별 통계처리
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

        # 카드별/월별 통계처리
        monthly_card_qs = qs.annotate(month=TruncMonth('date')) \
            .values('month', 'customer__id', 'customer__name') \
            .annotate(total_price=Sum('price')) \
            .order_by('month', 'customer__name')

        monthly_card_summary = defaultdict(list)
        for row in monthly_card_qs:
            month_key = row['month'].strftime('%y/%m')
            monthly_card_summary[month_key].append({
                'customer__id': row['customer__id'],
                'customer__name': row['customer__name'],
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
            'monthly_cost_summary': monthly_card_summary,  # 계정별 월별 합계 (테이블용)
        }

        return JsonResponse(context, safe=False)


def get_obj_cost(obj):
    return {
        'id': obj.id,
        'price': obj.price,
    }
