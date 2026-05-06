from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction, IntegrityError
from django.db.models import Q, OuterRef, Subquery, Max, Sum
from api.models import UserMaster, CompanyCard, CompanyCardHistory, MonthlySales
from api.lib import Pagenation, get_excep_msg
from datetime import datetime, date
from collections import defaultdict
from django.utils import timezone
from api.factory.factory_lib import get_user_info, to_float
from django.db.models.functions import TruncDate, TruncMonth


class MonthlySales_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        sch_year = request.GET.get("sch_year", "").strip()
        sch_month = request.GET.get("sch_month", "").strip()

        qs = MonthlySales.objects.filter(company=request_user.company).order_by('-year', '-month', '-id')

        # 기간 검색
        if sch_year:
            qs = qs.filter(year=sch_year)
        if sch_month:
            qs = qs.filter(month=sch_month)

        # sch_subsidiary 필터
        sch_subsidiary = request.GET.get('sch_subsidiary', '')
        if sch_subsidiary:
            qs = qs.filter(subsidiary_id=sch_subsidiary)

        # sch_customer 필터
        sch_customer = request.GET.get('sch_customer', '')
        if sch_customer:
            qs = qs.filter(customer_id=sch_customer)

        # sch_customer_class 필터
        sch_customer_class = request.GET.get('sch_customer_class', '')
        if sch_customer_class:
            qs = qs.filter(customer__customer_class_id=sch_customer_class)

        # sch_is_send 필터
        sch_is_send = request.GET.get('sch_is_send', '')
        if sch_is_send == "true":
            qs = qs.filter(is_send=True)
        elif sch_is_send == "false":
            qs = qs.filter(is_send=False)

        # sch_is_send 필터
        sch_is_done = request.GET.get('sch_is_done', '')
        if sch_is_done == "true":
            qs = qs.filter(is_done=True)
        elif sch_is_done == "false":
            qs = qs.filter(is_done=False)

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


