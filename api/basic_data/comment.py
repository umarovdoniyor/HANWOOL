from django.views import View
from django.http import JsonResponse
from api.models import BoardMaster, CommentMaster, ApvMaster, ProjectManage
from api.lib import Pagenation, get_excep_msg
from django.db import transaction
from django.shortcuts import get_object_or_404
import json
from api.msgs import txt
from api.basic_data.notification import noti_create_fn


class Comment_Read(View):
    def get(self, request, board_id=None, approval_id=None, project_id=None, *args, **kwargs):
        if board_id:
            qs = CommentMaster.objects.filter(board_id=board_id).order_by('created_at')
        elif approval_id:
            qs = CommentMaster.objects.filter(approval_id=approval_id).order_by('created_at')
        elif project_id:
            qs = CommentMaster.objects.filter(project_id=project_id).order_by('-created_at')
        else:
            return JsonResponse({'error': 'board_id 또는 approval_id, project_id를 제공해야 합니다.'}, status=400)

        # Pagination
        _page = int(request.GET.get('page', 1)) if request.GET.get('page', '1').isdigit() else 1
        _size = int(request.GET.get('page_size', 100)) if request.GET.get('page_size', '100').isdigit() else 100
        qs_ps = Pagenation(qs, _size, _page)

        pre_page = _page - 1
        url_pre = f"/?page_size={_size}&page={pre_page}" if pre_page >= 1 else None
        next_page = _page + 1
        url_next = f"/?page_size={_size}&page={next_page}" if next_page <= qs_ps.paginator.num_pages else None

        results = [get_obj(row, request) for row in qs_ps]
        context = {
            'count': qs_ps.paginator.count,
            'previous': url_pre,
            'next': url_next,
            'results': results,
        }
        return JsonResponse(context, safe=False)


class Comment_Create(View):
    @transaction.atomic
    def post(self, request, board_id=None, approval_id=None, project_id=None):
        try:
            data = json.loads(request.body)
            content = data.get("content", "").strip()
            is_private = bool(data.get("is_private", False))

            if not content:
                return JsonResponse({"error": "댓글 내용을 입력하세요."}, status=400)

            board = None
            approval = None
            project = None

            if board_id:
                board = get_object_or_404(BoardMaster, id=board_id)
            elif approval_id:
                approval = get_object_or_404(ApvMaster, id=approval_id)
            elif project_id:
                project = get_object_or_404(ProjectManage, id=project_id)
            else:
                return JsonResponse({'error': 'board_id 또는 approval_id를 제공해야 합니다.'}, status=400)

            obj = CommentMaster.objects.create(
                board=board if board else None,
                approval=approval if approval else None,
                project=project if project else None,
                content=content,
                created_by=request.user,
                company=request.user.company,
                is_private=is_private,
            )

            if board:
                if board.created_by != request.user:  # 자기 자신이 댓글 단 경우는 생략 가능
                    noti_create_fn(
                        content=f"{request.user.name} {getattr(request.user.job_level, 'name', '')} : {content}",
                        user=board.created_by,
                        url=f"/board/list/{board.id}/",
                        noti_type="board_comment"
                    )

            elif approval:
                if approval.created_by != request.user:  # 자기 자신이 댓글 단 경우는 생략 가능
                    noti_create_fn(
                        content=f"{request.user.name} {getattr(request.user.job_level, 'name', '')} : {content}",
                        user=approval.created_by,
                        url=f"/approval/progress/{approval.category}/{approval.id}/",
                        noti_type="approval_comment"
                    )

            elif project:
                if project.manager != request.user:  # 자기 자신이 댓글 단 경우는 생략 가능
                    noti_create_fn(
                        content=f"{request.user.name} {getattr(request.user.job_level, 'name', '')} : {content}",
                        user=project.manager,
                        url=f"/prj/prj_viewer/{project.id}/",
                        noti_type="project_comment"
                    )

            context = get_obj(obj, request)
            return JsonResponse(context)


        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class Comment_Update(View):
    @transaction.atomic
    def post(self, request, comment_id):
        try:
            obj = get_object_or_404(CommentMaster, id=comment_id, created_by=request.user)

            data = json.loads(request.body)
            new_content = data.get("content", "").strip()

            if not new_content:
                return JsonResponse({"error": "댓글 내용을 입력하세요."}, status=400)

            obj.content = new_content
            obj.save()

        except Exception as e:
            transaction.set_rollback(True)  # 트랜잭션 롤백 후 에러처리
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg})

        context = get_obj(obj, request)
        return JsonResponse(context)


class Comment_Delete(View):
    @transaction.atomic
    def post(self, request, comment_id):
        try:
            obj = get_object_or_404(CommentMaster, id=comment_id)

            # 작성자이거나 슈퍼유저만 삭제 가능
            if obj.created_by == request.user or request.user.is_superuser:
                obj.delete()
            else:
                return JsonResponse({'error': True, 'message': txt.pk_not_exist})

        except Exception as e:
            transaction.set_rollback(True)  # 트랜잭션 롤백 후 에러처리
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg})

        context = get_obj(obj, request)
        return JsonResponse(context)


def get_obj(obj, request):
    request_user = request.user
    is_owner = obj.created_by == request_user
    is_superuser = request_user.is_superuser
    is_private = obj.is_private

    # board가 존재할 경우에만 tost 판단
    if obj.board:
        is_tost_notice = obj.board.board_type == "tost"
    else:
        is_tost_notice = False  # approval에서는 해당 없음

    is_tost_comment = is_tost_notice

    if is_owner or is_superuser:
        # 작성자 본인 또는 관리자면 무조건 전체 공개
        is_visible = True
        partial_visible = False
    elif is_private and is_tost_comment:
        # tost + 비공개 → 모두 비공개
        is_visible = False
        partial_visible = False
    elif not is_private and is_tost_comment:
        # tost + 공개 → content만 공개
        is_visible = True
        partial_visible = True
    else:
        # 그 외는 전체 공개
        is_visible = True
        partial_visible = False

    # content 처리
    if is_visible:
        if (is_owner or is_superuser) and is_private:
            content = obj.content
        else:
            content = obj.content
    else:
        content = "** 관리자에게만 보이는 비공개 댓글입니다 **"

    obj_is_superuser = obj.created_by.is_superuser

    return {
        "id": obj.id,
        "content": content,
        "created_by": obj.created_by.name if (not partial_visible and is_visible) or obj_is_superuser else "익명의 토스터",
        "created_by_id": obj.created_by.id if not partial_visible and is_visible else "",
        "created_by_job_level": obj.created_by.job_level.name if obj.created_by.job_level and not partial_visible and is_visible else "",
        "created_by_company_id": obj.created_by.company.id if not partial_visible and is_visible else "",
        "created_by_company_name": obj.created_by.company.company_info.first().company_name if not partial_visible and is_visible else "",
        "profile_image": obj.created_by.profile_image.url if not partial_visible and is_visible else "/static/img/tost_icon_white_900.png",
        "created_at": obj.created_at.strftime("%Y-%m-%d %H:%M"),
        "updated_at": obj.updated_at.strftime("%Y-%m-%d %H:%M"),
        "is_owner": is_owner,
        "is_private": is_private,
        "is_superuser": is_superuser,
        "is_created_by_superuser": obj.created_by.is_superuser,
    }
