from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, Max
from api.models import UserMaster, FactoryPurchase, FactoryPurchaseItem, FactoryEvent, CodeMaster, CodeGroup, FactoryItemIn
from api.lib import Pagenation, get_excep_msg
from django.utils import timezone
from api.factory.inventory_list import get_item_stock
from api.basic_data.notification import noti_create_fn
from datetime import datetime, time
from api.factory.factory_lib import get_itemin_code, get_purchase_code, get_user_info
import json


class FactoryPurchase_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')

        qs = FactoryPurchase.objects.filter(company=request_user.company).order_by('request_date', 'order_date')

        input_manage = request.GET.get('input_manage', '')
        if input_manage:
            qs = qs.filter(is_approved=True)

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
                        Q(purchase_order__item_code__icontains=keyword) |
                        Q(purchase_order__item_name__icontains=keyword) |
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

        # sch_is_approved 필터
        sch_is_approved = request.GET.get('sch_is_approved', '')
        if sch_is_approved == "미승인":
            qs = qs.filter(is_approved=0)
        elif sch_is_approved == "승인":
            qs = qs.filter(is_approved=1)

        # sch_status 필터
        sch_status = request.GET.get('sch_status', '')
        if sch_status == "진행":
            qs = qs.filter(Q(status="") | Q(status=None) | Q(status="진행"))
        elif sch_status == "완료":
            qs = qs.filter(status="완료")

        # url 바로가기
        sch_id = request.GET.get('sch_id', '')
        if sch_id:
            qs = FactoryPurchase.objects.filter(id=sch_id, company=request_user.company)

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


