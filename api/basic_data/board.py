from django.views import View
from django.http import JsonResponse
from api.models import BoardMaster, CodeMaster, CommentMaster, CodeGroup, UserMaster, ReadStatus
from api.lib import Pagenation, get_excep_msg
from django.db import transaction
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Count
from django.utils.timezone import now
from datetime import datetime, time


class Board_List(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')

        # board/read 전용 쿼리
        board_read_id = request.GET.get('boardId', '')
        if board_read_id:
            qs = BoardMaster.objects.filter(id=board_read_id, company=request_user.company).order_by('-id')
            results = [get_obj(row) for row in qs]
            context = {'results': results}
            return JsonResponse(context, safe=False)

        # board_type은 board로 변경해야함
        qs = BoardMaster.objects.filter(company=request_user.company, board_type="notice").order_by('-id')
        qs_cat = BoardMaster.objects.filter(company=request_user.company, board_type="notice").order_by('-id')

        # 기간 검색
        if fr_date:
            if isinstance(fr_date, str):
                fr_date = datetime.strptime(fr_date, "%Y-%m-%d").date()
                fr_date = datetime.combine(fr_date, time(0, 0, 0))  # 00:00:00 설정
                qs = qs.filter(created_at__gte=fr_date)
                qs_cat = qs_cat.filter(created_at__gte=fr_date)

        if to_date:
            if isinstance(to_date, str):
                to_date = datetime.strptime(to_date, "%Y-%m-%d").date()
                to_date = datetime.combine(to_date, time(23, 59, 59))  # 23:59:59 설정
                qs = qs.filter(created_at__lte=to_date)
                qs_cat = qs_cat.filter(created_at__lte=to_date)

        # 키워드 검색
        all_sch = request.GET.get("all_sch", '')
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_condition = (
                            Q(title__icontains=keyword) |
                            Q(content__icontains=keyword) |
                            Q(created_by__name__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)
            qs_cat = qs_cat.filter(search_conditions)

        category_sch = request.GET.get('category_sch', '').strip()
        if category_sch and category_sch != "모든 게시물":
            qs = qs.filter(category__name=category_sch)

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

        # 전체게시물수 & 카테고리 게시물은 별도의 쿼리로 카테고리 이중필터 제한
        total_items_count = qs_cat.count()
        category_items = list(
            CodeMaster.objects.filter(group=CodeGroup.BOARD_CATEGORY, company=request_user.company)
            .annotate(item_count=Count('board_category', filter=Q(board_category__in=qs_cat)))
            .order_by('id').values('id', 'name', 'item_count')
        )

        # 별도의 쿼리로 구성된 고정된 게시물
        fixed_items = list(BoardMaster.objects.filter(board_type="notice", company=request_user.company, top_fixed_flag=True)
                           .annotate(comment_count=Count('comment_board')).order_by('-id')
                           .values('id', 'title', 'comment_count', 'views_count', 'created_at', 'upload_file',
                                   'category__name', 'created_by__name', 'created_by__job_level__name',
                                   'created_by__profile_image'))

        # 필터링에 따라 변하는 인기 게시물
        top_items = list(qs.annotate(comment_count=Count('comment_board')).order_by('-views_count')[:5]
                         .values('id', 'title', 'comment_count', 'views_count', 'created_at', 'upload_file',
                                 'category__name', 'created_by__name', 'created_by__job_level__name',
                                 'created_by__profile_image')
        )

        # 필터링에 따라 변하는 고정된 게시물 : 고정게시물은 변하면 안됨
        # fixed_items = list(qs.filter(top_fixed_flag=True).annotate(comment_count=Count('comment_board')).order_by('-id')
        #                    .values('id', 'title', 'comment_count', 'views_count', 'created_at', 'upload_file',
        #                            'category__name', 'created_by__name', 'created_by__job_level__name',
        #                            'created_by__profile_image')
        # )

        # 별도의 쿼리로 구성된 인기 게시물 : 인기세시물은 유동적인게 좋음
        # top_items = list(BoardMaster.objects.filter(board_type="notice", company=request_user.company)
        #                  .annotate(comment_count=Count('comment_board')).order_by('-views_count')[:5]
        #                  .values('id', 'title', 'comment_count', 'views_count', 'created_at', 'upload_file',
        #                          'category__name', 'created_by__name', 'created_by__job_level__name',
        #                          'created_by__profile_image'))

        context = {
            'count': qs_ps.paginator.count,
            'previous': url_pre,
            'next': url_next,
            'results': results,
            'category_items': category_items,
            'total_items_count': total_items_count,
            'top_items': top_items,
            'fixed_items': fixed_items,
        }

        return JsonResponse(context, safe=False)


class Board_Create(View):
    @transaction.atomic
    def post(self, request):
        try:
            title = request.POST.get('title', '')
            content = request.POST.get('content', '')
            category_id = request.POST.get('category', '')
            top_fixed_flag = request.POST.get('top_fixed_flag', '')
            upload_file = request.FILES.get("file", None)

            if upload_file and upload_file.size > 10 * 1024 * 1024:
                return JsonResponse({
                    'success': False,
                    'message': '업로드가 가능한 파일 크기와 첨부 이미지는 최대 10MB로 제한됩니다.'
                }, status=400)

            board_type = "notice"
            d_today = datetime.today().strftime('%Y-%m-%d')

            with transaction.atomic():
                obj = BoardMaster.objects.create(
                    title=title,
                    content=content,
                    category_id=category_id,
                    top_fixed_flag=top_fixed_flag,
                    board_type=board_type,
                    upload_file=upload_file,

                    created_by=request.user,
                    updated_by=request.user,
                    created_at=d_today,
                    updated_at=d_today,
                    company=request.user.company,
                )

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg})

        return JsonResponse({"id": obj.id, "success": True})


