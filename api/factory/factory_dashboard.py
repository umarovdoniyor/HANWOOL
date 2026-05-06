from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.db.models import F, ExpressionWrapper, FloatField, Case, When, Value, Sum
from django.db.models.functions import NullIf
from api.models import UserMaster, FactoryCustomerOrder, FactoryQuotation, FactoryItem, FactoryPurchase, \
    FactoryProduction, FactoryCustomerOrderItem
from api.factory.inventory_list import get_item_stock
from django.db.models.functions import TruncDate, TruncMonth
from calendar import month_name
from collections import OrderedDict
from django.db import models


class FactoryDashboard_Production_Status(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')

        qs = FactoryProduction.objects.filter(status="완료", company=request_user.company)

        # 기간 검색
        if fr_date:
            qs = qs.filter(start_date__gte=fr_date)
        if to_date:
            qs = qs.filter(end_date__lte=to_date)

        # sch_item 필터
        sch_item = request.GET.get('sch_item', '')
        if sch_item:
            qs = qs.filter(item_id=sch_item)

        results = (
            qs.values(date=TruncDate('end_date'))
            .annotate(
                result_qty=Sum('result_qty'),
                total_qty=Sum('total_qty'),
                faulty_qty=Sum('faulty_qty'),
            )
            .order_by('date')
        )

        context = {
            'results': list(results),
        }

        return JsonResponse(context, safe=False)


class FactoryDashboard_Quotation_Order_Status(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')

        qs_all = FactoryQuotation.objects.filter(company=request_user.company)
        qs_done = FactoryQuotation.objects.filter(status="수주", company=request_user.company)

        # 기간 검색
        if fr_date:
            qs_all = qs_all.filter(quotation_date__gte=fr_date)
            qs_done = qs_done.filter(quotation_date__gte=fr_date)
        if to_date:
            qs_all = qs_all.filter(quotation_date__lte=to_date)
            qs_done = qs_done.filter(quotation_date__lte=to_date)

        results_quotation = list(
            qs_all.values(date=TruncMonth('quotation_date'))
            .annotate(price=Sum('price'))
            .order_by('date')
        )

        results_order = list(
            qs_done.values(date=TruncMonth('quotation_date'))
            .annotate(price=Sum('price'))
            .order_by('date')
        )

        context = {
            'quotation': results_quotation,
            'order': results_order,
        }

        return JsonResponse(context, safe=False)


class FactoryDashboard_Inventory_Status(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)

        qs = FactoryItem.objects.filter(is_valid=True, company=request_user.company)

        result_dict = {}

        for item in qs:
            try:
                _, _, _, _, item_stock = get_item_stock(item.id)
                stock_value = item_stock * (item.std_cost or 0)

                class_id = item.item_class_id or 0
                class_name = item.item_class.name if item.item_class else "미분류"

                if class_id not in result_dict:
                    result_dict[class_id] = {
                        'item_class_id': class_id,
                        'item_class_name': class_name,
                        'total_stock_value': 0,
                    }

                result_dict[class_id]['total_stock_value'] += stock_value
            except Exception as e:
                continue  # 개별 품목 에러는 무시

        context = {
            'results': list(result_dict.values()),
        }

        return JsonResponse(context, safe=False)


class FactoryDashboard_Purchase_Sales_Status(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')

        qs_purchase = FactoryPurchase.objects.filter(status="완료", company=request_user.company)
        qs_order = FactoryCustomerOrder.objects.filter(status="완료", company=request_user.company)

        # 기간 검색
        if fr_date:
            qs_purchase = qs_purchase.filter(receive_date__gte=fr_date)
            qs_order = qs_order.filter(order_date__gte=fr_date)
        if to_date:
            qs_purchase = qs_purchase.filter(receive_date__lte=to_date)
            qs_order = qs_order.filter(order_date__lte=to_date)

        results_purchase = list(
            qs_purchase.values(date=TruncMonth('receive_date'))
            .annotate(price=Sum('price'))
            .order_by('date')
        )

        results_order = list(
            qs_order.values(date=TruncMonth('order_date'))
            .annotate(price=Sum('price'))
            .order_by('date')
        )

        context = {
            'purchase': results_purchase,
            'order': results_order,
        }

        return JsonResponse(context, safe=False)


class FactoryDashboard_Production_Faulty_Rate(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')

        qs = FactoryProduction.objects.filter(status="완료", company=request_user.company)

        # 기간 검색
        if fr_date:
            qs = qs.filter(start_date__gte=fr_date)
        if to_date:
            qs = qs.filter(end_date__lte=to_date)

        results = (
            qs.annotate(month=TruncMonth('end_date'))
            .values('month')
            .annotate(
                result_qty=Sum('result_qty'),
                faulty_qty=Sum('faulty_qty'),
            )
            .order_by('month')
        )

        # 기본 1월 ~ 12월 빈 틀 만들기
        month_map = OrderedDict(
            (f"{i}월", {'date': f"{i}월", 'result_qty': 0, 'faulty_qty': 0, 'faulty_rate': 0.0}) for i in range(1, 13))

        # 실제 결과 덮어쓰기
        for row in results:
            month = row['month'].month
            month_key = f"{month}월"
            result_qty = row['result_qty'] or 0
            faulty_qty = row['faulty_qty'] or 0
            total_qty = result_qty + faulty_qty
            faulty_rate = round((faulty_qty * 100 / total_qty), 1) if total_qty else 0.0

            month_map[month_key] = {
                'date': month_key,
                'result_qty': result_qty,
                'faulty_qty': faulty_qty,
                'faulty_rate': faulty_rate,
            }

        context = {
            'results': list(month_map.values()),
        }

        return JsonResponse(context, safe=False)


class FactoryDashboard_Production_Delivery_Status(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)

        production_qs = FactoryProduction.objects.filter(
            is_approved=True,
            status__in=["대기", "진행"],
            company=request_user.company
        ).values('id', 'code', 'approver_id', 'item_id', 'item__name', 'item__unit__name', 'is_approved', 'start_date', 'end_date', 'total_qty',
                 'receive_qty', 'faulty_qty', 'result_qty', 'desc1', 'desc2', 'desc3', 'status', 'warehouse_id').order_by('end_date')

        delivery_qs = FactoryCustomerOrder.objects.filter(
            status__in=["대기", "진행"],
            company=request_user.company
        ).values('id', 'code', 'approver_id', 'delivery_user_id', 'customer_id', 'customer__name', 'is_vat', 'price',
                 'order_date', 'request_date', 'desc1', 'desc2', 'desc3', 'status', 'delivery_date').order_by('request_date')

        delivery_list = []
        for delivery in delivery_qs:
            # 관련된 하위 품목 조회
            order_items = FactoryCustomerOrderItem.objects.filter(
                customer_order_id=delivery['id']
            )

            # 하위 품목 수량 합산
            total_qty_sum = order_items.aggregate(total=models.Sum('total_qty'))['total'] or 0

            # 주문서 딕셔너리에 total_qty 추가
            delivery['total_qty'] = int(total_qty_sum) if total_qty_sum == int(total_qty_sum) else total_qty_sum

            delivery_list.append(delivery)

        context = {
            'production': list(production_qs),
            'delivery': list(delivery_qs)
        }

        return JsonResponse(context, safe=False)
