from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, OuterRef, Subquery, Max, Sum
from api.models import UserMaster, CompanyCard, CompanyCardHistory
from api.lib import Pagenation, get_excep_msg
from datetime import datetime, date
from collections import defaultdict
from django.utils import timezone
from api.factory.factory_lib import get_user_info
from django.db.models.functions import TruncDate, TruncMonth


class CompanyCard_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')

        qs = CompanyCard.objects.filter(company=request_user.company).order_by('code')

        # 사용여부 필터
        sch_is_valid = request.GET.get('sch_is_valid', '')
        if sch_is_valid == "true":
            qs = qs.filter(is_valid=True)
        elif sch_is_valid == "false":
            qs = qs.filter(is_valid=False)

        # 키워드 검색
        all_sch = request.GET.get("a_all_sch", '')
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_condition = (
                        Q(name__icontains=keyword) |
                        Q(code__icontains=keyword) |
                        Q(owner__name__icontains=keyword) |
                        Q(card_supplier__icontains=keyword)
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


class CompanyCard_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)

            code = request.POST.get('code', '')
            name = request.POST.get('name', '')
            owner = request.POST.get('owner', '')
            owner = int(owner) if owner.isdigit() else None
            card_supplier = request.POST.get('card_supplier', '')
            validation_date_str = request.POST.get('validation_date', '')
            validation_date = datetime.strptime(validation_date_str, "%Y-%m-%d").date() if validation_date_str else None
            is_valid = request.POST.get('is_valid', '').lower() == 'true'

            obj = CompanyCard.objects.create(
                code=code,
                name=name,
                owner_id=owner,
                card_supplier=card_supplier,
                validation_date=validation_date,
                is_valid=is_valid,

                created_by=request_user,
                updated_by=request_user,
                created_at=timezone.now().date(),
                updated_at=timezone.now().date(),
                company=request_user.company,
            )

            # 사용자 > 법인카드 정보에 등록
            if owner:
                user_obj = get_object_or_404(UserMaster, pk=int(owner))
                user_obj.company_card_id = obj.id
                user_obj.save()

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class CompanyCard_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            code = request.POST.get('code', '')
            name = request.POST.get('name', '')
            owner = request.POST.get('owner', '')
            owner = int(owner) if owner.isdigit() else None
            card_supplier = request.POST.get('card_supplier', '')
            validation_date_str = request.POST.get('validation_date', '')
            validation_date = datetime.strptime(validation_date_str, "%Y-%m-%d").date() if validation_date_str else None
            is_valid = request.POST.get('is_valid', '').lower() == 'true'

            obj = get_object_or_404(CompanyCard, pk=int(pk))

            obj.code = code
            obj.name = name
            obj.owner_id = owner
            obj.card_supplier = card_supplier
            obj.validation_date = validation_date
            obj.is_valid = is_valid

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            # 사용자 > 법인카드 정보에 등록
            if owner:
                user_obj = get_object_or_404(UserMaster, pk=int(owner))
                user_obj.company_card_id = obj.id
                user_obj.save()

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class CompanyCard_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(CompanyCard, pk=int(pk))
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
        'name': obj.name or '',
        'code': obj.code or '',
        'card_supplier': obj.card_supplier or '',
        'validation_date': obj.validation_date.strftime('%Y-%m-%d') if obj.validation_date else '',
        'is_valid': obj.is_valid,
        'owner': get_user_info(obj.owner) if obj.owner else '',

        'created_by': get_user_info(obj.created_by) if obj.created_by else '',
        'updated_by': get_user_info(obj.updated_by) if obj.updated_by else '',
        'created_at': obj.created_at.strftime('%Y-%m-%d') if obj.created_at else '',
        'updated_at': obj.updated_at.strftime('%Y-%m-%d') if obj.updated_at else '',
        'company_id': obj.company.id if obj.company is not None else '',
        'company_name': obj.company.company_info.first().company_name if obj.company.company_info.exists() else '',
    }


