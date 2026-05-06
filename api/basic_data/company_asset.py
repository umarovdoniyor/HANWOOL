from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, OuterRef, Subquery, Max
from api.models import UserMaster, CompanyAsset, AssetHistory
from api.lib import Pagenation, get_excep_msg
from datetime import datetime, date
from collections import defaultdict
from django.utils import timezone


class AssetManage_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')
        asset_type = request.GET.get('asset_type', '')

        latest_history = AssetHistory.objects.filter(asset=OuterRef('pk')).order_by('-date', '-id')
        qs = CompanyAsset.objects.filter(asset_type=asset_type, company=request_user.company).annotate(
            current_owner_id=Subquery(latest_history.values('owner__id')[:1]),
            current_owner_team=Subquery(latest_history.values('owner__team__name')[:1])
        ).order_by('code')

        # 사용여부 필터
        sch_is_valid = request.GET.get('sch_is_valid', '')
        if sch_is_valid == "true":
            qs = qs.filter(is_valid=True)
        elif sch_is_valid == "false":
            qs = qs.filter(is_valid=False)

        # 기간 검색
        if fr_date:
            qs = qs.filter(acq_date__gte=fr_date)
        if to_date:
            qs = qs.filter(acq_date__lte=to_date)

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
                        Q(model__icontains=keyword) |
                        Q(info__icontains=keyword) |
                        Q(desc1__icontains=keyword) |
                        Q(desc2__icontains=keyword) |
                        Q(desc3__icontains=keyword) |
                        Q(asset_category__name__icontains=keyword) |
                        Q(current_owner_team__icontains=keyword) |
                        Q(supplier__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        # owner 필터
        sch_owner = request.GET.get('sch_owner', '')
        if sch_owner:
            qs = qs.filter(current_owner_id=sch_owner)

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


class AssetManage_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)

            asset_type = request.POST.get('asset_type', '')
            code = request.POST.get('code', '')
            name = request.POST.get('name', '')
            model = request.POST.get('model', '')
            is_valid = request.POST.get('is_valid', '').lower() == 'true'
            acq_date_str = request.POST.get('acq_date', '')
            acq_date = datetime.strptime(acq_date_str, "%Y-%m-%d").date() if acq_date_str else None
            supplier = request.POST.get('supplier', '')
            price = request.POST.get('price', '')
            price = int(price) if price and price.isdigit() else None
            info = request.POST.get('info', '')
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')
            desc3 = request.POST.get('desc3', '')
            asset_category = request.POST.get('asset_category', '')
            asset_category = int(asset_category) if asset_category.isdigit() else None
            image = request.FILES.get('image', None)

            if not code:
                code = get_asset_code(asset_type, request_user.company)

            obj = CompanyAsset.objects.create(
                code=code,
                name=name,
                model=model,
                is_valid=is_valid,
                acq_date=acq_date,
                supplier=supplier,
                price=price,
                info=info,
                desc1=desc1,
                desc2=desc2,
                desc3=desc3,
                asset_category_id=asset_category,
                image=image,
                asset_type=asset_type,

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


class AssetManage_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            asset_type = request.POST.get('asset_type', '')
            code = request.POST.get('code', '')
            name = request.POST.get('name', '')
            model = request.POST.get('model', '')
            is_valid = request.POST.get('is_valid', '').lower() == 'true'
            acq_date_str = request.POST.get('acq_date', '')
            acq_date = datetime.strptime(acq_date_str, "%Y-%m-%d").date() if acq_date_str else None
            supplier = request.POST.get('supplier', '')
            price = request.POST.get('price', '')
            price = int(price) if price and price.isdigit() else None
            info = request.POST.get('info', '')
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')
            desc3 = request.POST.get('desc3', '')
            asset_category = request.POST.get('asset_category', '')
            asset_category = int(asset_category) if asset_category.isdigit() else None
            image = request.FILES.get('image', None)
            image_clear = request.POST.get('image_clear', 'false') == 'true'

            if not code:
                code = get_asset_code(asset_type, request_user.company)

            obj = get_object_or_404(CompanyAsset, pk=int(pk))

            obj.code = code
            obj.name = name
            obj.model = model
            obj.is_valid = is_valid
            obj.acq_date = acq_date
            obj.supplier = supplier
            obj.price = price
            obj.info = info
            obj.desc1 = desc1
            obj.desc2 = desc2
            obj.desc3 = desc3
            obj.asset_category_id = asset_category

            if image_clear and obj.image:
                obj.image.delete(save=False)
                obj.image = None

            if image:
                obj.image = image

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class AssetManage_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(CompanyAsset, pk=int(pk))
            if obj.image:
                obj.image.delete(save=False)
            obj.delete()

            context = {'success': True}
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


def get_asset_code(asset_type, company):
    if asset_type == "private":
        prefix = 'AR-'
    elif asset_type == "public":
        prefix = 'AU-'
    elif asset_type == "item":
        prefix = 'AT-'
    else:
        prefix = 'AX-'

    order = '0000001'

    res = CompanyAsset.objects.filter(code__istartswith=prefix, company=company)
    if res.exists():
        latest_entry = res.order_by('-code').first()
        if latest_entry and latest_entry.code:
            try:
                num = latest_entry.code.replace(prefix, '')
                if num.isdigit():
                    order = str(int(num) + 1).zfill(7)
            except (ValueError, AttributeError):
                raise ValueError("기존 코드 처리 중 오류 발생")

    return prefix + order


def get_obj(obj):
    latest_history = obj.asset_history.order_by('-date', '-id').first()  # related_name='asset_history'
    current_owner = latest_history.owner if latest_history else None

    history_obj = []
    for h in obj.asset_history.order_by('-date', '-id'):
        history_obj.append({
            'id': h.id,
            'date': h.date.strftime('%Y-%m-%d') if h.date else '',
            'change_type': h.change_type or '',
            'desc1': h.desc1 or '',
            'desc2': h.desc2 or '',
            'desc3': h.desc3 or '',
            'owner': get_user_info(h.owner) if h.owner else '',
            'created_by': get_user_info(h.created_by) if h.created_by else '',
            'updated_by': get_user_info(h.updated_by) if h.updated_by else '',
        })

    return {
        'id': obj.id,
        'name': obj.name or '',
        'code': obj.code or '',
        'model': obj.model or '',
        'info': obj.info or '',
        'desc1': obj.desc1 or '',
        'desc2': obj.desc2 or '',
        'desc3': obj.desc3 or '',
        'acq_date': obj.acq_date.strftime('%Y-%m-%d') if obj.acq_date else '',
        'price': obj.price or 0,
        'supplier': obj.supplier or '',
        'is_valid': obj.is_valid,
        'asset_category_id': obj.asset_category.id if obj.asset_category is not None else '',
        'asset_category_name': obj.asset_category.name if obj.asset_category is not None else '',
        'image': obj.image.url if obj.image and obj.image.name else '',
        'current_owner': get_user_info(current_owner) if current_owner else '',
        'history_obj': history_obj,

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


class AssetHistory_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        asset_pk = request.GET.get('asset_pk', '')

        qs = AssetHistory.objects.filter(asset_id=asset_pk, company=request_user.company).order_by('-date', '-id')

        if _page == '' or _size == '':
            results = [get_obj_history(row) for row in qs]
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

        results = [get_obj_history(row) for row in qs_ps]

        context = {
            'count': qs_ps.paginator.count,
            'previous': url_pre,
            'next': url_next,
            'results': results,
        }

        return JsonResponse(context, safe=False)


class AssetHistory_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)

            asset_pk = request.POST.get('asset_pk', '')
            date_str = request.POST.get('date', '')
            date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else None
            change_type = request.POST.get('change_type', '')
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')
            desc3 = request.POST.get('desc3', '')
            owner = request.POST.get('owner', '')
            owner = int(owner) if owner.isdigit() else None

            obj = AssetHistory.objects.create(
                asset_id=asset_pk,
                date=date,
                change_type=change_type,
                desc1=desc1,
                desc2=desc2,
                desc3=desc3,
                owner_id=owner,

                created_by=request_user,
                updated_by=request_user,
                created_at=timezone.now().date(),
                updated_at=timezone.now().date(),
                company=request_user.company,
            )

            context = get_obj_history(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class AssetHistory_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            date_str = request.POST.get('date', '')
            date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else None
            change_type = request.POST.get('change_type', '')
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')
            desc3 = request.POST.get('desc3', '')
            owner = request.POST.get('owner', '')
            owner = int(owner) if owner.isdigit() else None

            obj = get_object_or_404(AssetHistory, pk=int(pk))

            obj.date = date
            obj.change_type = change_type
            obj.desc1 = desc1
            obj.desc2 = desc2
            obj.desc3 = desc3
            obj.owner_id = owner

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            context = get_obj_history(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class AssetHistory_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(AssetHistory, pk=int(pk))
            obj.delete()

            context = {'success': True}
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


def get_obj_history(obj):
    return {
        'id': obj.id,
        'date': obj.date.strftime('%Y-%m-%d') if obj.date else '',
        'change_type': obj.change_type or '',
        'desc1': obj.desc1 or '',
        'desc2': obj.desc2 or '',
        'desc3': obj.desc3 or '',
        'asset_id': obj.asset.id if obj.asset else '',
        'asset_name': obj.asset.name if obj.asset else '',
        'owner': get_user_info(obj.owner) if obj.owner else '',

        'created_by': get_user_info(obj.created_by) if obj.created_by else '',
        'updated_by': get_user_info(obj.updated_by) if obj.updated_by else '',
        'created_at': obj.created_at.strftime('%Y-%m-%d') if obj.created_at else '',
        'updated_at': obj.updated_at.strftime('%Y-%m-%d') if obj.updated_at else '',
    }


# class ItemStats_Read(View):
#     @transaction.atomic
#     def get(self, request, *args, **kwargs):
#         # 전체 장비
#         all_items = CompanyAsset.objects.all().prefetch_related('item_history')
#
#         # 통계 저장 딕셔너리
#         dept_summary = defaultdict(lambda: {'count': 0, 'cost': 0})
#         year_summary = defaultdict(lambda: {'count': 0, 'cost': 0})
#         no_history_count = 0
#         total_amount = 0
#         total_cost = 0
#         use_amount = 0
#         use_cost = 0
#         obsolete_amount = 0
#         obsolete_cost = 0
#
#         for item in all_items:
#             total_amount += 1
#             total_cost += item.acq_cost or 0
#
#             if item.is_valid:
#                 use_amount += 1
#                 use_cost += item.acq_cost or 0
#             else:
#                 obsolete_amount += 1
#                 obsolete_cost += item.acq_cost or 0
#
#             # 연도별
#             if item.acq_date:
#                 y = item.acq_date.year
#                 year_summary[y]['count'] += 1
#                 year_summary[y]['cost'] += item.acq_cost or 0
#
#             # 부서별 (latest history 기준)
#             history = item.item_history.order_by('-date', '-id')
#             latest = history.first()
#
#             if latest and latest.owner and latest.owner.department_position:
#                 dept = latest.owner.department_position.name
#             elif latest and (latest.owner is None or latest.owner.department_position is None):
#                 dept = "무소속"
#             elif not latest:
#                 dept = "무소속"
#
#             dept_summary[dept]['count'] += 1
#             dept_summary[dept]['cost'] += item.acq_cost or 0
#
#             # 미이력 수량
#             if not history.exists():
#                 no_history_count += 1
#
#             # 무소속 강제 포함
#             if "무소속" not in dept_summary:
#                 dept_summary["무소속"] = {"count": 0, "cost": 0}
#
#             # 무소속을 항상 마지막으로 보내며 나머지는 가나다순 정렬
#             sorted_dept = dict(
#                 sorted(dept_summary.items(), key=lambda x: (x[0] == '무소속', x[0]))
#             )
#
#         context = {
#             'total_amount': total_amount,
#             'total_cost': total_cost,
#             'use_amount': use_amount,
#             'use_cost': use_cost,
#             'obsolete_amount': obsolete_amount,
#             'obsolete_cost': obsolete_cost,
#             'no_history_count': no_history_count,
#             'by_dept': sorted_dept,
#             'by_year': dict(year_summary),
#         }
#
#         return JsonResponse(context, safe=False)

