from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q
from api.models import UserMaster, FactoryEvent, CodeMaster, CodeGroup, FactoryQuotation, FactoryQuotationItem, \
    FactoryCustomerOrder, FactoryCustomerOrderItem
from api.lib import Pagenation, get_excep_msg
from django.utils import timezone
from api.factory.inventory_list import get_item_stock
from api.basic_data.notification import noti_create_fn
from datetime import datetime, time
from api.factory.factory_lib import get_itemin_code, get_quotation_code, get_user_info, get_customer_order_code_from_quotation
import json


class FactoryQuotation_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')

        qs = FactoryQuotation.objects.filter(company=request_user.company).order_by('request_date', 'quotation_date')

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
                            Q(customer_quotation__item_code__icontains=keyword) |
                            Q(customer_quotation__item_name__icontains=keyword) |
                            Q(desc1__icontains=keyword) |
                            Q(desc2__icontains=keyword) |
                            Q(desc3__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        # 기간 검색
        if fr_date:
            qs = qs.filter(quotation_date__gte=fr_date)
        if to_date:
            qs = qs.filter(quotation_date__lte=to_date)

        # sch_customer 필터
        sch_customer = request.GET.get('sch_customer', '')
        if sch_customer:
            qs = qs.filter(customer_id=sch_customer)

        # sch_status 필터
        sch_status = request.GET.get('sch_status', '')
        if sch_status == "대기":
            qs = qs.filter(status="대기")
        elif sch_status == "수주":
            qs = qs.filter(status="수주")
        elif sch_status == "만료":
            qs = qs.filter(status="만료")

        # url 바로가기용
        sch_id = request.GET.get('sch_id', '')
        if sch_id:
            qs = FactoryQuotation.objects.filter(id=sch_id, company=request_user.company)

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


class FactoryQuotation_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)

            status = request.POST.get('status', '')
            quotation_date = request.POST.get('quotation_date', None) or None
            request_date = request.POST.get('request_date', None) or None
            is_vat = request.POST.get('is_vat', '').lower() == 'true'
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')
            try:
                price = float(request.POST.get('price', '').strip())
            except (TypeError, ValueError):
                price = None

            customer = request.POST.get('customer', '')
            customer = int(customer) if customer.isdigit() else None
            approver = request.POST.get('approver', '')
            approver = int(approver) if approver.isdigit() else None

            item_data = json.loads(request.POST.get('itemData'))

            obj = FactoryQuotation.objects.create(
                code=get_quotation_code(request_user.company),
                customer_id=customer,
                approver_id=approver,
                is_vat=is_vat,
                price=price,
                quotation_date=quotation_date,
                request_date=request_date,
                desc1=desc1,
                desc2=desc2,
                status=status,

                created_by=request_user,
                updated_by=request_user,
                created_at=timezone.now().date(),
                updated_at=timezone.now().date(),
                company=request_user.company,
            )

            for data in item_data:
                item_id = data.get('item_id')
                item_id = int(item_id) if item_id.isdigit() else None
                total_qty = data.get('total_qty')
                unit_price = data.get('unit_price')
                total_price = data.get('total_price')
                desc1 = data.get('desc1')
                desc2 = data.get('desc2')
                item_code = data.get('item_code')
                item_name = data.get('item_name')
                item_desc1 = data.get('item_desc1')
                item_desc2 = data.get('item_desc2')
                item_desc3 = data.get('item_desc3')

                # 견적품목 생성
                obj_item = FactoryQuotationItem.objects.create(
                    quotation_id=obj.id,
                    item_id=item_id,

                    total_qty=total_qty,
                    unit_price=unit_price,
                    total_price=total_price,
                    desc1=desc1,
                    desc2=desc2,

                    item_code=item_code,
                    item_name=item_name,
                    item_desc1=item_desc1,
                    item_desc2=item_desc2,
                    item_desc3=item_desc3,

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


class FactoryQuotation_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            status = request.POST.get('status', '')
            quotation_date = request.POST.get('quotation_date', '')
            request_date = request.POST.get('request_date', '')
            is_vat = request.POST.get('is_vat', '').lower() == 'true'
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')
            try:
                price = float(request.POST.get('price', '').strip())
            except (TypeError, ValueError):
                price = None

            customer = request.POST.get('customer', '')
            customer = int(customer) if customer.isdigit() else None
            approver = request.POST.get('approver', '')
            approver = int(approver) if approver.isdigit() else None

            item_data = json.loads(request.POST.get('itemData'))

            obj = get_object_or_404(FactoryQuotation, pk=int(pk))

            obj.customer_id = customer
            obj.approver_id = approver
            obj.status = status
            obj.is_vat = is_vat
            obj.price = price
            obj.quotation_date = quotation_date
            obj.request_date = request_date
            obj.desc1 = desc1
            obj.desc2 = desc2

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            # 기존 발주품목 삭제 후 재생성
            exist_obj_items = FactoryQuotationItem.objects.filter(quotation=int(pk))
            if exist_obj_items:
                for exist_obj_item in exist_obj_items:
                    exist_obj_item.delete()

            for data in item_data:
                item_id = data.get('item_id')
                item_id = int(item_id) if item_id.isdigit() else None
                total_qty = data.get('total_qty')
                unit_price = data.get('unit_price')
                total_price = data.get('total_price')
                desc1 = data.get('desc1')
                desc2 = data.get('desc2')
                item_code = data.get('item_code')
                item_name = data.get('item_name')
                item_desc1 = data.get('item_desc1')
                item_desc2 = data.get('item_desc2')
                item_desc3 = data.get('item_desc3')

                # 견적품목 생성
                obj_item = FactoryQuotationItem.objects.create(
                    quotation_id=obj.id,
                    item_id=item_id,

                    total_qty=total_qty,
                    unit_price=unit_price,
                    total_price=total_price,
                    desc1=desc1,
                    desc2=desc2,

                    item_code=item_code,
                    item_name=item_name,
                    item_desc1=item_desc1,
                    item_desc2=item_desc2,
                    item_desc3=item_desc3,

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


# 견적 수주처리
class FactoryQuotation_Approve(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            # 견적서를 수주처리 후 주문서 복제 생성
            quotation_obj = get_object_or_404(FactoryQuotation, pk=int(pk))
            quotation_obj.status = "수주"
            quotation_obj.updated_by = request_user
            quotation_obj.updated_at = timezone.now()
            quotation_obj.save()

            customer_order_obj = FactoryCustomerOrder.objects.create(
                code=get_customer_order_code_from_quotation(quotation_obj.code, request_user.company),
                approver_id=quotation_obj.approver.id,
                delivery_user_id=quotation_obj.approver.id,
                customer_id=quotation_obj.customer.id,
                is_vat=quotation_obj.is_vat,
                price=quotation_obj.price,
                order_date=timezone.now().date(),
                request_date=quotation_obj.request_date,
                desc1=quotation_obj.desc1,
                desc2=quotation_obj.desc2,
                status="대기",

                created_by=request_user,
                updated_by=request_user,
                created_at=timezone.now().date(),
                updated_at=timezone.now().date(),
                company=request_user.company,
            )

            # 주문서 하위품목 생성
            quotation_items = FactoryQuotationItem.objects.filter(quotation=quotation_obj).select_related('item')

            for item in quotation_items:
                FactoryCustomerOrderItem.objects.create(
                    customer_order=customer_order_obj,
                    item=item.item,

                    total_qty=item.total_qty,
                    unit_price=item.unit_price,
                    total_price=item.total_price,
                    desc1=item.desc1,
                    desc2=item.desc2,

                    item_code=item.item_code,
                    item_name=item.item_name,
                    item_desc1=item.item_desc1,
                    item_desc2=item.item_desc2,
                    item_desc3=item.item_desc3,

                    created_by=request_user,
                    updated_by=request_user,
                    company=request_user.company
                )

            # 생산일정 캘린더 등록
            event_category = CodeMaster.objects.filter(group=CodeGroup.FACTORY_EVENT_CATEGORY, name="주문출하 일정",
                                                       is_default=True, company=request_user.company).first()

            order_items = FactoryCustomerOrderItem.objects.filter(customer_order=customer_order_obj.id).select_related(
                'item')
            order_item_desc = "-"
            if order_items.exists():
                item_list = []
                for row in order_items:
                    if row.item:
                        qty = row.total_qty
                        qty_display = int(qty) if qty == int(qty) else qty  # 정수면 int로, 아니면 그대로
                        item_list.append(f"{row.item.name}({qty_display})")
                order_item_desc = ", ".join(item_list)

            FactoryEvent.objects.create(
                customer_order=customer_order_obj,
                title=f"[{customer_order_obj.code}] {customer_order_obj.customer.name}",
                category=event_category,
                start_date=datetime.combine(customer_order_obj.order_date, time.min),
                end_date=datetime.combine(customer_order_obj.request_date, time(hour=23, minute=59)),
                event_url=f"/factory/sales/delivery_list/?sch_id={customer_order_obj.id}",
                desc=f"[발주품목] {order_item_desc}\n[특이사항] {customer_order_obj.desc1 or '-'}\n[요청사항] {customer_order_obj.desc2 or '-'}",
                created_by=request_user,
                updated_by=request_user,
                company=request_user.company,
            )

            # context = get_obj(obj)
            context = {'success': True}
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class FactoryQuotation_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(FactoryQuotation, pk=int(pk))
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
        'code': obj.code or '',
        'price': obj.price or '',
        'status': obj.status or '',
        'quotation_date': obj.quotation_date or '',
        'request_date': obj.request_date or '',
        'desc1': obj.desc1 or '',
        'desc2': obj.desc2 or '',
        'desc3': obj.desc3 or '',
        'is_vat': obj.is_vat,

        'customer_id': obj.customer.id if obj.customer is not None else '',
        'customer_name': obj.customer.name if obj.customer is not None else '',
        'customer_charge_name': obj.customer.charge_name if obj.customer is not None else '',
        'customer_mobile': obj.customer.mobile if obj.customer is not None else '',
        'customer_email': obj.customer.email if obj.customer is not None else '',
        'approver': get_user_info(obj.approver) if obj.approver else '',

        'created_by': get_user_info(obj.created_by) if obj.created_by else '',
        'updated_by': get_user_info(obj.updated_by) if obj.updated_by else '',
        'created_at': obj.created_at.strftime('%Y-%m-%d') if obj.created_at else '',
        'updated_at': obj.updated_at.strftime('%Y-%m-%d') if obj.updated_at else '',
        'company_id': obj.company.id if obj.company is not None else '',
        'company_name': obj.company.company_info.first().company_name if obj.company.company_info.exists() else '',
    }


class FactoryQuotationItem_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        quotation = request.GET.get('quotation', '')

        qs = FactoryQuotationItem.objects.filter(quotation=quotation, company=request_user.company).order_by('id')

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

        results = [get_obj_items(row) for row in qs_ps]

        context = {
            'count': qs_ps.paginator.count,
            'previous': url_pre,
            'next': url_next,
            'results': results,
        }

        return JsonResponse(context, safe=False)


def get_obj_items(obj):
    try:
        in_total_sum, in_faulty_sum, in_result_sum, out_result_sum, item_stock = get_item_stock(obj.item.id)
    except Exception:
        in_total_sum = in_faulty_sum = in_result_sum = out_result_sum = item_stock = 0

    return {
        'id': obj.id,
        'quotation_id': obj.quotation.id if obj.quotation is not None else '',
        'item_id': obj.item.id if obj.item is not None else '',
        'item_class': obj.item.item_class.name if obj.item and obj.item.item_class else '',
        'item_warehouse': obj.item.warehouse.id if obj.item and obj.item.warehouse else '',
        'total_qty': obj.total_qty or '',  # 품목 발주수량
        'unit_price': obj.unit_price or '',  # 발주단가
        'total_price': obj.total_price or '',  # 공급가액
        'desc1': obj.desc1 or '',  # 특이사항
        'desc2': obj.desc2 or '',  # 요청사항

        'in_total_sum': in_total_sum,
        'in_faulty_sum': in_faulty_sum,
        'in_result_sum': in_result_sum,
        'out_result_sum': out_result_sum,
        'item_stock': item_stock,

        'item_code': obj.item_code or '',
        'item_name': obj.item_name or '',
        'item_desc1': obj.item_desc1 or '',
        'item_desc2': obj.item_desc2 or '',
        'item_desc3': obj.item_desc3 or '',
    }