class MonthlySales_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)

            year = int(request.POST.get("year") or 0)
            month = int(request.POST.get("month") or 0)
            is_daily = request.POST.get('is_daily', '').lower() == 'true'
            is_general = request.POST.get('is_general', '').lower() == 'true'

            daily_price = to_float(request.POST.get('daily_price'))
            general_price = to_float(request.POST.get('general_price'))
            total_price = to_float(request.POST.get('total_price'))
            daily_salary = to_float(request.POST.get('daily_salary'))
            general_salary = to_float(request.POST.get('general_salary'))
            total_salary = to_float(request.POST.get('total_salary'))
            daily_profit = to_float(request.POST.get('daily_profit'))
            general_profit = to_float(request.POST.get('general_profit'))
            # vat = request.POST.get('vat', None) or None
            # total_price = request.POST.get('total_price', None) or None

            desc1 = request.POST.get('desc1', '')
            desc1_price = to_float(request.POST.get('desc1_price'))
            desc2 = request.POST.get('desc2', '')
            desc2_price = to_float(request.POST.get('desc2_price'))
            desc3 = request.POST.get('desc3', '')
            desc3_price = to_float(request.POST.get('desc3_price'))
            desc4 = request.POST.get('desc4', '')
            desc4_price = to_float(request.POST.get('desc4_price'))

            subsidiary = request.POST.get('subsidiary', '')
            subsidiary = int(subsidiary) if subsidiary.isdigit() else None
            customer = request.POST.get('customer', '')
            customer = int(customer) if customer.isdigit() else None

            if not is_daily:
                daily_price = 0
                daily_profit = 0

            if not is_general:
                general_price = 0
                general_profit = 0

            sub_total = daily_price + general_price + desc1_price + desc2_price + desc3_price + desc4_price
            vat = round(sub_total * 0.1)
            total_price = sub_total + vat

            obj = MonthlySales.objects.create(
                year=year,
                month=month,
                subsidiary_id=subsidiary,
                customer_id=customer,
                is_daily=is_daily,
                is_general=is_general,
                daily_price=daily_price,
                general_price=general_price,
                vat=vat,
                total_price=total_price,
                daily_salary=daily_salary,
                general_salary=general_salary,
                total_salary=total_salary,
                daily_profit=daily_profit,
                general_profit=general_profit,

                desc1=desc1,
                desc1_price=desc1_price,
                desc2=desc2,
                desc2_price=desc2_price,
                desc3=desc3,
                desc3_price=desc3_price,
                desc4=desc4,
                desc4_price=desc4_price,

                created_by=request_user,
                updated_by=request_user,
                created_at=timezone.now().date(),
                updated_at=timezone.now().date(),
                company=request_user.company,
            )

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except IntegrityError:
            transaction.set_rollback(True)
            return JsonResponse({
                'error': True,
                'message': '동일한 [연도, 월, 센터] 조합의 청구데이터가 이미 존재합니다.'
            }, status=400)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class MonthlySales_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            year = int(request.POST.get("year") or 0)
            month = int(request.POST.get("month") or 0)
            is_daily = request.POST.get('is_daily', '').lower() == 'true'
            is_general = request.POST.get('is_general', '').lower() == 'true'

            daily_price = to_float(request.POST.get('daily_price'))
            general_price = to_float(request.POST.get('general_price'))
            daily_salary = to_float(request.POST.get('daily_salary'))
            general_salary = to_float(request.POST.get('general_salary'))
            total_salary = to_float(request.POST.get('total_salary'))
            daily_profit = to_float(request.POST.get('daily_profit'))
            general_profit = to_float(request.POST.get('general_profit'))
            # vat = request.POST.get('vat', None) or None
            # total_price = request.POST.get('total_price', None) or None

            desc1 = request.POST.get('desc1', '')
            desc1_price = to_float(request.POST.get('desc1_price'))
            desc2 = request.POST.get('desc2', '')
            desc2_price = to_float(request.POST.get('desc2_price'))
            desc3 = request.POST.get('desc3', '')
            desc3_price = to_float(request.POST.get('desc3_price'))
            desc4 = request.POST.get('desc4', '')
            desc4_price = to_float(request.POST.get('desc4_price'))

            subsidiary = request.POST.get('subsidiary', '')
            subsidiary = int(subsidiary) if subsidiary.isdigit() else None
            customer = request.POST.get('customer', '')
            customer = int(customer) if customer.isdigit() else None

            if not is_daily:
                daily_price = 0
                daily_profit = 0

            if not is_general:
                general_price = 0
                general_profit = 0

            sub_total = daily_price + general_price + desc1_price + desc2_price + desc3_price + desc4_price
            vat = round(sub_total * 0.1)
            total_price = sub_total + vat

            obj = get_object_or_404(MonthlySales, pk=int(pk))

            # 중복 데이터 검증
            exists = MonthlySales.objects.filter(
                year=year,
                month=month,
                customer_id=customer,
                company=request_user.company
            ).exclude(id=pk).exists()

            if exists:
                return JsonResponse({
                    'error': True,
                    'message': '동일한 [연도, 월, 고객사] 조합의 청구데이터가 이미 존재합니다.'
                }, status=400)

            # 값 설정
            obj.year = year
            obj.month = month
            obj.is_daily = is_daily
            obj.is_general = is_general
            obj.daily_price = daily_price
            obj.general_price = general_price
            obj.vat = vat
            obj.total_price = total_price
            obj.daily_salary = daily_salary
            obj.general_salary = general_salary
            obj.total_salary = total_salary
            obj.daily_profit = daily_profit
            obj.general_profit = general_profit
            obj.subsidiary_id = subsidiary
            obj.customer_id = customer

            obj.desc1 = desc1
            obj.desc1_price = desc1_price
            obj.desc2 = desc2
            obj.desc2_price = desc2_price
            obj.desc3 = desc3
            obj.desc3_price = desc3_price
            obj.desc4 = desc4
            obj.desc4_price = desc4_price

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except IntegrityError:
            transaction.set_rollback(True)
            return JsonResponse({
                'error': True,
                'message': '동일한 [연도, 월, 고객사] 조합의 청구데이터가 이미 존재합니다.'
            }, status=400)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class MonthlySales_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(MonthlySales, pk=int(pk))
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
        'year': obj.year or '',
        'month': obj.month or '',
        'is_daily': obj.is_daily,
        'is_general': obj.is_general,

        'subsidiary_id': obj.subsidiary.id if obj.subsidiary is not None else '',
        'subsidiary_name': obj.subsidiary.name if obj.subsidiary is not None else '',
        'customer_id': obj.customer.id if obj.customer is not None else '',
        'customer_name': obj.customer.name if obj.customer is not None else '',
        'customer_class_name': obj.customer.customer_class.name if obj.customer and obj.customer.customer_class is not None else '',

        'daily_price': obj.daily_price if obj.daily_price is not None else None,   # 단기청구액
        'general_price': obj.general_price if obj.general_price is not None else None,  # 파견청구액
        'vat': obj.vat if obj.vat is not None else None,  # 부가세
        'total_price': obj.total_price if obj.total_price is not None else None,  # 총 청구액
        'daily_profit': obj.daily_profit if obj.daily_profit is not None else None,  # 단기청구 이익금
        'general_profit': obj.general_profit if obj.general_profit is not None else None,  # 파견청구 이익금

        'desc1': obj.desc1 or '',
        'desc1_price': obj.desc1_price if obj.desc1_price is not None else None,  # 추가기입1
        'desc2': obj.desc2 or '',
        'desc2_price': obj.desc2_price if obj.desc2_price is not None else None,  # 추가기입2
        'desc3': obj.desc3 or '',
        'desc3_price': obj.desc3_price if obj.desc3_price is not None else None,  # 추가기입3
        'desc4': obj.desc4 or '',
        'desc4_price': obj.desc4_price if obj.desc4_price is not None else None,  # 추가기입4

        'is_send': obj.is_send,  # True 청구, False 미청구
        'is_done': obj.is_done,  # True 결제완료, False 결제미완료
        'paid_price': obj.paid_price if obj.paid_price is not None else None,  # 거래처 실지급액
        'paid_date': obj.paid_date or '',

        'created_by': get_user_info(obj.created_by) if obj.created_by else '',
        'updated_by': get_user_info(obj.updated_by) if obj.updated_by else '',
        'created_at': obj.created_at.strftime('%Y-%m-%d') if obj.created_at else '',
        'updated_at': obj.updated_at.strftime('%Y-%m-%d') if obj.updated_at else '',
        'company_id': obj.company.id if obj.company is not None else '',
        'company_name': obj.company.company_info.first().company_name if obj.company.company_info.exists() else '',
    }


