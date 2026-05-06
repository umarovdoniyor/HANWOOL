from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, Sum
from api.models import UserMaster, FactoryEvent, CodeMaster, CodeGroup, FactoryItemIn, FactoryItemOut, \
    FactoryCustomerOrder, FactoryCustomerOrderItem
from api.lib import Pagenation, get_excep_msg
from django.utils import timezone
from api.factory.inventory_list import get_item_stock
from api.basic_data.notification import noti_create_fn
from datetime import datetime, time, date
from api.factory.factory_lib import get_itemin_code, get_itemout_code, get_production_code, get_user_info, \
    get_item_info, fk_int, get_customer_order_code
import json


class FactoryCustomerOrder_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')

        qs = FactoryCustomerOrder.objects.filter(company=request_user.company).order_by('request_date', 'order_date')

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
                        Q(customer_order__item_code__icontains=keyword) |
                        Q(customer_order__item_name__icontains=keyword) |
                        Q(desc1__icontains=keyword) |
                        Q(desc2__icontains=keyword) |
                        Q(desc3__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        # 기간 검색
        if fr_date:
            qs = qs.filter(order_date__gte=fr_date)
        if to_date:
            qs = qs.filter(order_date__lte=to_date)

        # 납기 검색
        fr_req_date = request.GET.get('fr_req_date', '')
        to_req_date = request.GET.get('to_req_date', '')
        if fr_req_date:
            qs = qs.filter(request_date__gte=fr_req_date)
        if to_req_date:
            qs = qs.filter(request_date__lte=to_req_date)

        # sch_customer 필터
        sch_customer = request.GET.get('sch_customer', '')
        if sch_customer:
            qs = qs.filter(customer_id=sch_customer)

        # sch_status 필터
        sch_status = request.GET.get('sch_status', '')
        if sch_status == "진행":
            qs = qs.filter(status="진행")
        elif sch_status == "대기":
            qs = qs.filter(status="대기")
        elif sch_status == "대기/진행":
            qs = qs.filter(status__in=["대기", "진행"])
        elif sch_status == "완료":
            qs = qs.filter(status="완료")
        elif sch_status == "보류":
            qs = qs.filter(status="보류")

        # url 바로가기
        sch_id = request.GET.get('sch_id', '')
        if sch_id:
            qs = FactoryCustomerOrder.objects.filter(id=sch_id, company=request_user.company)

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


class FactoryCustomerOrder_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)

            status = request.POST.get('status', '')
            order_date = request.POST.get('order_date', None) or None
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

            obj = FactoryCustomerOrder.objects.create(
                code=get_customer_order_code(request_user.company),
                customer_id=customer,
                approver_id=approver,
                is_vat=is_vat,
                price=price,
                order_date=order_date,
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
                obj_item = FactoryCustomerOrderItem.objects.create(
                    customer_order_id=obj.id,
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

            # 출하 일정 캘린더 등록
            event_category = CodeMaster.objects.filter(group=CodeGroup.FACTORY_EVENT_CATEGORY, name="주문출하 일정",
                                                       is_default=True, company=request_user.company).first()

            order_items = FactoryCustomerOrderItem.objects.filter(
                customer_order=obj.id).select_related(
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
                customer_order=obj,
                title=f"[{obj.code}] {obj.customer.name}",
                category=event_category,
                start_date=datetime.combine(datetime.strptime(str(obj.order_date), "%Y-%m-%d").date(), time.min),
                end_date=datetime.combine(datetime.strptime(str(obj.request_date), "%Y-%m-%d").date(), time(hour=23, minute=59)),
                event_url=f"/factory/sales/delivery_list/?sch_id={obj.id}",
                desc=f"[발주품목] {order_item_desc}\n[특이사항] {obj.desc1 or '-'}\n[요청사항] {obj.desc2 or '-'}",
                created_by=request_user,
                updated_by=request_user,
                company=request_user.company,
            )

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class FactoryCustomerOrder_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            status = request.POST.get('status', '')
            order_date = request.POST.get('order_date', None) or None
            request_date = request.POST.get('request_date', None) or None
            delivery_date = request.POST.get('delivery_date', None) or None
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

            obj = get_object_or_404(FactoryCustomerOrder, pk=int(pk))

            obj.customer_id = customer
            obj.approver_id = approver
            obj.status = status
            obj.is_vat = is_vat
            obj.price = price
            obj.order_date = order_date
            obj.request_date = request_date
            obj.delivery_date = delivery_date
            obj.desc1 = desc1
            obj.desc2 = desc2

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            # 기존 주문품목 삭제 후 재생성
            exist_obj_items = FactoryCustomerOrderItem.objects.filter(customer_order=int(pk))
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
                obj_item = FactoryCustomerOrderItem.objects.create(
                    customer_order_id=obj.id,
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

            # 출하 일정 캘린더 수정
            order_items = FactoryCustomerOrderItem.objects.filter(
                customer_order=obj.id).select_related(
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

            event_obj = FactoryEvent.objects.filter(customer_order_id=obj.id).first()
            if event_obj:
                event_obj.title = f"[{obj.code}] {obj.customer.name}"
                event_obj.start_date = datetime.combine(datetime.strptime(str(obj.order_date), "%Y-%m-%d").date(),
                                                        time.min)
                event_obj.end_date = datetime.combine(datetime.strptime(str(obj.request_date), "%Y-%m-%d").date(),
                                                      time(hour=23, minute=59))
                event_obj.event_url = f"/factory/sales/delivery_list/?sch_id={obj.id}"
                event_obj.desc = f"[발주품목] {order_item_desc}\n[특이사항] {obj.desc1 or '-'}\n[요청사항] {obj.desc2 or '-'}"
                event_obj.updated_by = request_user
                event_obj.company = request_user.company
                event_obj.save()

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


# 출하 완료처리
class FactoryCustomerOrder_Approve(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            obj = get_object_or_404(FactoryCustomerOrder, pk=int(pk))
            order_items = FactoryCustomerOrderItem.objects.filter(customer_order=obj)

            # 재고출고 등록
            for order_item in order_items:
                total_qty = order_item.total_qty or 0

                FactoryItemOut.objects.create(
                    code=get_itemout_code(request_user.company),
                    date=obj.delivery_date,
                    desc1=f"주문출하 출고 ({obj.code})",
                    desc2=obj.desc1,
                    total_amount=total_qty,
                    faulty_amount=0,
                    result_amount=total_qty,
                    price=order_item.unit_price or 0,

                    customer=obj.customer,
                    item=order_item.item,
                    warehouse=order_item.warehouse,
                    customer_order=obj,
                    customer_order_item=order_item,

                    created_by=request_user,
                    updated_by=request_user,
                    created_at=timezone.now().date(),
                    updated_at=timezone.now().date(),
                    company=request_user.company,
                )

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            context = {'success': True}
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class FactoryCustomerOrder_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(FactoryCustomerOrder, pk=int(pk))
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
        'order_date': obj.order_date or '',
        'request_date': obj.request_date or '',
        'delivery_date': obj.delivery_date or '',
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
        'delivery_user': get_user_info(obj.delivery_user) if obj.delivery_user else '',

        'created_by': get_user_info(obj.created_by) if obj.created_by else '',
        'updated_by': get_user_info(obj.updated_by) if obj.updated_by else '',
        'created_at': obj.created_at.strftime('%Y-%m-%d') if obj.created_at else '',
        'updated_at': obj.updated_at.strftime('%Y-%m-%d') if obj.updated_at else '',
        'company_id': obj.company.id if obj.company is not None else '',
        'company_name': obj.company.company_info.first().company_name if obj.company.company_info.exists() else '',
    }



class FactoryCustomerOrderItem_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        customer_order = request.GET.get('customer_order', '')

        qs = FactoryCustomerOrderItem.objects.filter(customer_order=customer_order, company=request_user.company).order_by('id')

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


# 출하현황 등록
class FactoryCustomerOrderItem_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            status = request.POST.get('status', '')
            delivery_date = request.POST.get('delivery_date') or None
            delivery_user = request.POST.get('delivery_user', '')
            delivery_user = int(delivery_user) if delivery_user.isdigit() else None

            item_data = json.loads(request.POST.get('itemData'))

            obj = get_object_or_404(FactoryCustomerOrder, pk=int(pk))

            # 이미 완료된 주문서 수정 방지
            if obj.status == "완료":
                return JsonResponse({"error": True, "message": "이미 출하 상태가 완료된 주문서입니다."})

            obj.status = status
            obj.delivery_user_id = delivery_user
            obj.delivery_date = delivery_date or date.today()

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            # 기존 발주품목 수정
            for data in item_data:
                row_id = data.get('row_id')
                try:
                    obj_item = FactoryCustomerOrderItem.objects.get(id=row_id)
                except FactoryCustomerOrderItem.DoesNotExist:
                    continue

                # 업데이트할 필드만 지정
                obj_item.delivery_date = data.get('delivery_date') or date.today()
                obj_item.delivery_qty = data.get('delivery_qty') or None
                obj_item.warehouse_id = data.get('warehouse') or None
                obj_item.desc1 = data.get('desc1') or None

                obj_item.updated_by = request_user
                obj_item.updated_at = timezone.now()
                obj_item.save()

            # status가 완료일 경우, 재고출고 등록
            if obj.status == "완료":
                for data in item_data:
                    row_id = data.get('row_id')
                    try:
                        obj_item = FactoryCustomerOrderItem.objects.get(id=row_id)
                    except FactoryCustomerOrderItem.DoesNotExist:
                        continue

                    FactoryItemOut.objects.create(
                        code=get_itemout_code(request_user.company),
                        date=obj.delivery_date,
                        desc1=f"주문출하 출고 ({obj.code})",
                        desc2=obj.desc1,
                        total_amount=obj_item.delivery_qty,
                        faulty_amount=0,
                        result_amount=obj_item.delivery_qty,
                        price=obj_item.unit_price,

                        item_id=obj_item.item_id,
                        warehouse_id=obj_item.warehouse_id,
                        customer_id=obj.customer.id,
                        customer_order_id=obj.id,

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


def get_obj_items(obj):
    try:
        in_total_sum, in_faulty_sum, in_result_sum, out_result_sum, item_stock = get_item_stock(obj.item.id)
    except Exception:
        in_total_sum = in_faulty_sum = in_result_sum = out_result_sum = item_stock = 0

    return {
        'id': obj.id,
        'customer_order_id': obj.customer_order.id if obj.customer_order is not None else '',
        'item_id': obj.item.id if obj.item is not None else '',
        'item_class': obj.item.item_class.name if obj.item.item_class is not None else '',
        'item_warehouse': obj.item.warehouse.id if obj.item.warehouse is not None else '',
        'total_qty': obj.total_qty or '',
        'unit_price': obj.unit_price or '',
        'total_price': obj.total_price or '',
        'desc1': obj.desc1 or '',
        'desc2': obj.desc2 or '',

        'delivery_date': obj.delivery_date or '',
        'delivery_qty': obj.delivery_qty or '',
        'warehouse_id': obj.warehouse.id if obj.warehouse is not None else '',
        'warehouse_name': obj.warehouse.name if obj.warehouse is not None else '',

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