class CompanyCardHistory_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')

        qs = CompanyCardHistory.objects.filter(company=request_user.company).order_by('-date', '-id')

        # 키워드 검색
        all_sch = request.GET.get("all_sch", '')
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_condition = (
                        Q(card__code__icontains=keyword) |
                        Q(card__name__icontains=keyword) |
                        Q(desc1__icontains=keyword) |
                        Q(desc2__icontains=keyword) |
                        Q(user__name__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        # 기간 검색
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')
        if fr_date:
            qs = qs.filter(date__gte=fr_date)
        if to_date:
            qs = qs.filter(date__lte=to_date)

        # card_id 필터
        card_id = request.GET.get('card_id', '')
        if card_id:
            qs = qs.filter(card_id=card_id)

        # sch_card_account 필터
        sch_card_account = request.GET.get('sch_card_account', '')
        if sch_card_account:
            qs = qs.filter(card_account_id=sch_card_account)

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


class CompanyCardHistory_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)

            card = request.POST.get('card', '')
            card = int(card) if card.isdigit() else None
            user = request.POST.get('user', '')
            user = int(user) if user.isdigit() else None
            card_account = request.POST.get('card_account', '')
            card_account = int(card_account) if card_account.isdigit() else None
            date_str = request.POST.get('date', None) or None
            date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else None
            price = request.POST.get('price', '')
            price = float(price) if price else 0
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')
            desc3 = request.POST.get('desc3', '')
            image = request.FILES.get('image', None)

            obj = CompanyCardHistory.objects.create(
                card_id=card,
                user_id=user,
                card_account_id=card_account,
                date=date,
                price=price,
                desc1=desc1,
                desc2=desc2,
                desc3=desc3,
                image=image,

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


class CompanyCardHistory_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            card = request.POST.get('card', '')
            card = int(card) if card.isdigit() else None
            user = request.POST.get('user', '')
            user = int(user) if user.isdigit() else None
            card_account = request.POST.get('card_account', '')
            card_account = int(card_account) if card_account.isdigit() else None
            date_str = request.POST.get('date', None) or None
            date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else None
            price = request.POST.get('price', '')
            price = float(price) if price else 0
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')
            desc3 = request.POST.get('desc3', '')
            image = request.FILES.get('image', None)
            image_clear = request.POST.get('image_clear', 'false') == 'true'

            obj = get_object_or_404(CompanyCardHistory, pk=int(pk))

            obj.card_id = card
            obj.user_id = user
            obj.card_account_id = card_account
            obj.date = date
            obj.price = price
            obj.desc1 = desc1
            obj.desc2 = desc2
            obj.desc3 = desc3

            if image_clear and obj.image:
                obj.image.delete(save=False)
                obj.image = None

            if image:
                obj.image = image

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            context = get_obj_history(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class CompanyCardHistory_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(CompanyCardHistory, pk=int(pk))
            if obj.image:
                obj.image.delete(save=False)
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
        'price': obj.price or 0,
        'desc1': obj.desc1 or '',
        'desc2': obj.desc2 or '',
        'desc3': obj.desc3 or '',
        'card_id': obj.card.id if obj.card else '',
        'card_code': obj.card.code if obj.card else '',
        'card_account_id': obj.card_account.id if obj.card_account else '',
        'card_account_name': obj.card_account.name if obj.card_account else '',
        'user': get_user_info(obj.user) if obj.user else '',
        'image': obj.image.url if obj.image and obj.image.name else '',

        'created_by': get_user_info(obj.created_by) if obj.created_by else '',
        'updated_by': get_user_info(obj.updated_by) if obj.updated_by else '',
        'created_at': obj.created_at.strftime('%Y-%m-%d') if obj.created_at else '',
        'updated_at': obj.updated_at.strftime('%Y-%m-%d') if obj.updated_at else '',
    }


# 법인카드 통계
class CompanyCard_Data(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        a_year_filter = request.GET.get('a_year_filter', '')
        try:
            a_year_filter = int(a_year_filter)
        except (ValueError, TypeError):
            return JsonResponse({'error': '기준연도에 오류가 있습니다.'}, status=400)

        start_date = date(a_year_filter, 1, 1)  # 선택연도의 1월 1일
        end_date = date(a_year_filter, 12, 31)  # 선택연도의 12월 31일

        qs = CompanyCardHistory.objects.filter(date__gte=start_date, date__lte=end_date,
                                               company=request_user.company).order_by('-date', '-id')

        # 키워드 검색
        all_sch = request.GET.get("all_sch", '')
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_condition = (
                        Q(card__owner__name__icontains=keyword) |
                        Q(card__code__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        # sch_team 필터
        sch_team = request.GET.get('sch_team', '')
        if sch_team:
            qs = qs.filter(card__owner__team_id=sch_team)

        # 월별 통계처리
        monthly_summary_qs = qs.annotate(month=TruncMonth('date')) \
            .values('month') \
            .annotate(total_price=Sum('price')) \
            .order_by('month')

        monthly_summary = [
            {
                'month': item['month'].strftime('%y/%m'),
                'total_price': item['total_price'] or 0
            }
            for item in monthly_summary_qs
        ]

        # 카드별/월별 통계처리
        monthly_card_qs = qs.annotate(month=TruncMonth('date')).values('month', 'card__id', 'card__code') \
            .annotate(total_price=Sum('price')).order_by('month', 'card__code')

        monthly_card_summary = defaultdict(list)

        for row in monthly_card_qs:
            month_key = row['month'].strftime('%y/%m')
            card_id = row['card__id']

            card_obj = CompanyCard.objects.filter(id=card_id, company=request_user.company) \
                .select_related('owner__team', 'owner__job_level').first()
            user_name = card_obj.owner.name if card_obj else ''
            user_team = card_obj.owner.team.name if card_obj and card_obj.owner.team else ''
            user_level = card_obj.owner.job_level.name if card_obj and card_obj.owner.job_level else ''
            user_image = card_obj.owner.profile_image.url if card_obj else ''

            monthly_card_summary[month_key].append({
                'card__id': card_id,
                'card__code': row['card__code'],
                'user_name': user_name,
                'user_team': user_team,
                'user__job_level__name': user_level,
                'user__profile_image': user_image,
                'total_price': row['total_price'] or 0
            })

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

        results = [get_obj_cost(row) for row in qs_ps]

        context = {
            'count': qs_ps.paginator.count,
            'previous': url_pre,
            'next': url_next,
            'results': results,
            'monthly_summary': monthly_summary,  # 월별 합계 (그래프용)
            'monthly_card_summary': monthly_card_summary,  # 사람별 월별 합계 (테이블용)
        }

        return JsonResponse(context, safe=False)


def get_obj_cost(obj):
    return {
        'id': obj.id,
        'desc1': obj.desc1,
        'desc2': obj.desc2,
        'price': obj.price,
    }