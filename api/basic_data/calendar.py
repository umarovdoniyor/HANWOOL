from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from api.models import EventMaster
from django.views import View
from django.http import JsonResponse
from api.models import CodeMaster, CodeGroup, UserMaster
from api.lib import Pagenation, get_excep_msg
from django.db import transaction, IntegrityError
from django.db.models import Q, Count
from django.utils import timezone
from api.msgs import txt
from api.basic_data.notification import noti_create_fn

class Event_Read(View):
    def get(self, request, *args, **kwargs):
        request_user = request.user
        event_filter = request.GET.get('event_filter', '')

        qs = EventMaster.objects.filter(company=request_user.company).exclude(change_type__in=["연차 추가", "연차 삭감"])

        if event_filter:
            category_ids = event_filter.split(',')
            qs = qs.filter(category__id__in=category_ids)

        results = [get_obj(row) for row in qs]
        return JsonResponse(results, safe=False)


class Event_Create(View):
    @transaction.atomic
    def post(self, request):
        try:
            request_user = request.user

            title = request.POST.get('title', '')
            category_id = request.POST.get('category', '')
            category = get_object_or_404(CodeMaster, pk=int(category_id))
            start_date = request.POST.get('start_date', '')
            end_date = request.POST.get('end_date', '')
            trip_with = request.POST.get('trip_with', '')
            desc = request.POST.get('desc', '')

            obj = EventMaster.objects.create(
                title=title,
                category=category,
                start_date=start_date,
                end_date=end_date,
                trip_with=trip_with,
                desc=desc,

                created_by=request_user,
                updated_by=request_user,
                created_at=timezone.now(),
                updated_at=timezone.now(),
                company=request_user.company,
            )

            # 알림센터 메세지 전송
            trip_with_ids = request.POST.get('trip_with', '')
            trip_with_ids = [int(uid) for uid in trip_with_ids.split(',') if uid]
            trip_with_users = UserMaster.objects.filter(id__in=trip_with_ids)
            for user in trip_with_users:
                noti_create_fn(
                    content=f"[{obj.category.name}] {obj.title} ({obj.start_date})",
                    user=user,
                    url="/calendar/",
                    noti_type="calendar_with_create"
                )

            context = get_obj(obj)
            return JsonResponse(context)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class Event_Update(View):
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
            trip_with = request.POST.get('trip_with', '')
            desc = request.POST.get('desc', '')

            obj = get_object_or_404(EventMaster, pk=int(pk))
            obj.title = title
            obj.category = category
            obj.start_date = start_date
            obj.end_date = end_date
            obj.trip_with = trip_with
            obj.desc = desc
            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            # 알림센터 메세지 전송
            trip_with_ids = request.POST.get('trip_with', '')
            trip_with_ids = [int(uid) for uid in trip_with_ids.split(',') if uid]
            trip_with_users = UserMaster.objects.filter(id__in=trip_with_ids)
            for user in trip_with_users:
                noti_create_fn(
                    content=f"[{obj.category.name}] {obj.title} ({obj.start_date})",
                    user=user,
                    url="/calendar/",
                    noti_type="calendar_with_update"
                )

            context = get_obj(obj)
            return JsonResponse(context)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class Event_Delete(View):
    @transaction.atomic
    def post(self, request):
        pk = request.POST.get('pk')

        if not pk:
            return JsonResponse({'error': True, 'message': '잘못된 요청입니다.'})

        try:
            obj = get_object_or_404(EventMaster, pk=int(pk))
            obj.delete()
        except Exception as e:
            print('삭제 실패:', e)
            return JsonResponse({'error': True, 'message': '사용중인 데이터입니다. 관련 데이터를 먼저 삭제해주세요.'})

        return JsonResponse({'error': False, 'id': pk})


def get_obj(obj):
    return {
        'id': obj.id,
        'title': obj.title if obj.title is not None else '',
        'start': obj.start_date if obj.start_date is not None else '',
        'end': obj.end_date if obj.start_date is not None else '',
        'desc': obj.desc if obj.desc is not None else '',
        'approval_id': obj.approval.id if obj.approval is not None else '',
        'approval_status': obj.approval.status if obj.approval is not None else '',
        'category_id': obj.category.id if obj.category is not None else '',
        'category_name': obj.category.name if obj.category is not None else '',
        'color': obj.category.desc3 if obj.category is not None else '',
        'annual_leave_days': obj.annual_leave_days if obj.annual_leave_days is not None else '',
        'change_type': obj.change_type if obj.change_type is not None else '',
        'change_reason': obj.change_reason if obj.change_reason is not None else '',
        'trip_with': obj.trip_with if obj.trip_with is not None else '',

        'created_by_id': obj.created_by.id if obj.created_by is not None else '',
        'created_by_name': obj.created_by.name if obj.created_by is not None else '',
        'created_at': obj.created_at.date() if obj.created_at is not None else '',
        'updated_by_id': obj.updated_by.id if obj.updated_by is not None else '',
        'updated_by_name': obj.updated_by.name if obj.updated_by is not None else '',
        'updated_at': obj.updated_at.date() if obj.updated_at is not None else '',
        'company_id': obj.company.id if obj.company is not None else '',
        'company_name': obj.company.company_info.first().company_name if obj.company.company_info.exists() else '',
    }
