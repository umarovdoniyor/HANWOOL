from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, OuterRef, Subquery, Max
from api.models import UserMaster, CompanyAsset, AssetHistory, FactoryItem, FactoryBomStructure
from api.lib import Pagenation, get_excep_msg
from datetime import datetime, date
from collections import defaultdict
from django.utils import timezone
from api.factory.factory_lib import get_itemin_code, get_production_code, get_user_info, get_item_info


class BomStructure_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        item = request.GET.get('item', '')

        qs = FactoryBomStructure.objects.filter(parent_item_id=item, company=request_user.company).order_by('part_no')

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


class BomStructure_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)

            parent_item = request.POST.get('parent_item', '')
            parent_item = int(parent_item) if parent_item.isdigit() else None
            child_item = request.POST.get('child_item', '')
            child_item = int(child_item) if child_item.isdigit() else None
            part_no = request.POST.get('part_no', '')
            child_qty = request.POST.get('child_qty', '')

            if parent_item == child_item:
                return JsonResponse({"error": True, "message": "[BOM 품목]과 동일한 [하위 품목] 을 등록할 수 없습니다."})

            if not part_no:
                part_no = get_part_no(request_user.company, parent_item)

            obj = FactoryBomStructure.objects.create(
                parent_item_id=parent_item,
                child_item_id=child_item,
                part_no=part_no,
                child_qty=child_qty,

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


class BomStructure_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            parent_item = request.POST.get('parent_item', '')
            parent_item = int(parent_item) if parent_item.isdigit() else None
            child_item = request.POST.get('child_item', '')
            child_item = int(child_item) if child_item.isdigit() else None
            part_no = request.POST.get('part_no', '')
            child_qty = request.POST.get('child_qty', '')

            if parent_item == child_item:
                return JsonResponse({"error": True, "message": "[BOM 품목]과 동일한 [하위 품목] 을 등록할 수 없습니다."})

            if not part_no:
                part_no = get_part_no(request_user.company, parent_item)

            obj = get_object_or_404(FactoryBomStructure, pk=int(pk))

            obj.parent_item_id = parent_item
            obj.child_item_id = child_item
            obj.part_no = part_no
            obj.child_qty = child_qty

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class BomStructure_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(FactoryBomStructure, pk=int(pk))
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
        'part_no': obj.part_no or '',
        'child_qty': obj.child_qty or '',
        'parent_item': get_item_info(obj.parent_item) if obj.parent_item else '',
        'child_item': get_item_info(obj.child_item) if obj.child_item else '',

        'created_by': get_user_info(obj.created_by) if obj.created_by else '',
        'updated_by': get_user_info(obj.updated_by) if obj.updated_by else '',
        'created_at': obj.created_at.strftime('%Y-%m-%d') if obj.created_at else '',
        'updated_at': obj.updated_at.strftime('%Y-%m-%d') if obj.updated_at else '',
        'company_id': obj.company.id if obj.company is not None else '',
        'company_name': obj.company.company_info.first().company_name if obj.company.company_info.exists() else '',
    }

def get_part_no(company, parent_item):
    existing_part_nos = FactoryBomStructure.objects.filter(parent_item=parent_item, company=company).values_list('part_no', flat=True)
    used_numbers = set()
    for val in existing_part_nos:
        try:
            used_numbers.add(int(val))
        except ValueError:
            continue  # 숫자가 아닌 경우 무시

    # 1부터 사용되지 않은 숫자 찾기
    i = 1
    while i in used_numbers:
        i += 1
    return str(i)