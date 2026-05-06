from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, OuterRef, Subquery, Max
from api.models import UserMaster, ItemHistory, CompanyItem
from api.lib import Pagenation, get_excep_msg
from datetime import datetime, date
from collections import defaultdict
from django.utils import timezone
from django.db.models import Sum, Case, When, F, Value, FloatField, BooleanField, ExpressionWrapper


class ItemManage_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')
        input_history = request.GET.get('input_history', '').lower() == 'true'
        output_history = request.GET.get('output_history', '').lower() == 'true'
        shortage_stock = request.GET.get('shortage_stock', '').lower() == 'true'

        qs = CompanyItem.objects.filter(company=request_user.company).order_by('code')

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
                        Q(asset_category__name__icontains=keyword) |
                        Q(supplier__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        # 날짜 필터 조건
        history_filter = Q()
        if fr_date:
            history_filter &= Q(item_history__date__gte=fr_date)
        if to_date:
            history_filter &= Q(item_history__date__lte=to_date)

        # 기본 값
        total_in_case = []
        total_out_case = []

        # 구매 필터
        if input_history:
            total_in_case.append(
                When(history_filter & Q(item_history__change_type='구매'), then=F('item_history__qty'))
            )

        # 소모 필터
        if output_history:
            total_out_case.append(
                When(history_filter & Q(item_history__change_type='소모'), then=F('item_history__qty'))
            )

        # annotate 적용
        qs = qs.annotate(
            total_in=Sum(
                Case(
                    *total_in_case,
                    default=Value(0),
                    output_field=FloatField()
                )
            ),
            total_out=Sum(
                Case(
                    *total_out_case,
                    default=Value(0),
                    output_field=FloatField()
                )
            ),
        ).annotate(
            current_amount=ExpressionWrapper(F('total_in') - F('total_out'), output_field=FloatField()),
            shortage_stock=Case(
                When(safety_stock__isnull=False, current_amount__lt=F('safety_stock'), then=Value(True)),
                default=Value(False),
                output_field=BooleanField()
            )
        )

        if shortage_stock:
            qs = qs.filter(shortage_stock=True)

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

        results = [get_obj_from_annotated(row) for row in qs_ps]

        context = {
            'count': qs_ps.paginator.count,
            'previous': url_pre,
            'next': url_next,
            'results': results,
        }

        return JsonResponse(context, safe=False)


def get_obj_from_annotated(obj):
    return {
        'id': obj.id,
        'name': obj.name or '',
        'code': obj.code or '',
        'desc1': obj.desc1 or '',
        'desc2': obj.desc2 or '',
        'desc3': obj.desc3 or '',
        'price': obj.price or '',
        'safety_stock': obj.safety_stock or '',
        "total_in": obj.total_in or 0,
        "total_out": obj.total_out or 0,
        "current_amount": obj.current_amount or 0,
        "shortage_stock": obj.shortage_stock,
        'supplier': obj.supplier or '',
        'is_valid': obj.is_valid,
        'asset_category_id': obj.asset_category.id if obj.asset_category else '',
        'asset_category_name': obj.asset_category.name if obj.asset_category else '',
        'created_by': get_user_info(obj.created_by) if obj.created_by else '',
        'updated_by': get_user_info(obj.updated_by) if obj.updated_by else '',
        'created_at': obj.created_at.strftime('%Y-%m-%d') if obj.created_at else '',
        'updated_at': obj.updated_at.strftime('%Y-%m-%d') if obj.updated_at else '',
    }


# class ItemManage_Read(View):
#     @transaction.atomic
#     def get(self, request, *args, **kwargs):
#         request_user = get_object_or_404(UserMaster, id=request.user.id)
#         _page = request.GET.get('page', '')
#         _size = request.GET.get('page_size', '')
#         fr_date = request.GET.get('fr_date', '')
#         to_date = request.GET.get('to_date', '')
#         input_history = request.GET.get('input_history', '').lower() == 'true'
#         output_history = request.GET.get('output_history', '').lower() == 'true'
#         shortage_stock = request.GET.get('shortage_stock', '').lower() == 'true'
#
#         qs = CompanyItem.objects.filter(company=request_user.company).order_by('code')
#
#         # 사용여부 필터
#         sch_is_valid = request.GET.get('sch_is_valid', '')
#         if sch_is_valid == "true":
#             qs = qs.filter(is_valid=True)
#         elif sch_is_valid == "false":
#             qs = qs.filter(is_valid=False)
#
#         # 키워드 검색
#         all_sch = request.GET.get("all_sch", '')
#         if all_sch:
#             search_keywords = all_sch.split(',')
#             search_conditions = Q()
#             for keyword in search_keywords:
#                 keyword = keyword.strip()
#                 if keyword:
#                     search_condition = (
#                         Q(name__icontains=keyword) |
#                         Q(code__icontains=keyword) |
#                         Q(desc1__icontains=keyword) |
#                         Q(desc2__icontains=keyword) |
#                         Q(desc3__icontains=keyword) |
#                         Q(asset_category__name__icontains=keyword) |
#                         Q(supplier__icontains=keyword)
#                     )
#                     search_conditions |= search_condition
#             qs = qs.filter(search_conditions)
#
#         if _page == '' or _size == '':
#             results = [get_obj(row) for row in qs]
#             context = {'results': results}
#             return JsonResponse(context, safe=False)
#
#         # Pagination
#         qs_ps = Pagenation(qs, _size, _page)
#
#         pre = int(_page) - 1
#         url_pre = "/?page_size=" + _size + "&page=" + str(pre)
#         if pre < 1:
#             url_pre = None
#
#         next = int(_page) + 1
#         url_next = "/?page_size=" + _size + "&page=" + str(next)
#         if next > qs_ps.paginator.num_pages:
#             url_next = None
#
#         results = []
#         # 기간 검색
#         for row in qs_ps:
#             row._fr_date = fr_date if fr_date else None
#             row._to_date = to_date if to_date else None
#             row_obj = get_obj(row)
#
#             # 필터링 조건: 재고 부족 항목만
#             if shortage_stock and not row_obj.get("shortage_stock", False):
#                 continue
#
#             results.append(row_obj)
#
#         context = {
#             'count': qs_ps.paginator.count,
#             'previous': url_pre,
#             'next': url_next,
#             'results': results,
#         }
#
#         return JsonResponse(context, safe=False)


class ItemManage_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)

            code = request.POST.get('code', '')
            name = request.POST.get('name', '')
            is_valid = request.POST.get('is_valid', '').lower() == 'true'
            supplier = request.POST.get('supplier', '')
            price = request.POST.get('price', '')
            price = int(price) if price and price.isdigit() else None
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')
            desc3 = request.POST.get('desc3', '')
            asset_category = request.POST.get('asset_category', '')
            asset_category = int(asset_category) if asset_category.isdigit() else None
            safety_stock = request.POST.get('safety_stock', '')
            try:
                safety_stock = float(safety_stock) if safety_stock else None
            except ValueError:
                safety_stock = None

            if not code:
                code = get_asset_code('item', request_user.company)

            obj = CompanyItem.objects.create(
                code=code,
                name=name,
                is_valid=is_valid,
                supplier=supplier,
                price=price,
                desc1=desc1,
                desc2=desc2,
                desc3=desc3,
                asset_category_id=asset_category,
                safety_stock=safety_stock,

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


class ItemManage_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            code = request.POST.get('code', '')
            name = request.POST.get('name', '')
            is_valid = request.POST.get('is_valid', '').lower() == 'true'
            supplier = request.POST.get('supplier', '')
            price = request.POST.get('price', '')
            price = int(price) if price and price.isdigit() else None
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')
            desc3 = request.POST.get('desc3', '')
            asset_category = request.POST.get('asset_category', '')
            asset_category = int(asset_category) if asset_category.isdigit() else None
            safety_stock = request.POST.get('safety_stock', '')
            try:
                safety_stock = float(safety_stock) if safety_stock else None
            except ValueError:
                safety_stock = None

            if not code:
                code = get_asset_code('item', request_user.company)

            obj = get_object_or_404(CompanyItem, pk=int(pk))

            obj.code = code
            obj.name = name
            obj.is_valid = is_valid
            obj.supplier = supplier
            obj.price = price
            obj.desc1 = desc1
            obj.desc2 = desc2
            obj.desc3 = desc3
            obj.asset_category_id = asset_category
            obj.safety_stock = safety_stock

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class ItemManage_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(CompanyItem, pk=int(pk))
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

    res = CompanyItem.objects.filter(code__istartswith=prefix, company=company)
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
    fr_date = getattr(obj, "_fr_date", None)
    to_date = getattr(obj, "_to_date", None)

    history_qs = obj.item_history.all()
    if fr_date:
        history_qs = history_qs.filter(date__gte=fr_date)
    if to_date:
        history_qs = history_qs.filter(date__lte=to_date)

    total_in = 0
    total_out = 0
    for h in history_qs:
        qty = h.qty or 0
        if h.change_type == '구매':
            total_in += qty
        elif h.change_type == '소모':
            total_out += qty

    current_amount = total_in - total_out
    shortage = obj.safety_stock is not None and current_amount < obj.safety_stock

    return {
        'id': obj.id,
        'name': obj.name or '',
        'code': obj.code or '',
        'desc1': obj.desc1 or '',
        'desc2': obj.desc2 or '',
        'desc3': obj.desc3 or '',
        'price': obj.price or '',
        "total_in": total_in,
        "total_out": total_out,
        "current_amount": current_amount,
        'safety_stock': obj.safety_stock or '',
        "shortage_stock": shortage,
        'supplier': obj.supplier or '',
        'is_valid': obj.is_valid,
        'asset_category_id': obj.asset_category.id if obj.asset_category is not None else '',
        'asset_category_name': obj.asset_category.name if obj.asset_category is not None else '',

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


class ItemHistory_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')
        item_pk = request.GET.get('item_pk', '')
        input_history = request.GET.get('input_history', '').lower() == 'true'
        output_history = request.GET.get('output_history', '').lower() == 'true'

        qs = ItemHistory.objects.filter(item_id=item_pk, company=request_user.company).order_by('-date', '-id')

        # 기간 검색
        if fr_date:
            qs = qs.filter(date__gte=fr_date)
        if to_date:
            qs = qs.filter(date__lte=to_date)

        # 구매 or 소모만 검색
        change_type_filter = Q()
        if input_history:
            change_type_filter |= Q(change_type="구매")
        if output_history:
            change_type_filter |= Q(change_type="소모")

        # 조건이 있을 때만 필터 적용
        if change_type_filter:
            qs = qs.filter(change_type_filter)
        else:
            qs = qs.none()  # 아무 조건도 없으면 결과 없음

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


class ItemHistory_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)

            item_pk = request.POST.get('item_pk', '')
            date_str = request.POST.get('date', '')
            date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else None
            change_type = request.POST.get('change_type', '')
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')
            desc3 = request.POST.get('desc3', '')
            qty = request.POST.get('qty', '')
            qty = float(qty) if qty else 0

            obj = ItemHistory.objects.create(
                item_id=item_pk,
                date=date,
                change_type=change_type,
                desc1=desc1,
                desc2=desc2,
                desc3=desc3,
                qty=qty,

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


class ItemHistory_Update(View):
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
            qty = request.POST.get('qty', '')
            qty = float(qty) if qty else 0

            obj = get_object_or_404(ItemHistory, pk=int(pk))

            obj.date = date
            obj.change_type = change_type
            obj.desc1 = desc1
            obj.desc2 = desc2
            obj.desc3 = desc3
            obj.qty = qty

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            context = get_obj_history(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class ItemHistory_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(ItemHistory, pk=int(pk))
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
        'qty': obj.qty or '',
        'item_id': obj.item.id if obj.item else '',
        'item_name': obj.item.name if obj.item else '',

        'created_by': get_user_info(obj.created_by) if obj.created_by else '',
        'updated_by': get_user_info(obj.updated_by) if obj.updated_by else '',
        'created_at': obj.created_at.strftime('%Y-%m-%d') if obj.created_at else '',
        'updated_at': obj.updated_at.strftime('%Y-%m-%d') if obj.updated_at else '',
    }

