from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from api.models import CodeMaster, FactoryEvent
from api.lib import get_excep_msg
from django.db import transaction
from django.utils import timezone


class FactoryEvent_Read(View):
    def get(self, request, *args, **kwargs):
        request_user = request.user
        event_filter = request.GET.get('event_filter', '')
        sch_status = request.GET.get('sch_status', 'false').lower() == 'true'

        qs = FactoryEvent.objects.filter(company=request_user.company)

        if event_filter:
            category_ids = event_filter.split(',')
            qs = qs.filter(category__id__in=category_ids)

        # 연관 객체 미리 가져오기 (쿼리 수 줄이기)
        qs = qs.select_related('purchase', 'production', 'customer_order')

        result = []
        for obj in qs:
            status = ''
            if obj.purchase_id and obj.purchase and hasattr(obj.purchase, 'status'):
                status = obj.purchase.status
            elif obj.production_id and obj.production and hasattr(obj.production, 'status'):
                status = obj.production.status
            elif obj.customer_order_id and obj.customer_order and hasattr(obj.customer_order, 'status'):
                status = obj.customer_order.status

            # sch_status가 true일 경우만 '완료' 상태 제외
            if sch_status and status == '완료':
                continue

            result.append(get_obj(obj))

        return JsonResponse(result, safe=False)


# class FactoryEvent_Read(View):
#     def get(self, request, *args, **kwargs):
#         request_user = request.user
#         event_filter = request.GET.get('event_filter', '')
#
#         qs = FactoryEvent.objects.filter(company=request_user.company)
#
#         if event_filter:
#             category_ids = event_filter.split(',')
#             qs = qs.filter(category__id__in=category_ids)
#
#         results = [get_obj(row) for row in qs]
#         return JsonResponse(results, safe=False)


class FactoryEvent_Create(View):
    @transaction.atomic
    def post(self, request):
        try:
            request_user = request.user

            title = request.POST.get('title', '')
            category_id = request.POST.get('category', '')
            category = get_object_or_404(CodeMaster, pk=int(category_id))
            start_date = request.POST.get('start_date', '')
            end_date = request.POST.get('end_date', '')
            event_url = request.POST.get('event_url', '')
            desc = request.POST.get('desc', '')

            obj = FactoryEvent.objects.create(
                title=title,
                category=category,
                start_date=start_date,
                end_date=end_date,
                event_url=event_url,
                desc=desc,

                created_by=request_user,
                updated_by=request_user,
                created_at=timezone.now(),
                updated_at=timezone.now(),
                company=request_user.company,
            )

            context = get_obj(obj)
            return JsonResponse(context)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class FactoryEvent_Update(View):
    @transaction.atomic
    def post(self, request):
        try:
            request_user = request.user

            pk = request.POST.get('pk')
            title = request.POST.get('title', '')
            category_id = request.POST.get('category', '')
            category = get_object_or_404(CodeMaster, pk=int(category_id))
            start_date = request.POST.get('start_date', '')
            end_date = request.POST.get('end_date', '')
            event_url = request.POST.get('event_url', '')
            desc = request.POST.get('desc', '')

            obj = get_object_or_404(FactoryEvent, pk=int(pk))
            obj.title = title
            obj.category = category
            obj.start_date = start_date
            obj.end_date = end_date
            obj.event_url = event_url
            obj.desc = desc
            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            context = get_obj(obj)
            return JsonResponse(context)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class FactoryEvent_Delete(View):
    @transaction.atomic
    def post(self, request):
        pk = request.POST.get('pk')

        if not pk:
            return JsonResponse({'error': True, 'message': '잘못된 요청입니다.'})

        try:
            obj = get_object_or_404(FactoryEvent, pk=int(pk))
            obj.delete()
        except Exception as e:
            print('삭제 실패:', e)
            return JsonResponse({'error': True, 'message': '사용중인 데이터입니다. 관련 데이터를 먼저 삭제해주세요.'})

        return JsonResponse({'error': False, 'id': pk})


def get_obj(obj):
    status = ''
    if obj.purchase_id and hasattr(obj.purchase, 'status'):
        status = obj.purchase.status
    elif obj.production_id and hasattr(obj.production, 'status'):
        status = obj.production.status
    elif obj.customer_order_id and hasattr(obj.customer_order, 'status'):
        status = obj.customer_order.status

    return {
        'id': obj.id,
        'title': obj.title if obj.title is not None else '',
        'start': obj.start_date if obj.start_date is not None else '',
        'end': obj.end_date if obj.start_date is not None else '',
        'desc': obj.desc if obj.desc is not None else '',
        'event_url': obj.event_url if obj.event_url is not None else '',
        'category_id': obj.category.id if obj.category is not None else '',
        'category_name': obj.category.name if obj.category is not None else '',
        'color': obj.category.desc3 if obj.category is not None else '',
        'status': status,

        'created_by_id': obj.created_by.id if obj.created_by is not None else '',
        'created_by_name': obj.created_by.name if obj.created_by is not None else '',
        'created_at': obj.created_at.date() if obj.created_at is not None else '',
        'updated_by_id': obj.updated_by.id if obj.updated_by is not None else '',
        'updated_by_name': obj.updated_by.name if obj.updated_by is not None else '',
        'updated_at': obj.updated_at.date() if obj.updated_at is not None else '',
        'company_id': obj.company.id if obj.company is not None else '',
        'company_name': obj.company.company_info.first().company_name if obj.company.company_info.exists() else '',
    }
