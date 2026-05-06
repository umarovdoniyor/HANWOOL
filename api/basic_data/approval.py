from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from django.db import transaction, DatabaseError
from django.db.models import Q, OuterRef, Subquery, Max, Sum, Count
from api.models import ApvMaster, CommentMaster, ApvSubItem, ApvApprover, ApvCC, UserMaster, ReadStatus, EventMaster, \
    CodeMaster, BoardMaster, CompanyInfo
from api.lib import Pagenation, get_excep_msg
from datetime import datetime, date, time
from django.utils import timezone
import base64
import json
import logging
from django.views.decorators.csrf import csrf_exempt
from api.basic_data.notification import noti_create_fn
from api.basic_data.email import send_approval_mail_fn
from django.db.models.functions import TruncMonth

logger = logging.getLogger(__name__)


# 첨부파일 검증
APV_ATTACH_MAX_BYTES = 5 * 1024 * 1024  # 5 MB - matches the JS check in html_lib.html
APV_ATTACH_ALLOWED_EXTS = {
    'pdf', 'jpg', 'jpeg', 'png',
    'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    'hwp', 'hwpx', 'txt', 'zip',
}


def _validate_apv_attach(f):
    """첨부파일 사이즈/확장자 검증. 문제 없으면 None, 잘못된 경우 에러 메시지 반환."""
    if not f:
        return None
    if f.size > APV_ATTACH_MAX_BYTES:
        return "첨부파일 용량은 5MB를 초과할 수 없습니다."
    ext = (f.name.rsplit('.', 1)[-1] if '.' in f.name else '').lower()
    if ext not in APV_ATTACH_ALLOWED_EXTS:
        allowed = ', '.join(sorted(APV_ATTACH_ALLOWED_EXTS))
        return f"허용되지 않는 파일 형식입니다. (허용: {allowed})"
    return None