class Board_Update(View):
    @transaction.atomic
    def post(self, request):
        try:
            request_user = request.user

            pk = request.POST.get("pk", "")
            if request_user.is_master:
                obj = get_object_or_404(BoardMaster, id=pk)
            else:
                obj = get_object_or_404(BoardMaster, id=pk, created_by=request_user)

            title = request.POST.get("title", "").strip()
            content = request.POST.get("content", "").strip()
            category_id = request.POST.get("category", "")
            top_fixed_flag = request.POST.get("top_fixed_flag", "")
            remove_file = request.POST.get("remove_file", "0")
            upload_file = request.FILES.get("file", None)

            if upload_file and upload_file.size > 10 * 1024 * 1024:
                return JsonResponse({
                    'success': False,
                    'message': '업로드가 가능한 파일 크기와 첨부 이미지는 최대 10MB로 제한됩니다.'
                }, status=400)

            obj.title = title
            obj.content = content
            obj.category_id = category_id

            if remove_file == "1":
                obj.upload_file.delete(save=False)
                obj.upload_file = None
            if upload_file:
                obj.upload_file = upload_file

            obj.updated_by = request_user
            obj.updated_at = now()
            obj.save()

            return JsonResponse({"id": obj.id, "success": True})

        except BoardMaster.DoesNotExist:
            return JsonResponse({"error": True, "message": "해당 게시물을 찾을 수 없습니다."})

        except Exception as e:
            transaction.set_rollback(True)
            return JsonResponse({"error": True, "message": str(e)})


class Board_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            request_user = request.user
            pk = request.POST.get("pk", "")
            if request_user.is_master:
                obj = get_object_or_404(BoardMaster, id=pk)
            else:
                obj = get_object_or_404(BoardMaster, id=pk, created_by=request_user)

            with transaction.atomic():
                if obj.upload_file:
                    obj.upload_file.delete(save=False)
                if obj.title_image:
                    obj.title_image.delete(save=False)
                obj.delete()

            return JsonResponse({"id": pk, "success": True})

        except BoardMaster.DoesNotExist:
            return JsonResponse({'error': True, 'message': "해당 게시물을 찾을 수 없습니다."}, status=404)

        except Exception as e:
            transaction.set_rollback(True)
            return JsonResponse({'error': True, 'message': str(e)}, status=500)


# board_type을 'board'로 변경예정
def get_obj(obj):
    comment_count = CommentMaster.objects.filter(board=obj).count()
    is_read = ReadStatus.objects.filter(board=obj).first()
    is_read = is_read.is_read if is_read else False

    return {
        'id': obj.id,
        'title': obj.title if obj.title is not None else '',
        'content': obj.content if obj.content is not None else '',
        'views_count': obj.views_count if obj.views_count is not None else '',
        'comment_count': comment_count,
        'is_read': is_read,
        'top_fixed_flag': obj.top_fixed_flag if obj.top_fixed_flag is not None else '',
        'upload_file': obj.upload_file.url if obj.upload_file else '',
        'board_type': obj.board_type if obj.board_type else '',
        'category_id': obj.category.id if obj.category is not None else '',
        'category_name': obj.category.name if obj.category is not None else '',

        'created_by': get_user_info(obj.created_by) if obj.created_by else '',
        'updated_by': get_user_info(obj.updated_by) if obj.updated_by else '',
        'created_at': obj.created_at.date() if obj.created_at is not None else '',
        'created_at_datetime': obj.created_at.strftime('%Y-%m-%d %H:%M') if obj.created_at is not None else '',
        'updated_at': obj.updated_at.date() if obj.updated_at is not None else '',
        'updated_at_datetime': obj.updated_at.strftime('%Y-%m-%d %H:%M') if obj.updated_at is not None else '',
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