class MonthlySales_DailyPrice(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            daily_price = to_float(request.POST.get('total_total'))
            daily_profit = to_float(request.POST.get('total_fee'))

            obj = get_object_or_404(MonthlySales, pk=int(pk))

            general_price = obj.general_price or 0
            if not obj.is_general:
                obj.general_price = 0
                obj.general_profit = 0
                general_price = 0

            desc1_price = obj.desc1_price or 0
            desc2_price = obj.desc2_price or 0
            desc3_price = obj.desc3_price or 0
            desc4_price = obj.desc4_price or 0

            obj.daily_price = daily_price
            obj.vat = round((general_price + daily_price + desc1_price + desc2_price + desc3_price + desc4_price) * 0.1)
            obj.total_price = general_price + daily_price + desc1_price + desc2_price + desc3_price + desc4_price + obj.vat
            obj.daily_profit = daily_profit

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class MonthlySales_GeneralPrice(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            general_price = to_float(request.POST.get('total_total'))
            general_profit = to_float(request.POST.get('total_fee'))

            obj = get_object_or_404(MonthlySales, pk=int(pk))

            daily_price = obj.daily_price or 0
            if not obj.is_daily:
                obj.daily_price = 0
                obj.daily_profit = 0
                daily_price = 0

            desc1_price = obj.desc1_price or 0
            desc2_price = obj.desc2_price or 0
            desc3_price = obj.desc3_price or 0
            desc4_price = obj.desc4_price or 0

            obj.general_price = general_price
            obj.vat = round((general_price + daily_price + desc1_price + desc2_price + desc3_price + desc4_price) * 0.1)
            obj.total_price = general_price + daily_price + desc1_price + desc2_price + desc3_price + desc4_price + obj.vat
            obj.general_profit = general_profit

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class MonthlySales_Result(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            is_send = request.POST.get('is_send', '').lower() == 'true'
            is_done = request.POST.get('is_done', '').lower() == 'true'
            paid_price = to_float(request.POST.get('paid_price'))
            paid_date = request.POST.get('paid_date', None) or None

            obj = get_object_or_404(MonthlySales, pk=int(pk))

            obj.is_send = is_send
            obj.is_done = is_done
            obj.paid_price = paid_price
            obj.paid_date = paid_date

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class MonthlySales_Data(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        a_year_filter = request.GET.get('a_year_filter', '')
        try:
            a_year_filter = int(a_year_filter)
        except (ValueError, TypeError):
            return JsonResponse({'error': '기준연도에 오류가 있습니다.'}, status=400)

        # 해당 연도의 데이터만 필터링
        qs = MonthlySales.objects.filter(
            company=request_user.company,
            year=a_year_filter
        )

        # sch_customer_class 필터
        sch_customer_class = request.GET.get('sch_customer_class', '')
        if sch_customer_class:
            qs = qs.filter(customer__customer_class_id=sch_customer_class)

        # 월별 total_price, paid_price 합계
        monthly_summary_qs = qs.values('month') \
            .annotate(
                sum_total_price=Sum('total_price'),
                sum_paid_price=Sum('paid_price'),
            ).order_by('month')

        monthly_summary = [
            {
                'month': f"{a_year_filter}/{str(item['month']).zfill(2)}",
                'total_price': item['sum_total_price'] or 0,
                'paid_price': item['sum_paid_price'] or 0,
            }
            for item in monthly_summary_qs
        ]

        # 전체 합계도 같이 내려주면 유용함
        total_summary = {
            'year': a_year_filter,
            'total_price': qs.aggregate(sum_total=Sum('total_price'))['sum_total'] or 0,
            'paid_price': qs.aggregate(sum_paid=Sum('paid_price'))['sum_paid'] or 0,
        }

        context = {
            'monthly_summary': monthly_summary,  # 월별 합계
            'total_summary': total_summary,      # 연도별 합계
        }

        return JsonResponse(context, safe=False)