class Approval_List(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')

        qs = (
            ApvMaster.objects.filter(company=request_user.company)
            .select_related(
                'created_by',
                'created_by__team',
                'created_by__job_level',
            )
            .prefetch_related(
                'apv_approver',
                'apv_approver__approver1__job_level',
                'apv_approver__approver2__job_level',
                'apv_approver__approver3__job_level',
                'apv_approver__approver4__job_level',
                'apv_cc__user',
            )
            .annotate(comment_count_annotated=Count('comment_apv'))
            .order_by('-updated_at', '-apv_no')
        )

        # ORM-side "next approver is request_user" Q, avoids iterating qs in Python
        next_approver_is_user_q = (
            Q(apv_approver__approver1=request_user, apv_approver__approver1_status='대기') |
            (Q(apv_approver__approver2=request_user, apv_approver__approver2_status='대기')
             & ~Q(apv_approver__approver1_status='대기')) |
            (Q(apv_approver__approver3=request_user, apv_approver__approver3_status='대기')
             & ~Q(apv_approver__approver1_status='대기')
             & ~Q(apv_approver__approver2_status='대기')) |
            (Q(apv_approver__approver4=request_user, apv_approver__approver4_status='대기')
             & ~Q(apv_approver__approver1_status='대기')
             & ~Q(apv_approver__approver2_status='대기')
             & ~Q(apv_approver__approver3_status='대기'))
        )

        # 사용자의 권한에 따라 필터링
        if request_user.is_authenticated:
            if request_user.is_superuser or request_user.is_observer:  # 토스트관리자는 모든 게시물 조회 가능
                pass

            else:
                # 임시 상태의 문서를 해당 사용자만 볼 수 있도록 필터링, 삭제 상태의 문서를 목록에서 제외
                qs = qs.filter(
                    Q(created_by=request_user) |
                    ~Q(status='임시')
                )

                # 사용자가 생성한 게시물, cc_list에 포함된 게시물, 승인자로 포함된 게시물만 필터링
                qs = qs.filter(
                    Q(created_by=request_user) |
                    Q(apv_cc__user=request_user) |
                    Q(apv_approver__approver1=request_user) |
                    Q(apv_approver__approver2=request_user) |
                    Q(apv_approver__approver3=request_user) |
                    Q(apv_approver__approver4=request_user)
                ).distinct()

        else:  # 인증되지 않은 사용자는 아무 게시물도 조회할 수 없음
            qs = qs.none()

        # 사용자가 읽은 게시물 ID 목록, 읽지않음과 결재대기 건수
        read_status = ReadStatus.objects.filter(user=request_user).values_list('approval', flat=True)
        read_documents = set(read_status)
        unread_docs = qs.exclude(id__in=read_documents).count()
        waiting_docs = qs.filter(next_approver_is_user_q).exclude(status='반려').distinct().count()
        temp_docs = qs.filter(status="임시").count()

        # 기간 검색
        if fr_date:
            if isinstance(fr_date, str):
                fr_date = datetime.strptime(fr_date, "%Y-%m-%d").date()
            fr_date = datetime.combine(fr_date, time(0, 0, 0))  # 00:00:00 설정
            qs = qs.filter(updated_at__gte=fr_date)

        if to_date:
            if isinstance(to_date, str):
                to_date = datetime.strptime(to_date, "%Y-%m-%d").date()
            to_date = datetime.combine(to_date, time(23, 59, 59))  # 23:59:59 설정
            qs = qs.filter(updated_at__lte=to_date)

        # 키워드 검색
        all_sch = request.GET.get("all_sch", '')
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_condition = (
                        Q(apv_no__icontains=keyword) |
                        Q(title__icontains=keyword) |
                        Q(created_by__name__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        # 액션필터 검색
        action_filter = request.GET.get('action_filter', '')
        if action_filter == 'waiting_docs':
            qs = qs.filter(next_approver_is_user_q).exclude(status='반려').distinct()
        if action_filter == 'unread_docs':
            subquery = ReadStatus.objects.filter(approval=OuterRef('pk'), user=request_user)
            qs = qs.filter(
                Q(readstatus_apv__is_read=False, readstatus_apv__user=request_user) |
                ~Q(id__in=subquery.values('approval'))
            ).distinct()

        # '임시', '진행', '완료', '반려' 중 하나 이상 포함 시 필터링
        status_filter = request.GET.get('status_filter', '')
        if status_filter:
            status_list = status_filter.split(',')  # 다중 선택된 상태를 리스트로 변환
            allowed_statuses = {'임시', '진행', '완료', '반려'}  # URL에서 올 수 있는 값들
            selected_statuses = list(allowed_statuses.intersection(status_list))  # 유효한 상태만 필터링
            if selected_statuses:
                qs = qs.filter(status__in=selected_statuses).distinct()

        # 결재함 필터
        apvbox_filter = request.GET.get('apvbox_filter', '')
        if apvbox_filter == 'alldocs':  # 전체결재함
            qs = qs.filter()
        if apvbox_filter == 'mydocs':  # 보낸결재함
            qs = qs.filter(created_by=request_user)
        if apvbox_filter == 'rcvdocs':  # 받은결재함
            qs = qs.exclude(Q(created_by=request_user) | Q(apv_cc__user=request_user))
        if apvbox_filter == 'ccdocs':  # 참조결재함
            qs = qs.filter(apv_cc__user=request_user)

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

        results = []
        for row in qs_ps:
            cc_data = [{
                'user_id': cc.user.id if cc.user else '',
                'username': cc.user.name if cc.user else '',
            } for cc in row.apv_cc.all()]

            result = get_obj(row)
            result['apv_cc'] = cc_data
            result['is_read'] = row.id in read_documents

            if row.status == '진행':
                next_approver = Approval_Read.get_next_approver(row)
                result['next_approver'] = (
                    next_approver.name + ' ' + next_approver.job_level.name
                    if next_approver and next_approver.job_level
                    else next_approver.name if next_approver else ''
                )
                result['next_approver_id'] = next_approver.id if next_approver else ''
            else:
                result['next_approver'] = ''
                result['next_approver_id'] = ''
            results.append(result)

        context = {
            'count': qs_ps.paginator.count,
            'previous': url_pre,
            'next': url_next,
            'results': results,
            'unread_docs': unread_docs,
            'waiting_docs': waiting_docs,
            'temp_docs': temp_docs,
        }

        return JsonResponse(context, safe=False)



class Approval_Read(View):
    def get(self, request, *args, **kwargs):
        user = get_object_or_404(UserMaster, id=request.user.id)
        apv_id = request.GET.get('apv_id', '')

        if apv_id:
            apv_master = get_object_or_404(ApvMaster, id=apv_id)

            # 권한 검사: 슈퍼유저, 생성자, CC 리스트에 포함된 사용자, 승인자로 포함된 사용자
            if apv_master.status == '임시':
                is_authorized = user.is_observer or user.is_superuser or apv_master.created_by == user
            else:
                is_authorized = (
                    user.is_master or
                    apv_master.created_by == user or
                    apv_master.apv_cc.filter(user=user).exists() or
                    apv_master.apv_approver.filter(
                        Q(approver1=user) |
                        Q(approver2=user) |
                        Q(approver3=user) |
                        Q(approver4=user)
                    ).exists()
                )

            if not is_authorized:
                return JsonResponse({'error': '해당 문서에 접근 권한이 없습니다.'}, status=403)

            qs = [apv_master]

            # 세부항목 로딩
            sub_items = ApvSubItem.objects.filter(approval=apv_master)
            sub_item_data = [{
                'item_no': item.item_no,
                'desc1': item.desc1,
                'desc2': item.desc2,
                'desc3': item.desc3,
                'price': item.price,
                'qty': item.qty,
                'amount': item.amount,
                'remarks': item.remarks,
            } for item in sub_items]

            # approver 로딩
            approvers = ApvApprover.objects.filter(approval=apv_master).select_related(
                'approver1', 'approver2', 'approver3', 'approver4'
            )

            approver_data = []
            next_approver = None

            for approver in approvers:
                data = {}
                for i in range(1, 5):
                    approver_obj = getattr(approver, f'approver{i}', None)
                    status = getattr(approver, f'approver{i}_status', None)
                    if approver_obj is not None:
                        data.update({
                            f'approver{i}_id': approver_obj.id,
                            f'approver{i}_name': f"{approver_obj.name} {approver_obj.job_level.name}" if approver_obj.job_level else approver_obj.name,
                            f'approver{i}_img': approver_obj.profile_image.url if approver_obj.profile_image else None,
                            # f'approver{i}_sign': approver_obj.signature_file_path.url if approver_obj.signature_file_path else None,
                            f'approver{i}_team': approver_obj.team.name if approver_obj.team else None,
                            f'approver{i}_status': status,
                            f'approver{i}_date': getattr(approver, f'approver{i}_date', None)
                        })
                    else:
                        data.update({
                            f'approver{i}_id': None,
                            f'approver{i}_name': None,
                            f'approver{i}_img': None,
                            f'approver{i}_sign': None,
                            f'approver{i}_team': None,
                            f'approver{i}_status': None,
                            f'approver{i}_date': None
                        })

                    if status == '대기' and next_approver is None:
                        next_approver = approver_obj.id

                approver_data.append(data)

            # cc목록 로딩
            cc_list = ApvCC.objects.filter(approval=apv_master)
            cc_data = [{
                'user_id': cc.user.id if cc.user else '',
                'name': cc.user.name if cc.user else '',
                'job_level': cc.user.job_level.name if cc.user.job_level else '',
                'team': cc.user.team.name if cc.user.team else '',
                'profile_image': cc.user.profile_image.url if cc.user.profile_image else '',
            } for cc in cc_list]

            # 읽음 상태 업데이트
            read_status, created = ReadStatus.objects.get_or_create(
                user=user,
                approval=apv_master,
                company=user.company,
                defaults={'is_read': True}
            )

            # 변경된 필드만 업데이트
            if not created and not read_status.is_read:
                read_status.is_read = True
                read_status.save(update_fields=['is_read'])

            results = [get_obj(row) for row in qs]
            for result in results:
                result['sub_items'] = sub_item_data
                result['approvers'] = approver_data
                result['apv_cc'] = cc_data

            context = {
                'results': results,
                'current_user_id': user.id,
                'next_approver': next_approver,
                'last_approver': self.get_last_approver(apv_master),
            }

            return JsonResponse(context, safe=False)

    def post(self, request, *args, **kwargs):
        user_id = request.user.id
        user = get_object_or_404(UserMaster, id=user_id)
        apv_id = request.POST.get('apv_id', '')
        if not apv_id:
            return JsonResponse({'error': 'APV ID is required'}, status=400)

        apv_master = get_object_or_404(ApvMaster, id=apv_id)
        approver_action = request.POST.get('approver_action', '')

        # 승인 취소를 전달받을때
        if approver_action == 'cancel_approval':
            updated = self.update_approver_status(apv_master, user, '대기')
            if not updated:
                return JsonResponse({'error': 'Failed to cancel approval'}, status=500)

            next_approver = self.get_next_approver(apv_master)

            # 만약 모든 승인자가 취소되어 다시 대기 상태가 되면 문서 상태도 '진행'으로 변경
            apv_master.status = '진행'
            apv_master.save(update_fields=['status'])

            # 알림센터 메세지 전송
            noti_create_fn(
                content=f"{apv_master.title}",
                user=apv_master.created_by,
                url=f"/approval/progress/{apv_master.category}/{apv_master.id}/",
                noti_type="approval_canceled"
            )

            return JsonResponse({'success': 'Approval canceled and status updated'}, status=200)

        # 기안취소
        if approver_action == 'return_temp':
            if apv_master.created_by != user:
                return JsonResponse({'error': '권한이 없습니다.'}, status=403)
            self.reset_approver_status(apv_master)
            apv_master.status = '임시'
            apv_master.save(update_fields=['status'])
            ReadStatus.objects.filter(approval=apv_master).delete()
            EventMaster.objects.filter(approval=apv_master).delete()
            return JsonResponse({'success': '기안 취소 후 임시저장 상태로 변경하였습니다.'}, status=200)

        # 승인 버튼을 누른 사용자가 다음 승인자인지 확인
        next_approver = self.get_next_approver(apv_master)
        if next_approver is None:
            return JsonResponse({'error': '잘못된 접근입니다.'}, status=400)

        # 현재 유저가 다음 승인자가 아닌 경우 에러 반환
        if next_approver.id != user.id:
            return JsonResponse({'error': '권한이 없습니다.'}, status=403)

        # 승인을 전달받을때
        if approver_action == 'approve':
            updated = self.update_approver_status(apv_master, user, '승인')
            if not updated:
                return JsonResponse({'error': 'Failed to update status'}, status=500)

            next_approver = self.get_next_approver(apv_master)
            if next_approver is None:
                apv_master.status = '완료'
                apv_master.save(update_fields=['status'])

                # 알림센터 메세지 전송
                noti_create_fn(
                    content=f"{apv_master.title}",
                    user=apv_master.created_by,
                    url=f"/approval/progress/{apv_master.category}/{apv_master.id}/",
                    noti_type="approval_approved"
                )

                company_info = request.user.company.company_info.first()
                if company_info and company_info.approval_email:
                    try:
                        send_approval_mail_fn(
                            title=apv_master.title,
                            sub_title="전자결재 승인완료",
                            recipient=apv_master.created_by,
                            url_path=f"/approval/progress/{apv_master.category}/{apv_master.id}/"
                        )
                    except Exception as e:
                        logger.exception("이메일 발송 실패")

            else:
                # 다음 승인자에게 알림 전송
                noti_create_fn(
                    content=f"{apv_master.title}",
                    user=next_approver,
                    url=f"/approval/progress/{apv_master.category}/{apv_master.id}/",
                    noti_type="approval_requested"
                )

                company_info = request.user.company.company_info.first()
                if company_info and company_info.approval_email:
                    try:
                        send_approval_mail_fn(
                            title=apv_master.title,
                            sub_title="전자결재 승인요청",
                            recipient=next_approver,
                            url_path=f"/approval/progress/{apv_master.category}/{apv_master.id}/"
                        )
                    except Exception as e:
                        logger.exception("이메일 발송 실패")

            return JsonResponse({'success': 'Status updated'}, status=200)

        # 반려를 전달받을때
        elif approver_action == 'reject':
            updated = self.update_approver_status(apv_master, user, '반려')
            if updated:
                apv_master.status = '반려'
                apv_master.save(update_fields=['status'])

                # 연차신청 반려시 캘린더 데이터 삭제
                EventMaster.objects.filter(approval=apv_master).delete()

                # 알림센터 메세지 전송
                noti_create_fn(
                    content=f"{apv_master.title}",
                    user=apv_master.created_by,
                    url=f"/approval/progress/{apv_master.category}/{apv_master.id}/",
                    noti_type="approval_rejected"
                )

                company_info = request.user.company.company_info.first()
                if company_info and company_info.approval_email:
                    try:
                        send_approval_mail_fn(
                            title=apv_master.title,
                            sub_title="전자결재 반려",
                            recipient=apv_master.created_by,
                            url_path=f"/approval/progress/{apv_master.category}/{apv_master.id}/"
                        )
                    except Exception as e:
                        logger.exception("이메일 발송 실패")

            if not updated:
                return JsonResponse({'error': 'Failed to update status'}, status=500)
            return JsonResponse({'success': 'Status updated to 반려'}, status=200)

        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)

    @staticmethod
    def get_next_approver(apv_master):
        # Use the related manager so callers that prefetched apv_approver hit cache.
        for approver in apv_master.apv_approver.all():
            for i in range(1, 5):
                status = getattr(approver, f'approver{i}_status', None)
                approver_obj = getattr(approver, f'approver{i}', None)
                if status == '대기':
                    return approver_obj
        return None

    def get_last_approver(self, apv_master):
        approvers = ApvApprover.objects.filter(approval=apv_master)
        for approver in approvers:
            for i in range(4, 0, -1):  # 최근 승인자를 찾기 위해 역순 탐색
                status = getattr(approver, f'approver{i}_status', None)
                approver_obj = getattr(approver, f'approver{i}', None)
                if status == '승인' and approver_obj:  # 최근 승인된 사용자 찾기
                    return approver_obj.id
        return None

    def update_approver_status(self, apv_master, user, status):
        approvers = ApvApprover.objects.filter(approval=apv_master)
        for approver in approvers:
            for i in range(1, 5):
                approver_obj = getattr(approver, f'approver{i}', None)
                if approver_obj == user:
                    setattr(approver, f'approver{i}_status', status)
                    if status == '대기':  # 승인 취소 시 날짜 삭제
                        setattr(approver, f'approver{i}_date', None)
                    else:
                        setattr(approver, f'approver{i}_date', timezone.now().date())
                    approver.save()
                    return True
        return False

    def reset_approver_status(self, apv_master):
        approvers = ApvApprover.objects.filter(approval=apv_master)
        for approver in approvers:
            for i in range(1, 5):
                setattr(approver, f'approver{i}_status', '대기')
                setattr(approver, f'approver{i}_date', None)
            approver.save()


class Approval_Create(View):
    @transaction.atomic
    def post(self, request):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            apv_no = generate_apv_no()
            title = request.POST.get('title', '')
            category = int(request.POST.get('category', ''))
            status = request.POST.get('status', '')
            leave_reason = request.POST.get('leave_reason', '')
            detail = request.POST.get('detail', '')
            purpose = request.POST.get('purpose', '')
            payment_method = request.POST.get('payment_method', '')
            trip_with = request.POST.get('trip_with', '')
            start_half = request.POST.get('start_half', '')
            end_half = request.POST.get('end_half', '')
            leave_days = request.POST.get('leave_days', '')
            leave_days = None if leave_days == '' else leave_days
            apv_attach = request.FILES.get("apv_attach", None)
            err = _validate_apv_attach(apv_attach)
            if err:
                return JsonResponse({'error': True, 'message': err})

            deadline = request.POST.get('deadline', None)
            deadline = deadline.strip() if deadline else None

            start_datetime = request.POST.get('start_datetime', None)
            if start_datetime:
                start_datetime = datetime.strptime(start_datetime, "%Y-%m-%d %H:%M")
            else:
                start_datetime = None

            end_datetime = request.POST.get('end_datetime', None)
            if end_datetime:
                end_datetime = datetime.strptime(end_datetime, "%Y-%m-%d %H:%M")
            else:
                end_datetime = None

            approver_ids = [request.POST.get(f'approver{i}', None) for i in range(1, 5)]
            approvers = [get_object_or_404(UserMaster, pk=id) for id in approver_ids if id]

            apv_cc_ids = request.POST.getlist('apv_cc[]', [])
            apv_cc_users = UserMaster.objects.filter(pk__in=apv_cc_ids) if apv_cc_ids else []

            table_data = request.POST.get('table_data', '[]')
            table_data = json.loads(table_data)

            obj = ApvMaster.objects.create(
                apv_no=apv_no,
                title=title,
                category=category,
                status=status,
                leave_reason=leave_reason,
                detail=detail,
                deadline=deadline,
                purpose=purpose,
                payment_method=payment_method,
                trip_with=trip_with,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                start_half=start_half,
                end_half=end_half,
                leave_days=leave_days,
                apv_attach=apv_attach,
                request_date=timezone.now(),

                created_by=request_user,
                updated_by=request_user,
                created_at=timezone.now(),
                updated_at=timezone.now(),
                company=request_user.company,
            )

            approver_obj = ApvApprover.objects.create(
                approval=obj,
                **{f'approver{i}': approver for i, approver in enumerate(approvers, start=1)},
                **{f'approver{i}_status': '대기' for i in range(1, len(approvers) + 1)}
            )

            # 결재 프로세스가 진행될 경우, 첫 번째 결재자에게 알림 전송
            if status == '진행' and approvers:
                first_approver = approvers[0]
                noti_create_fn(
                    content=f"{title}",
                    user=first_approver,
                    url=f"/approval/progress/{category}/{obj.id}/",
                    noti_type="approval_requested"
                )

                company_info = request.user.company.company_info.first()
                if company_info and company_info.approval_email:
                    try:
                        send_approval_mail_fn(
                            title=title,
                            sub_title="전자결재 승인요청",
                            recipient=first_approver,
                            url_path=f"/approval/progress/{category}/{obj.id}/"
                        )
                    except Exception as e:
                        logger.exception("이메일 발송 실패")

            for apv_cc_user in apv_cc_users:
                ApvCC.objects.create(approval=obj, user=apv_cc_user)

            for item in table_data:
                ApvSubItem.objects.create(
                    approval=obj,
                    item_no=item['item_no'],
                    desc1=item['desc1'],
                    desc2=item['desc2'],
                    desc3=item['desc3'],
                    price=item['price'],
                    remarks=item['remarks']
                )

            # 본인이 작성한 글은 항상 is_read가 True
            ReadStatus.objects.create(user=request_user, approval=obj, company=request_user.company, is_read=True)

            # 캘린더 등록
            if (category == 1 or category == 2) and status in ['진행', '완료']:
                category_name = "휴가" if category == 1 else "출장"
                event_category = CodeMaster.objects.filter(company=request_user.company, name=category_name).last()

                if event_category:
                    if category == 1:
                        annual_leave_days = leave_days if leave_reason == "연차" else 0
                        event_desc = obj.leave_reason + (' (' + obj.detail + ')' if obj.detail else '')
                    else:  # category == 2
                        annual_leave_days = 0
                        event_desc = obj.purpose + (' (' + obj.detail + ')' if obj.detail else '')

                    EventMaster.objects.create(
                        approval=obj,
                        title=event_category.name + ' (' + obj.created_by.name + ')',
                        desc=event_desc,
                        start_date=obj.start_datetime,
                        end_date=obj.end_datetime,
                        category=event_category,
                        annual_leave_days=annual_leave_days,
                        change_type=event_category.name,
                        trip_with=obj.trip_with,

                        created_by=obj.created_by,
                        updated_by=obj.created_by,
                        company=obj.created_by.company,
                    )

            context = get_obj(obj)
            return JsonResponse(context)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


def generate_apv_no():
    today = timezone.now().date()
    prefix = f'AP{today.strftime("%y%m%d")}-'

    # 해당 날짜의 가장 큰 번호 찾기
    max_apv_no = ApvMaster.objects.filter(
        created_at__year=today.year,
        created_at__month=today.month,
        created_at__day=today.day,
        apv_no__startswith=prefix
    ).aggregate(Max('apv_no'))['apv_no__max']

    if max_apv_no:
        # 가장 큰 번호에서 숫자 부분만 추출
        last_count = int(max_apv_no.split('-')[-1])
        count_today = last_count + 1
    else:
        count_today = 1

    apv_no = f'{prefix}{count_today:03d}'
    return apv_no


class Approval_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            apv_id = request.POST.get('apv_id')
            apv_no = request.POST.get('apv_no', '')
            title = request.POST.get('title', '')
            category = int(request.POST.get('category', ''))
            status = request.POST.get('status', '')
            leave_reason = request.POST.get('leave_reason', '')
            detail = request.POST.get('detail', '')
            purpose = request.POST.get('purpose', '')
            payment_method = request.POST.get('payment_method', '')
            trip_with = request.POST.get('trip_with', '')
            start_half = request.POST.get('start_half', '')
            end_half = request.POST.get('end_half', '')
            leave_days = request.POST.get('leave_days', None)
            apv_attach = request.FILES.get("apv_attach", None)
            err = _validate_apv_attach(apv_attach)
            if err:
                return JsonResponse({'error': True, 'message': err})

            deadline = request.POST.get('deadline', None)
            deadline = deadline.strip() if deadline else None

            start_datetime = request.POST.get('start_datetime', None)
            if start_datetime:
                start_datetime = datetime.strptime(start_datetime, "%Y-%m-%d %H:%M")

            end_datetime = request.POST.get('end_datetime', None)
            if end_datetime:
                end_datetime = datetime.strptime(end_datetime, "%Y-%m-%d %H:%M")

            approver_ids = [request.POST.get(f'approver{i}', None) for i in range(1, 5)]
            approvers = [get_object_or_404(UserMaster, pk=id) for id in approver_ids if id]

            apv_cc_ids = request.POST.getlist('apv_cc[]', [])
            apv_cc_users = UserMaster.objects.filter(pk__in=apv_cc_ids) if apv_cc_ids else []

            table_data = request.POST.get('table_data', '[]')
            table_data = json.loads(table_data)

            obj = get_object_or_404(ApvMaster, pk=int(apv_id))
            obj.apv_no = apv_no
            obj.title = title
            obj.category = category
            obj.status = status
            obj.leave_reason = leave_reason
            obj.detail = detail
            obj.deadline = deadline
            obj.purpose = purpose
            obj.payment_method = payment_method
            obj.trip_with = trip_with
            obj.start_datetime = start_datetime
            obj.end_datetime = end_datetime
            obj.start_half = start_half
            obj.end_half = end_half
            obj.leave_days = leave_days
            obj.request_date = timezone.now()
            if apv_attach:
                obj.apv_attach = apv_attach
            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            ApvApprover.objects.filter(approval=obj).delete()
            ApvApprover_obj = ApvApprover.objects.create(approval=obj,
                **{f'approver{i}': approver for i, approver in enumerate(approvers, start=1)},
                **{f'approver{i}_status': '대기' for i in range(1, len(approvers) + 1)}
            )
            approver_data = {'approval': obj}

            # 결재 프로세스가 진행될 경우, 첫 번째 결재자에게 알림 전송
            if status == '진행' and approvers:
                first_approver = approvers[0]
                noti_create_fn(
                    content=f"{title}",
                    user=first_approver,
                    url=f"/approval/progress/{category}/{obj.id}/",
                    noti_type="approval_requested"
                )

                company_info = request.user.company.company_info.first()
                if company_info and company_info.approval_email:
                    try:
                        send_approval_mail_fn(
                            title=title,
                            sub_title="전자결재 승인요청",
                            recipient=first_approver,
                            url_path=f"/approval/progress/{category}/{obj.id}/"
                        )
                    except Exception as e:
                        logger.exception("이메일 발송 실패")

            ApvCC.objects.filter(approval=obj).delete()
            for apv_cc_user in apv_cc_users:
                ApvCC.objects.create(approval=obj, user=apv_cc_user)

            ApvSubItem.objects.filter(approval=obj).delete()
            for item in table_data:
                ApvSubItem.objects.create(
                    approval=obj,
                    item_no=item['item_no'],
                    desc1=item['desc1'],
                    desc2=item['desc2'],
                    desc3=item['desc3'],
                    price=item['price'],
                    remarks=item['remarks']
                )

            # 캘린더 기존객체 삭제 후 재등록
            EventMaster.objects.filter(approval=obj).delete()
            if (category == 1 or category == 2) and status in ['진행', '완료']:
                category_name = "휴가" if category == 1 else "출장"
                event_category = CodeMaster.objects.filter(company=request_user.company, name=category_name).last()

                if event_category:
                    if category == 1:
                        annual_leave_days = leave_days if leave_reason == "연차" else 0
                        event_desc = obj.leave_reason + (' (' + obj.detail + ')' if obj.detail else '')
                    else:  # category == 2
                        annual_leave_days = 0
                        event_desc = obj.purpose + (' (' + obj.detail + ')' if obj.detail else '')

                    EventMaster.objects.create(
                        approval=obj,
                        title=event_category.name + ' (' + obj.created_by.name + ')',
                        desc=event_desc,
                        start_date=obj.start_datetime,
                        end_date=obj.end_datetime,
                        category=event_category,
                        annual_leave_days=annual_leave_days,
                        change_type=event_category.name,
                        trip_with=obj.trip_with,

                        created_by=obj.created_by,
                        updated_by=obj.created_by,
                        company=obj.created_by.company,
                    )

            context = get_obj(obj)

        except Exception:
            logger.exception('전자결재 처리 중 예외 발생')
            msg = "입력한 데이터에 오류가 존재합니다.\n"
            for i in e.args:
                if i == 1062:
                    msg = '중복된 데이터가 존재합니다.'

            return JsonResponse({'error': True, 'message': msg})

        return JsonResponse(context)


class Approval_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            apv_id = request.POST.get('apv_id', '')

            if (apv_id == ''):
                msg = "삭제하시겠습니까?"
                return JsonResponse({'error': True, 'message': msg})

            obj = ApvMaster.objects.get(pk=int(apv_id))
            if obj.apv_attach:
                obj.apv_attach.delete(save=False)
            obj.delete()
        except Exception:
            logger.exception('전자결재 삭제 실패')
            msg = ["사용중인 데이터 입니다. 관련 데이터 삭제 후 다시 시도해주세요."]
            return JsonResponse({'error': True, 'message': msg})

        context = {}
        context['id'] = apv_id
        return JsonResponse(context)


def get_obj(obj):
    # Prefer annotated count if the caller used .annotate(comment_count_annotated=...)
    if hasattr(obj, 'comment_count_annotated'):
        comment_count = obj.comment_count_annotated
    else:
        comment_count = CommentMaster.objects.filter(approval=obj.id).count()

    return {
        'id': obj.id,
        'apv_no': obj.apv_no if obj.apv_no is not None else '',
        'title': obj.title if obj.title is not None else '',
        'category': obj.category if obj.category is not None else '',
        'category_name': obj.get_category_display() if obj.category is not None else '',
        'status': obj.status if obj.status is not None else '',
        'request_date': obj.request_date.date() if obj.request_date is not None else '',
        'created_by': {
            'id': obj.created_by.id,
            'name': obj.created_by.name,
            'profile_image': obj.created_by.profile_image.url if obj.created_by.profile_image else '',
            'team': obj.created_by.team.name if obj.created_by.team else '',
            'job_level': obj.created_by.job_level.name if obj.created_by.job_level else '',
            # 'signature_file_path': obj.created_by.signature_file_path.url if obj.created_by.signature_file_path else '',
        } if obj.created_by else '',
        'created_at': obj.created_at.date() if obj.created_at is not None else '',
        'updated_at': obj.updated_at.date() if obj.updated_at is not None else '',
        'detail': obj.detail if obj.detail is not None else '',
        'purpose': obj.purpose if obj.purpose is not None else '',
        'start_date': obj.start_datetime.date() if obj.start_datetime is not None else '',
        'start_datetime': obj.start_datetime.strftime('%Y-%m-%d %H:%M') if obj.start_datetime is not None else '',
        'start_half': obj.start_half if obj.start_half is not None else '',
        'end_date': obj.end_datetime.date() if obj.end_datetime is not None else '',
        'end_datetime': obj.end_datetime.strftime('%Y-%m-%d %H:%M') if obj.end_datetime is not None else '',
        'end_half': obj.end_half if obj.end_half is not None else '',
        'leave_days': obj.leave_days if obj.leave_days is not None else '',
        'leave_reason': obj.leave_reason if obj.leave_reason is not None else '',
        'deadline': obj.deadline if obj.deadline is not None else '',
        'payment_method': obj.payment_method if obj.payment_method is not None else '',
        'trip_with': obj.trip_with if obj.trip_with is not None else '',
        'apv_attach': obj.apv_attach.url if hasattr(obj, 'apv_attach') and obj.apv_attach else '',
        'apv_attach_size': obj.apv_attach.size if hasattr(obj, 'apv_attach') and obj.apv_attach and obj.apv_attach.storage.exists(obj.apv_attach.name) else None,
        'comment_count': comment_count,
    }


# 전자결재 비용/지출 통계
class Approval_Cost(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')

        qs = ApvSubItem.objects.filter(approval__status__in=["진행", "완료"], approval__company=request_user.company).order_by('-desc3', '-approval_id')

        # 사용자의 권한에 따라 필터링
        if request_user.is_authenticated:
            if request_user.is_superuser or request_user.is_observer or request_user.is_master:  # 토스트관리자와 업체관리자만 조회 가능
                pass

            else:
                qs = qs.none()

        else:  # 인증되지 않은 사용자는 아무 게시물도 조회할 수 없음
            qs = qs.none()

        # 기간 검색
        if fr_date:
            if isinstance(fr_date, str):
                fr_date = datetime.strptime(fr_date, "%Y-%m-%d").date()
            fr_date = datetime.combine(fr_date, time(0, 0, 0))  # 00:00:00 설정
            qs = qs.filter(desc3__gte=fr_date)

        if to_date:
            if isinstance(to_date, str):
                to_date = datetime.strptime(to_date, "%Y-%m-%d").date()
            to_date = datetime.combine(to_date, time(23, 59, 59))  # 23:59:59 설정
            qs = qs.filter(desc3__lte=to_date)

        # 키워드 검색
        all_sch = request.GET.get("all_sch", '')
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_condition = (
                        Q(desc1__icontains=keyword) |
                        Q(desc2__icontains=keyword) |
                        Q(remarks__icontains=keyword) |
                        Q(approval__purpose__icontains=keyword) |
                        Q(approval__apv_no__icontains=keyword) |
                        Q(approval__title__icontains=keyword) |
                        Q(approval__created_by__name__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        # sch_is_approved 필터
        sch_is_approved = request.GET.get('sch_is_approved', '')
        if sch_is_approved == "미승인":
            qs = qs.filter(approval__status="진행")
        elif sch_is_approved == "승인":
            qs = qs.filter(approval__status="완료")

        # 월별 통계처리
        monthly_summary_qs = qs.annotate(month=TruncMonth('desc3')) \
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
            'monthly_summary': monthly_summary,
        }

        return JsonResponse(context, safe=False)


def get_obj_cost(obj):
    return {
        'id': obj.id,
        'item_no': obj.item_no,
        'desc1': obj.desc1,
        'desc2': obj.desc2,
        'desc3': obj.desc3,
        'price': obj.price,
        'remarks': obj.remarks,

        'apv_id': obj.approval.id if obj.approval.id is not None else '',
        'apv_no': obj.approval.apv_no if obj.approval.apv_no is not None else '',
        'title': obj.approval.title if obj.approval.title is not None else '',
        'category': obj.approval.category if obj.approval.category is not None else '',
        'category_name': obj.approval.get_category_display() if obj.approval.category is not None else '',
        'status': obj.approval.status if obj.approval.status is not None else '',
        'purpose': obj.approval.purpose if obj.approval.purpose is not None else '',
    }