class FactoryPurchase_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)

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

            obj = FactoryPurchase.objects.create(
                code=get_purchase_code(request_user.company),
                customer_id=customer,
                approver_id=approver,
                is_vat=is_vat,
                price=price,
                order_date=order_date,
                request_date=request_date,
                desc1=desc1,
                desc2=desc2,

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
                item_code = data.get('item_code')
                item_name = data.get('item_name')
                item_desc1 = data.get('item_desc1')
                item_desc2 = data.get('item_desc2')
                item_desc3 = data.get('item_desc3')

                # 발주품목 생성
                obj_item = FactoryPurchaseItem.objects.create(
                    purchase_id=obj.id,
                    item_id=item_id,

                    total_qty=total_qty,
                    unit_price=unit_price,
                    total_price=total_price,

                    status="진행",
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

            # 알림센터 메세지 전송
            noti_create_fn(
                content=f"[{obj.code}] {obj.customer.name}의 구매발주서 결재 요청",
                user=obj.approver,
                url=f"/factory/purchase/list/?sch_id={obj.id}",
                noti_type="purchase_approval_request"
            )

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class FactoryPurchase_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

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

            obj = get_object_or_404(FactoryPurchase, pk=int(pk))

            obj.customer_id = customer
            obj.approver_id = approver
            obj.is_vat = is_vat
            obj.price = price
            obj.order_date = order_date
            obj.request_date = request_date
            obj.desc1 = desc1
            obj.desc2 = desc2

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            # 기존 발주품목 삭제 후 재생성
            exist_obj_items = FactoryPurchaseItem.objects.filter(purchase=int(pk))
            if exist_obj_items:
                for exist_obj_item in exist_obj_items:
                    exist_obj_item.delete()

            for data in item_data:
                item_id = data.get('item_id')
                item_id = int(item_id) if item_id.isdigit() else None
                total_qty = data.get('total_qty')
                unit_price = data.get('unit_price')
                total_price = data.get('total_price')
                item_code = data.get('item_code')
                item_name = data.get('item_name')
                item_desc1 = data.get('item_desc1')
                item_desc2 = data.get('item_desc2')
                item_desc3 = data.get('item_desc3')

                # 발주품목 생성
                obj_item = FactoryPurchaseItem.objects.create(
                    purchase_id=obj.id,
                    item_id=item_id,

                    total_qty=total_qty,
                    unit_price=unit_price,
                    total_price=total_price,

                    status="진행",
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


class FactoryPurchase_Approve(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            obj = get_object_or_404(FactoryPurchase, pk=int(pk))

            if obj.approver_id != request_user.id:
                return JsonResponse({"error": True, "message": "[결재 승인자] 가 아닙니다."})

            obj.is_approved = True

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            # 알림센터 메세지 전송
            noti_create_fn(
                content=f"[{obj.code}] {obj.customer.name}의 구매발주서 결재 승인",
                user=obj.created_by,
                url=f"/factory/purchase/list/?sch_id={obj.id}",
                noti_type="purchase_approval_approved"
            )

            # 생산일정 캘린더 등록
            event_category = CodeMaster.objects.filter(group=CodeGroup.FACTORY_EVENT_CATEGORY, name="발주입고 일정",
                                                       is_default=True, company=request_user.company).first()

            purchase_items = FactoryPurchaseItem.objects.filter(purchase=obj.id).select_related('item')
            order_item_desc = "-"
            if purchase_items.exists():
                item_list = []
                for row in purchase_items:
                    if row.item:
                        qty = row.total_qty
                        qty_display = int(qty) if qty == int(qty) else qty  # 정수면 int로, 아니면 그대로
                        item_list.append(f"{row.item.name}({qty_display})")
                order_item_desc = ", ".join(item_list)

            FactoryEvent.objects.create(
                purchase=obj,
                title=f"[{obj.code}] {obj.customer.name}",
                category=event_category,
                start_date=datetime.combine(obj.order_date, time.min),
                end_date=datetime.combine(obj.request_date, time(hour=23, minute=59)),
                event_url=f"/factory/purchase/input/?sch_id={obj.id}",
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


class FactoryPurchase_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(FactoryPurchase, pk=int(pk))
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
        'receive_date': obj.receive_date or '',
        'desc1': obj.desc1 or '',
        'desc2': obj.desc2 or '',
        'desc3': obj.desc3 or '',
        'is_approved': obj.is_approved,
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



class FactoryPurchaseItem_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        purchase = request.GET.get('purchase', '')

        qs = FactoryPurchaseItem.objects.filter(purchase=purchase, company=request_user.company).order_by('id')

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


class FactoryPurchaseItem_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            status = request.POST.get('status', '')
            receive_total_price = request.POST.get('receive_total_price', '')
            item_data = json.loads(request.POST.get('itemData'))

            obj = get_object_or_404(FactoryPurchase, pk=int(pk))

            # 이미 완료된 발주서 수정 방지
            if obj.status == "완료":
                return JsonResponse({"error": True, "message": "이미 입고상태가 완료된 발주서입니다."})

            obj.status = status
            obj.receive_total_price = receive_total_price

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            # 기존 발주품목 수정
            for data in item_data:
                row_id = data.get('row_id')
                try:
                    obj_item = FactoryPurchaseItem.objects.get(id=row_id)
                except FactoryPurchaseItem.DoesNotExist:
                    continue

                # 업데이트할 필드만 지정
                obj_item.receive_date = data.get('receive_date') or None
                obj_item.receive_qty = data.get('receive_qty') or None
                obj_item.faulty_qty = data.get('faulty_qty') or None
                obj_item.result_qty = data.get('result_qty') or None
                obj_item.receive_price = data.get('receive_price') or None
                obj_item.receive_total_price = data.get('receive_total_price') or None
                obj_item.warehouse_id = data.get('warehouse') or None

                obj_item.updated_by = request_user
                obj_item.updated_at = timezone.now()
                obj_item.save()

            # 가장 나중의 receive_date로 obj.receive_date 설정
            latest_receive_date = FactoryPurchaseItem.objects.filter(purchase=obj).aggregate(
                latest=Max('receive_date')
            )['latest']
            if latest_receive_date:
                obj.receive_date = latest_receive_date
            obj.save()

            # status가 완료일 경우, 재고입고 등록
            if obj.status == "완료":
                for data in item_data:
                    row_id = data.get('row_id')
                    try:
                        obj_item = FactoryPurchaseItem.objects.get(id=row_id)
                    except FactoryPurchaseItem.DoesNotExist:
                        continue

                    FactoryItemIn.objects.create(
                        code=get_itemin_code(request_user.company),
                        date=obj_item.receive_date,
                        desc1=f"발주입고 ({obj.code})",
                        desc2=obj.desc1,
                        total_amount=obj_item.receive_qty,
                        faulty_amount=obj_item.faulty_qty,
                        result_amount=obj_item.result_qty,
                        price=obj_item.receive_price,

                        item_id=obj_item.item_id,
                        warehouse_id=obj_item.warehouse_id,
                        customer_id=obj.customer.id,
                        purchase_id=obj.id,

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
        'purchase_id': obj.purchase.id if obj.purchase is not None else '',
        'item_id': obj.item.id if obj.item is not None else '',
        'item_class': obj.item.item_class.name if obj.item.item_class is not None else '',
        'item_warehouse': obj.item.warehouse.id if obj.item.warehouse is not None else '',
        'unit_price': obj.unit_price or '',  # 발주단가
        'total_price': obj.total_price or '',  # 공급가액
        'total_qty': obj.total_qty or '',  # 품목 발주수량
        'desc1': obj.desc1 or '',  # 특이사항
        'desc2': obj.desc2 or '',  # 요청사항

        'status': obj.status or '',  # 발주입고 상태
        'receive_date': obj.receive_date or '',  # 입하날짜
        'receive_qty': obj.receive_qty or '',  # 입하수량
        'faulty_qty': obj.faulty_qty or '',  # 입하중 불량수량
        'result_qty': obj.result_qty or '',  # 최종입고수량
        'receive_price': obj.receive_price or '',  # 최종입고금액
        'receive_total_price': obj.receive_total_price or '',  # 최종입고 공급가액
        'receive_warehouse': obj.warehouse.id if obj.warehouse is not None else '',

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