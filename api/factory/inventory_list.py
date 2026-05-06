from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, OuterRef, Subquery, Max, Sum
from api.models import UserMaster, FactoryItemIn, FactoryItemOut, FactoryItem, CodeMaster, CodeGroup
from api.lib import Pagenation, get_excep_msg, tof
from django.utils import timezone
from api.factory.factory_lib import get_itemin_code, get_itemout_code


class InventoryList_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')

        qs = FactoryItem.objects.filter(company=request_user.company).order_by('code')

        # 사용여부 필터
        sch_is_valid = request.GET.get('sch_is_valid', '')
        if sch_is_valid == "true":
            qs = qs.filter(is_valid=True)
        elif sch_is_valid == "false":
            qs = qs.filter(is_valid=False)

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
                            Q(code__icontains=keyword) |
                            Q(desc1__icontains=keyword) |
                            Q(desc2__icontains=keyword) |
                            Q(desc3__icontains=keyword) |
                            Q(supplier__name__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        # item_code 필터
        sch_item = request.GET.get('sch_item', '')
        if sch_item:
            qs = qs.filter(id=sch_item)

        # item_class 필터
        sch_item_class = request.GET.get('sch_item_class', '')
        if sch_item_class:
            qs = qs.filter(item_class_id=sch_item_class)

        # item_select로 특정 아이템 호출
        item_select = request.GET.get('item_select', '')
        if item_select:
            qs = FactoryItem.objects.filter(id=item_select, company=request_user.company)

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

        results = [get_obj(row, fr_date, to_date) for row in qs_ps]

        context = {
            'count': qs_ps.paginator.count,
            'previous': url_pre,
            'next': url_next,
            'results': results,
        }

        return JsonResponse(context, safe=False)


class InventoryTransfer_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)

            item = request.POST.get('item', '')
            date = request.POST.get('date', '')
            transfer_amount = request.POST.get('transfer_amount', None) or None
            remark = request.POST.get('remark', '')

            warehouse_from = request.POST.get('warehouse_from', '')
            warehouse_from = get_object_or_404(CodeMaster, id=warehouse_from)
            warehouse_to = request.POST.get('warehouse_to', '')
            warehouse_to = get_object_or_404(CodeMaster, id=warehouse_to)
            desc1 = f"창고이동 ({warehouse_from.name} → {warehouse_to.name})"

            # 창고이동 : 입고등록
            obj_in = FactoryItemIn.objects.create(
                code=get_itemin_code(request_user.company),
                date=date,
                desc1=desc1,
                desc2=remark,
                warehouse_transfer=True,
                total_amount=transfer_amount,
                faulty_amount=None,
                result_amount=transfer_amount,
                price=None,

                item_id=item,
                warehouse=warehouse_to,
                customer_id=None,

                created_by=request_user,
                updated_by=request_user,
                created_at=timezone.now().date(),
                updated_at=timezone.now().date(),
                company=request_user.company,
            )

            # 창고이동 : 출고등록
            obj_out = FactoryItemOut.objects.create(
                code=get_itemout_code(request_user.company),
                date=date,
                desc1=desc1,
                desc2=remark,
                warehouse_transfer=True,
                total_amount=transfer_amount,
                faulty_amount=None,
                result_amount=transfer_amount,
                price=None,

                item_id=item,
                warehouse=warehouse_from,
                faulty_class_id=None,
                customer_id=None,

                created_by=request_user,
                updated_by=request_user,
                created_at=timezone.now().date(),
                updated_at=timezone.now().date(),
                company=request_user.company,
            )

            context = {'success': True}
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


def get_obj(obj, fr_date=None, to_date=None):
    try:
        in_total_sum, in_faulty_sum, in_result_sum, out_result_sum, item_stock = get_item_stock(obj.id, fr_date, to_date)
    except Exception:
        in_total_sum = in_faulty_sum = in_result_sum = out_result_sum = item_stock = 0

    return {
        'id': obj.id,
        'name': obj.name or '',
        'code': obj.code or '',
        'desc1': obj.desc1 or '',
        'desc2': obj.desc2 or '',
        'desc3': obj.desc3 or '',
        'safety_stock': obj.safety_stock or '',
        'moq': obj.moq or '',
        'buy_price': obj.buy_price or 0,
        'sell_price': obj.sell_price or 0,
        'std_cost': obj.std_cost or 0,
        # 'qr_code': obj.qr_code or 0,
        'is_valid': obj.is_valid,
        'img': obj.img.url if obj.img and obj.img.name else '',
        'doc_url': obj.doc.url if obj.doc and obj.doc.name else '',
        'doc_name': obj.doc.name if obj.doc and obj.doc.name else '',

        'in_total_sum': in_total_sum,
        'in_faulty_sum': in_faulty_sum,
        'in_result_sum': in_result_sum,
        'out_result_sum': out_result_sum,
        'item_stock': item_stock,

        'unit_id': obj.unit.id if obj.unit is not None else '',
        'unit_name': obj.unit.name if obj.unit is not None else '',
        'item_class_id': obj.item_class.id if obj.item_class is not None else '',
        'item_class_name': obj.item_class.name if obj.item_class is not None else '',
        'warehouse_id': obj.warehouse.id if obj.warehouse is not None else '',
        'warehouse_name': obj.warehouse.name if obj.warehouse is not None else '',
        'supplier_id': obj.supplier.id if obj.supplier is not None else '',
        'supplier_name': obj.supplier.name if obj.supplier is not None else '',
    }


