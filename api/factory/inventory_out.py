from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, OuterRef, Subquery, Max
from api.models import UserMaster, FactoryItemOut
from api.lib import Pagenation, get_excep_msg
from django.utils import timezone
from api.factory.factory_lib import get_itemout_code


class InventoryOut_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')

        qs = FactoryItemOut.objects.filter(company=request_user.company).order_by('-date', '-created_at')

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
                        Q(customer__name__icontains=keyword) |
                        Q(warehouse__name__icontains=keyword) |
                        Q(item__desc1__icontains=keyword) |
                        Q(item__desc2__icontains=keyword) |
                        Q(item__desc3__icontains=keyword) |
                        Q(item__item_class__name__icontains=keyword) |
                        Q(faulty_class__name__icontains=keyword) |
                        Q(desc1__icontains=keyword) |
                        Q(desc2__icontains=keyword) |
                        Q(desc3__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        # 기간 검색
        if fr_date:
            qs = qs.filter(date__gte=fr_date)
        if to_date:
            qs = qs.filter(date__lte=to_date)

        # item_code 필터
        sch_item = request.GET.get('sch_item', '')
        if sch_item:
            qs = qs.filter(item_id=sch_item)

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


class InventoryOut_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)

            code = request.POST.get('code', '')
            date = request.POST.get('date', '')
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')
            desc3 = request.POST.get('desc3', '')
            total_amount = request.POST.get('total_amount', None) or None
            faulty_amount = request.POST.get('faulty_amount', None) or None
            result_amount = request.POST.get('result_amount', None) or None
            price = request.POST.get('price', None) or None

            item = request.POST.get('item', '')
            item = int(item) if item.isdigit() else None
            warehouse = request.POST.get('warehouse', '')
            warehouse = int(warehouse) if warehouse.isdigit() else None
            faulty_class = request.POST.get('faulty_class', '')
            faulty_class = int(faulty_class) if faulty_class.isdigit() else None
            customer = request.POST.get('customer', '')
            customer = int(customer) if customer.isdigit() else None

            if not code:
                code = get_itemout_code(request_user.company)

            obj = FactoryItemOut.objects.create(
                code=code,
                date=date,
                desc1=desc1,
                desc2=desc2,
                desc3=desc3,
                total_amount=total_amount,
                faulty_amount=faulty_amount,
                result_amount=result_amount,
                price=price,

                item_id=item,
                warehouse_id=warehouse,
                faulty_class_id=faulty_class,
                customer_id=customer,

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


class InventoryOut_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            code = request.POST.get('code', '')
            date = request.POST.get('date', '')
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')
            desc3 = request.POST.get('desc3', '')
            total_amount = request.POST.get('total_amount', None) or None
            faulty_amount = request.POST.get('faulty_amount', None) or None
            result_amount = request.POST.get('result_amount', None) or None
            price = request.POST.get('price', None) or None

            item = request.POST.get('item', '')
            item = int(item) if item.isdigit() else None
            warehouse = request.POST.get('warehouse', '')
            warehouse = int(warehouse) if warehouse.isdigit() else None
            faulty_class = request.POST.get('faulty_class', '')
            faulty_class = int(faulty_class) if faulty_class.isdigit() else None
            customer = request.POST.get('customer', '')
            customer = int(customer) if customer.isdigit() else None

            if not code:
                code = get_itemout_code(request_user.company)

            obj = get_object_or_404(FactoryItemOut, pk=int(pk))

            obj.code = code
            obj.date = date
            obj.desc1 = desc1
            obj.desc2 = desc2
            obj.desc3 = desc3
            obj.total_amount = total_amount
            obj.faulty_amount = faulty_amount
            obj.result_amount = result_amount
            obj.price = price

            obj.item_id = item
            obj.warehouse_id = warehouse
            obj.faulty_class_id = faulty_class
            obj.customer_id = customer

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class InventoryOut_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(FactoryItemOut, pk=int(pk))
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
        'date': obj.date or '',
        'desc1': obj.desc1 or '',
        'desc2': obj.desc2 or '',
        'desc3': obj.desc3 or '',
        'total_amount': obj.total_amount or '',
        'faulty_amount': obj.faulty_amount or '',
        'result_amount': obj.result_amount or '',
        'price': obj.price or '',

        'item': get_item_info(obj.item) if obj.item else '',
        'warehouse_id': obj.warehouse.id if obj.warehouse is not None else '',
        'warehouse_name': obj.warehouse.name if obj.warehouse is not None else '',
        'faulty_class_id': obj.faulty_class.id if obj.faulty_class is not None else '',
        'faulty_class_name': obj.faulty_class.name if obj.faulty_class is not None else '',
        'customer_id': obj.customer.id if obj.customer is not None else '',
        'customer_name': obj.customer.name if obj.customer is not None else '',

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


def get_item_info(item):
    return {
        'id': item.id,
        'name': item.name or '',
        'code': item.code or '',
        'desc1': item.desc1 or '',
        'desc2': item.desc2 or '',
        'desc3': item.desc3 or '',
        'safety_stock': item.safety_stock or '',
        'moq': item.moq or '',
        'buy_price': item.buy_price or 0,
        'sell_price': item.sell_price or 0,
        'std_cost': item.std_cost or 0,
        # 'qr_code': item.qr_code or 0,
        'is_valid': item.is_valid,
        'img': item.img.url if item.img and item.img.name else '',
        'doc_url': item.doc.url if item.doc and item.doc.name else '',
        'doc_name': item.doc.name if item.doc and item.doc.name else '',

        'unit_id': item.unit.id if item.unit is not None else '',
        'unit_name': item.unit.name if item.unit is not None else '',
        'item_class_id': item.item_class.id if item.item_class is not None else '',
        'item_class_name': item.item_class.name if item.item_class is not None else '',
        'warehouse_id': item.warehouse.id if item.warehouse is not None else '',
        'warehouse_name': item.warehouse.name if item.warehouse is not None else '',
        'supplier_id': item.supplier.id if item.supplier is not None else '',
        'supplier_name': item.supplier.name if item.supplier is not None else '',

        'created_by': get_user_info(item.created_by) if item.created_by else '',
        'updated_by': get_user_info(item.updated_by) if item.updated_by else '',
        'created_at': item.created_at.strftime('%Y-%m-%d') if item.created_at else '',
        'updated_at': item.updated_at.strftime('%Y-%m-%d') if item.updated_at else '',
        'company_id': item.company.id if item.company is not None else '',
        'company_name': item.company.company_info.first().company_name if item.company.company_info.exists() else '',
    }