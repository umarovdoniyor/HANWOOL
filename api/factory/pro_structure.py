from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, OuterRef, Subquery, Max
from api.models import UserMaster, CompanyAsset, AssetHistory, FactoryItem, FactoryProStructure
from api.lib import Pagenation, get_excep_msg
from datetime import datetime, date
from collections import defaultdict
from django.utils import timezone


class ProStructure_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        item = request.GET.get('item', '')

        qs = FactoryProStructure.objects.filter(item_id=item, company=request_user.company).order_by('seq_no')

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


class ProStructure_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)

            item = request.POST.get('parent_item', '')
            item = int(item) if item.isdigit() else None
            process = request.POST.get('process', '')
            process = int(process) if process.isdigit() else None
            workshop = request.POST.get('workshop', '')
            workshop = int(workshop) if workshop.isdigit() else None
            responsible = request.POST.get('responsible', '')
            responsible = int(responsible) if responsible.isdigit() else None
            seq_no = request.POST.get('seq_no', None) or None
            desc1 = request.POST.get('desc1', '')

            if not seq_no:
                seq_no = get_seq_no(request_user.company, item)

            obj = FactoryProStructure.objects.create(
                item_id=item,
                process_id=process,
                workshop_id=workshop,
                responsible_id=responsible,
                seq_no=seq_no,
                desc1=desc1,

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


class ProStructure_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            item = request.POST.get('parent_item', '')
            item = int(item) if item.isdigit() else None
            process = request.POST.get('process', '')
            process = int(process) if process.isdigit() else None
            workshop = request.POST.get('workshop', '')
            workshop = int(workshop) if workshop.isdigit() else None
            responsible = request.POST.get('responsible', '')
            responsible = int(responsible) if responsible.isdigit() else None
            seq_no = request.POST.get('seq_no', None) or None
            desc1 = request.POST.get('desc1', '')

            if not seq_no:
                seq_no = get_seq_no(request_user.company, item)

            obj = get_object_or_404(FactoryProStructure, pk=int(pk))

            obj.item_id = item
            obj.process_id = process
            obj.workshop_id = workshop
            obj.responsible_id = responsible
            obj.seq_no = seq_no
            obj.desc1 = desc1

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class ProStructure_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(FactoryProStructure, pk=int(pk))
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
        'seq_no': obj.seq_no or '',
        'desc1': obj.desc1 or '',
        'item': get_item_info(obj.item) if obj.item else '',
        'responsible': get_user_info(obj.responsible) if obj.responsible else '',

        'process_id': obj.process.id if obj.process is not None else '',
        'process_name': obj.process.name if obj.process is not None else '',
        'workshop_id': obj.workshop.id if obj.workshop is not None else '',
        'workshop_name': obj.workshop.name if obj.workshop is not None else '',

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


def get_seq_no(company, item):
    existing_seq_nos = FactoryProStructure.objects.filter(item=item, company=company).values_list('seq_no', flat=True)
    used_numbers = set()
    for val in existing_seq_nos:
        try:
            used_numbers.add(int(val))
        except ValueError:
            continue  # 숫자가 아닌 경우 무시

    # 1부터 사용되지 않은 숫자 찾기
    i = 1
    while i in used_numbers:
        i += 1
    return str(i)