def get_item_stock(item_id, fr_date=None, to_date=None):
    item = get_object_or_404(FactoryItem, id=item_id)

    in_qs = FactoryItemIn.objects.only('total_amount', 'faulty_amount', 'result_amount').filter(item=item).exclude(warehouse_transfer=True).select_related('item')
    if fr_date:
        in_qs = in_qs.filter(date__gte=fr_date)
    if to_date:
        in_qs = in_qs.filter(date__lte=to_date)
    in_total_dict = in_qs.aggregate(Sum('total_amount'))
    in_total_sum = tof(in_total_dict['total_amount__sum'] or 0, 2)  # 입고/입하수량 합
    in_faulty_dict = in_qs.aggregate(Sum('faulty_amount'))
    in_faulty_sum = tof(in_faulty_dict['faulty_amount__sum'] or 0, 2)  # 입고/불량수량 합
    in_result_dict = in_qs.aggregate(Sum('result_amount'))
    in_result_sum = tof(in_result_dict['result_amount__sum'] or 0, 2)  # 입고/입고수량 합

    out_qs = FactoryItemOut.objects.only('result_amount').filter(item=item).exclude(warehouse_transfer=True).select_related('item')
    if fr_date:
        out_qs = out_qs.filter(date__gte=fr_date)
    if to_date:
        out_qs = out_qs.filter(date__lte=to_date)
    out_result_dict = out_qs.aggregate(Sum('result_amount'))
    out_result_sum = tof(out_result_dict['result_amount__sum'] or 0, 2)  # 출고/출고수량 합

    # 현재고 = 입고수량 - 출고수량
    item_stock = tof((in_result_sum - out_result_sum) or 0, 2)

    return in_total_sum, in_faulty_sum, in_result_sum, out_result_sum, item_stock


# 특정 품목의 창고별 (혹은 특정창고) 재고 호출 (예시 : /factory_warehouse_list_read_fn/?item_id=4&warehouse_id=695)
class WarehouseList_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')

        item_id = request.GET.get("item_id", '')
        item_id = int(item_id) if item_id.isdigit() else None
        warehouse_id = request.GET.get("warehouse_id", '')
        warehouse_id = int(warehouse_id) if warehouse_id.isdigit() else None

        qs = CodeMaster.objects.filter(group=CodeGroup.FACTORY_WAREHOUSE, company=request_user.company).order_by('name')

        if warehouse_id:
            qs = qs.filter(id=warehouse_id)

        results = []
        for warehouse in qs:
            in_qs = FactoryItemIn.objects.filter(item_id=item_id, warehouse_id=warehouse.id)
            if fr_date:
                in_qs = in_qs.filter(date__gte=fr_date)
            if to_date:
                in_qs = in_qs.filter(date__lte=to_date)
            in_total_sum = sum(row.total_amount or 0 for row in in_qs)
            in_faulty_sum = sum(row.faulty_amount or 0 for row in in_qs)
            in_result_sum = sum(row.result_amount or 0 for row in in_qs)

            out_qs = FactoryItemOut.objects.filter(item_id=item_id, warehouse_id=warehouse.id)
            if fr_date:
                out_qs = out_qs.filter(date__gte=fr_date)
            if to_date:
                out_qs = out_qs.filter(date__lte=to_date)
            out_result_sum = sum(row.result_amount or 0 for row in out_qs)

            item_stock = in_result_sum - out_result_sum

            all_in_total_sum, all_in_faulty_sum, all_in_result_sum, all_out_result_sum, all_item_stock = get_item_stock(item_id)

            results.append({
                'warehouse_id': warehouse.id,
                'warehouse_name': warehouse.name,
                'warehouse_in_total_sum': tof(in_total_sum, 2),
                'warehouse_in_faulty_sum': tof(in_faulty_sum, 2),
                'warehouse_in_result_sum': tof(in_result_sum, 2),
                'warehouse_out_result_sum': tof(out_result_sum, 2),
                'warehouse_item_stock': tof(item_stock, 2),
                'all_item_stock': tof(all_item_stock, 2),
            })

            # 현재고 순서로 정렬
            results.sort(key=lambda x: x['warehouse_item_stock'], reverse=True)

            exist = request.GET.get('exist', '')
            if exist:
                results = [row for row in results if row['warehouse_item_stock'] != 0]

        return JsonResponse({'results': results}, safe=False)
