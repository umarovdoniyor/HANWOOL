from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, OuterRef, Subquery, Max
from api.models import UserMaster, CompanyAsset, AssetHistory, FactoryItem, FactoryBomStructure, FactoryProStructure
from api.lib import Pagenation, get_excep_msg
from datetime import datetime, date
from collections import defaultdict
from django.utils import timezone
from api.factory.inventory_list import get_item_stock
from api.factory.factory_lib import get_item_code


class FactoryItem_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')

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
        sch_code = request.GET.get('sch_code', '')
        if sch_code:
            qs = qs.filter(id=sch_code)

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

        results = [get_obj(row) for row in qs_ps]

        context = {
            'count': qs_ps.paginator.count,
            'previous': url_pre,
            'next': url_next,
            'results': results,
        }

        return JsonResponse(context, safe=False)


class FactoryItem_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)

            code = request.POST.get('code', '')
            name = request.POST.get('name', '')
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')
            desc3 = request.POST.get('desc3', '')
            buy_price = request.POST.get('buy_price', None) or None
            sell_price = request.POST.get('sell_price', None) or None
            std_cost = request.POST.get('std_cost', None) or None
            moq = request.POST.get('moq', None) or None
            safety_stock = request.POST.get('safety_stock', None) or None
            is_valid = request.POST.get('is_valid', '').lower() == 'true'
            img = request.FILES.get('img', None)
            doc = request.FILES.get('doc', None)

            unit = request.POST.get('unit', '')
            unit = int(unit) if unit.isdigit() else None
            item_class = request.POST.get('item_class', '')
            item_class = int(item_class) if item_class.isdigit() else None
            warehouse = request.POST.get('warehouse', '')
            warehouse = int(warehouse) if warehouse.isdigit() else None
            supplier = request.POST.get('supplier', '')
            supplier = int(supplier) if supplier.isdigit() else None

            # qr_code = request.POST.get('qr_code', '')

            if not code:
                code = get_item_code(request_user.company)

            obj = FactoryItem.objects.create(
                code=code,
                name=name,
                desc1=desc1,
                desc2=desc2,
                desc3=desc3,
                buy_price=buy_price,
                sell_price=sell_price,
                std_cost=std_cost,
                moq=moq,
                safety_stock=safety_stock,
                is_valid=is_valid,
                img=img,
                doc=doc,
                # qr_code=qr_code,

                unit_id=unit,
                item_class_id=item_class,
                warehouse_id=warehouse,
                supplier_id=supplier,

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


class FactoryItem_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            code = request.POST.get('code', '')
            name = request.POST.get('name', '')
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')
            desc3 = request.POST.get('desc3', '')
            buy_price = request.POST.get('buy_price', None) or None
            sell_price = request.POST.get('sell_price', None) or None
            std_cost = request.POST.get('std_cost', None) or None
            moq = request.POST.get('moq', None) or None
            safety_stock = request.POST.get('safety_stock', None) or None
            is_valid = request.POST.get('is_valid', '').lower() == 'true'
            img = request.FILES.get('img', None)
            img_clear = request.POST.get('img_clear', 'false') == 'true'
            doc = request.FILES.get('doc', None)
            doc_clear = request.POST.get('doc_clear', 'false') == 'true'

            unit = request.POST.get('unit', '')
            unit = int(unit) if unit.isdigit() else None
            item_class = request.POST.get('item_class', '')
            item_class = int(item_class) if item_class.isdigit() else None
            warehouse = request.POST.get('warehouse', '')
            warehouse = int(warehouse) if warehouse.isdigit() else None
            supplier = request.POST.get('supplier', '')
            supplier = int(supplier) if supplier.isdigit() else None

            # qr_code = request.POST.get('qr_code', '')

            if not code:
                code = get_item_code(request_user.company)

            obj = get_object_or_404(FactoryItem, pk=int(pk))

            obj.code = code
            obj.name = name
            obj.desc1 = desc1
            obj.desc2 = desc2
            obj.desc3 = desc3
            obj.buy_price = buy_price
            obj.sell_price = sell_price
            obj.std_cost = std_cost
            obj.moq = moq
            obj.safety_stock = safety_stock
            obj.is_valid = is_valid
            # obj.qr_code = qr_code

            obj.unit_id = unit
            obj.item_class_id = item_class
            obj.warehouse_id = warehouse
            obj.supplier_id = supplier

            if img_clear and obj.img:
                obj.img.delete(save=False)
                obj.img = None
            if img:
                obj.img = img

            if doc_clear and obj.doc:
                obj.doc.delete(save=False)
                obj.doc = None
            if doc:
                obj.doc = doc

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class FactoryItem_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(FactoryItem, pk=int(pk))
            if obj.img:
                obj.img.delete(save=False)
            if obj.doc:
                obj.doc.delete(save=False)
            obj.delete()

            context = {'success': True}
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


def get_obj(obj):
    have_bom = FactoryBomStructure.objects.filter(parent_item=obj.id).exists()
    have_pro = FactoryProStructure.objects.filter(item=obj.id).exists()

    try:
        in_total_sum, in_faulty_sum, in_result_sum, out_result_sum, item_stock = get_item_stock(obj.id)
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

        'have_bom': have_bom,
        'have_pro': have_pro,
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

        'created_by': get_user_info(obj.created_by) if obj.created_by else '',
        'updated_by': get_user_info(obj.updated_by) if obj.updated_by else '',
        'created_at': obj.created_at.strftime('%Y-%m-%d') if obj.created_at else '',
        'updated_at': obj.updated_at.strftime('%Y-%m-%d') if obj.updated_at else '',
        'company_id': obj.company.id if obj.company is not None else '',
        'company_name': obj.company.company_info.first().company_name if obj.company.company_info.exists() else '',
    }


def get_user_info(user):
    return {
        'id': user.id,
        'name': user.name,
        'profile_image': user.profile_image.url if user.profile_image and user.profile_image.name else '',
        'team': user.team.name if user.team else '',
        'job_level': user.job_level.name if user.job_level else '',
    }