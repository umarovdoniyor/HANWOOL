from django.views import View
from django.http import JsonResponse
from api.models import Notification
from api.lib import Pagenation, get_excep_msg
from django.db import transaction
from django.shortcuts import get_object_or_404
import json
from django.db.models import Q
from datetime import time, datetime


class Noti_List(View):
    def get(self, request, *args, **kwargs):
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')

        qs = Notification.objects.filter(user=request.user).order_by('-created_at')

        # 기간 검색
        if fr_date:
            if isinstance(fr_date, str):
                fr_date = datetime.strptime(fr_date, "%Y-%m-%d").date()
            fr_date = datetime.combine(fr_date, time(0, 0, 0))  # 00:00:00 설정
            qs = qs.filter(created_at__gte=fr_date)

        if to_date:
            if isinstance(to_date, str):
                to_date = datetime.strptime(to_date, "%Y-%m-%d").date()
            to_date = datetime.combine(to_date, time(23, 59, 59))  # 23:59:59 설정
            qs = qs.filter(created_at__lte=to_date)

        # 키워드 검색
        all_sch = request.GET.get("all_sch", "").strip()
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_conditions |= (
                        Q(message__icontains=keyword) |
                        Q(content__icontains=keyword)
                    )
            qs = qs.filter(search_conditions)

        # 전체/미확인/확인 필터
        notibox_filter = request.GET.get('notibox_filter', '')
        if notibox_filter == 'allBox':  # 전체 알림
            qs = qs.filter()
        if notibox_filter == 'unreadBox':  # 미확인 알림
            qs = qs.filter(is_read=False)
        if notibox_filter == 'readBox':  # 확인 알림
            qs = qs.filter(is_read=True)

        # 알림 종류로 필터 (미구현)
        # noti_type_sch = request.GET.get('noti_type_sch', '')
        # if noti_type_sch:
        #     qs = qs.filter(noti_type__contains=noti_type_sch)

        # Pagination
        _page = int(request.GET.get('page', 1)) if request.GET.get('page', '1').isdigit() else 1
        _size = int(request.GET.get('page_size', 100)) if request.GET.get('page_size', '100').isdigit() else 100
        qs_ps = Pagenation(qs, _size, _page)

        pre_page = _page - 1
        url_pre = f"/?page_size={_size}&page={pre_page}" if pre_page >= 1 else None
        next_page = _page + 1
        url_next = f"/?page_size={_size}&page={next_page}" if next_page <= qs_ps.paginator.num_pages else None

        results = [get_obj(row) for row in qs_ps]
        context = {
            'count': qs_ps.paginator.count,
            'previous': url_pre,
            'next': url_next,
            'results': results,
        }
        return JsonResponse(context, safe=False)


class Noti_Read_Update(View):
    def post(self, request):
        try:
            noti_id = request.POST.get("noti_id")
            change_type = request.POST.get("change_type", "")
            is_read = True
            if change_type == 'unread':
                is_read = False

            noti = Notification.objects.get(id=noti_id, user=request.user)
            noti.is_read = is_read
            noti.save()
            return JsonResponse({"success": True, "id": noti.id})
        except Notification.DoesNotExist:
            return JsonResponse({"error": True, "message": "알림이 존재하지 않거나 권한이 없습니다."})
        except Exception as e:
            return JsonResponse({"error": True, "message": get_excep_msg(e)})


class Noti_Read_Mass_Update(View):
    def post(self, request):
        try:
            ids = json.loads(request.POST.get("noti_ids", "[]"))
            change_range = request.POST.get("change_range", "")
            change_type = request.POST.get("change_type", "")
            is_read = True
            if change_type == 'unread':
                is_read = False

            if change_range == 'all':  # 전체 항목 변경
                count = Notification.objects.filter(user=request.user).update(is_read=is_read)
            else:  # 선택 항목만 변경
                count = Notification.objects.filter(id__in=ids, user=request.user).update(is_read=is_read)
            return JsonResponse({"success": True, "count": count})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})


class Noti_Mass_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            ids = json.loads(request.POST.get("noti_ids", "[]"))
            change_range = request.POST.get("change_range", "")

            if change_range == 'all':  # 전체 삭제
                deleted = Notification.objects.filter(user=request.user)
                count = deleted.count()
                deleted.delete()

            else:  # 선택 항목만 삭제
                deleted = Notification.objects.filter(id__in=ids, user=request.user)
                count = deleted.count()
                deleted.delete()

            return JsonResponse({"success": True, "count": count})

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg})


def get_obj(obj):
    return {
        "id": obj.id,
        'user': get_user_info(obj.user) if obj.user else '',
        "noti_type": obj.noti_type,
        "message": obj.message,
        "content": obj.content,
        "url": obj.url,
        "is_read": obj.is_read,
        "created_at": obj.created_at.strftime("%Y-%m-%d %H:%M"),
    }


def get_user_info(user):
    return {
        'id': user.id,
        'name': user.name,
        'profile_image': user.profile_image.url if user.profile_image and user.profile_image.name else '',
        'team': user.team.name if user.team else '',
        'job_level': user.job_level.name if user.job_level else '',
    }


# 알림센터 메세지 전송
NOTI_MESSAGES = {
    "board_comment": "작성한 게시물에 댓글이 등록되었습니다.",
    "calendar_with_create": "캘린더에 나와 관련된 일정이 등록되었습니다.",
    "calendar_with_update": "캘린더에 나와 관련된 일정이 수정되었습니다.",
    "approval_requested": "전자결재에 새로운 결재가 수신되었습니다.",
    "approval_approved": "신청한 전자결재가 승인되었습니다.",
    "approval_rejected": "신청한 전자결재가 반려되었습니다.",
    "approval_canceled": "전자결재 승인이 취소되었습니다.",
    "approval_comment": "전자결재에 댓글이 등록되었습니다.",
    "project_comment": "프로젝트에 댓글이 등록되었습니다.",
    "worktime_byadmin": "관리자에 의해 퇴근처리가 완료되었습니다.",
    "worktime_cancel": "관리자에 의해 퇴근처리가 취소되었습니다.",
    "worktime_deleted": "관리자에 의해 퇴근처리가 삭제되었습니다.",
    "leave_create": "연차 수량이 추가되었습니다.",
    "leave_delete": "연차 수량이 조정되었습니다.",
    "salary_master_created": "급여명세서가 등록되었습니다.",
    "company_create": "신규 업체가 가입하였습니다.",
    "company_delete": "업체가 탈퇴 요청을 하였습니다.",

    "purchase_approval_request": "구매발주서 결재 요청이 발생했습니다.",
    "purchase_approval_approved": "구매발주서 결재 요청이 승인되었습니다.",
    "production_approval_request": "생산계획서 결재 요청이 발생했습니다.",
    "production_approval_approved": "생산계획서 결재 요청이 승인되었습니다.",
    "delivery_approval_request": "출하계획서 결재 요청이 발생했습니다.",
    "delivery_approval_approved": "출하계획서 결재 요청이 승인되었습니다.",
}


def noti_create_fn(content, user, url=None, noti_type=None):
    message = NOTI_MESSAGES.get(noti_type)
    if user and message:
        Notification.objects.create(
            user=user,
            message=message,
            content=content,
            url=url,
            noti_type=noti_type
        )
