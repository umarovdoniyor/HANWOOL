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


def notice_list_page(request):
    request_user = request.user  # usermaster 객체
    user_id = request_user.id  # user의 pk_id
    user_id_code = request_user.user_id  # user의 id_code 텍스트
    company_id = request_user.company.id  # user의 company pk id

    all_sch = request.GET.get("all_sch", "").strip()  # 검색어
    category = request.GET.get("category", "").strip()  # 카테고리
    page = request.GET.get("page", 1)  # 기본 페이지 번호 (기본값: 1)

    notice_list = BoardMaster.objects.filter(board_type="notice", company=company_id).annotate(
        comment_count=Count('comment_board')
    ).order_by('-id')

    if all_sch:
        notice_list = notice_list.filter(
            Q(title__icontains=all_sch) |  # 제목 검색
            Q(content__icontains=all_sch) |  # 내용 검색
            Q(created_by__name__icontains=all_sch)  # 작성자 이름 검색
        )

    if category:
        notice_list = notice_list.filter(category__name=category)  # 카테고리 이름

    paginator = Paginator(notice_list, 10)  # 페이지당 게시물 수량
    notices = paginator.get_page(page)

    board_category = CodeMaster.objects.filter(group=CodeGroup.BOARD_CATEGORY, company=company_id).annotate(
        post_count=Count('board_category', filter=Q(board_category__board_type='notice'))
    ).order_by('id')
    total_notice_count = BoardMaster.objects.filter(board_type="notice", company=company_id).count()
    top_notices = BoardMaster.objects.filter(board_type="notice", company=company_id).annotate(
        comment_count=Count('comment_board')
    ).order_by('-views_count')[:5]
    top_fixed_notices = (BoardMaster.objects.filter(board_type="notice", company=company_id,top_fixed_flag=True)
                         .annotate(comment_count=Count('comment_board')).order_by('-id'))

    context = {
        'notices': notices,  # 변경된 변수명 적용
        'top_notices': top_notices,  # 인기게시물 상위 5개 추가
        'all_sch': all_sch,  # 검색어를 템플릿에 전달 (입력 필드 유지)
        'category': category,
        'board_category': board_category,
        'total_notice_count': total_notice_count,
        'top_fixed_notices': top_fixed_notices,
    }
    return render(request, 'notice/notice_list.html', context)


def notice_create_page(request, id=None):
    request_user = request.user  # usermaster 객체
    company_id = request_user.company.id  # user의 company pk id

    board_category = CodeMaster.objects.filter(group=CodeGroup.BOARD_CATEGORY, company=company_id)

    notice = None
    if id:
        if request_user.is_master:
            notice = get_object_or_404(BoardMaster, id=id)
        else:
            notice = get_object_or_404(BoardMaster, id=id, created_by=request_user)

    context = {
        "board_category": board_category,
        "notice": notice  # 수정 페이지로 전달
    }
    return render(request, "notice/notice_create.html", context)


def notice_read_page(request, id):
    request_user = request.user
    company_id = request_user.company.id

    try:
        notice = get_object_or_404(BoardMaster, id=id, board_type='notice')

        # 회사 불일치 시 오류 페이지 이동
        if notice.company_id != company_id:
            return render(request, 'error_page.html', {
                'message': '잘못된 접근입니다.'
            })

    except BoardMaster.DoesNotExist:
        return render(request, 'error_page.html', {
            'message': '존재하지 않는 게시물입니다.'
        })

    category = request.GET.get("category", "").strip()  # 카테고리
    notice_list = BoardMaster.objects.filter(board_type="notice", company=company_id).order_by('-id')
    board_category = CodeMaster.objects.filter(group=CodeGroup.BOARD_CATEGORY, company=company_id).annotate(
        post_count=Count('board_category', filter=Q(board_category__board_type='notice'))
    ).order_by('id')
    total_notice_count = BoardMaster.objects.filter(board_type="notice", company=company_id).count()
    top_notices = BoardMaster.objects.filter(board_type="notice", company=company_id).annotate(
        comment_count=Count('comment_board')
    ).order_by('-views_count')[:5]
    comment_count = CommentMaster.objects.filter(board=notice).count()
    top_fixed_notices = (BoardMaster.objects.filter(board_type="notice", company=company_id, top_fixed_flag=True)
                         .annotate(comment_count=Count('comment_board')).order_by('-id'))

    if category:
        notice_list = notice_list.filter(category__name=category)  # 카테고리 이름

    # 조회수 증가
    notice.views_count += 1
    notice.save(update_fields=["views_count"])

    # 읽음 상태 업데이트
    read_status, created = ReadStatus.objects.get_or_create(
        user=request_user,
        board=notice,
        company=request_user.company,
        defaults={'is_read': True}
    )

    context = {
        'notice': notice,
        'top_notices': top_notices,
        'category': category,
        'board_category': board_category,
        'total_notice_count': total_notice_count,
        'comment_count': comment_count,
        'top_fixed_notices': top_fixed_notices,
    }
    return render(request, 'notice/notice_read.html', context)


class Notice_List(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')
        # board_type = request.GET.get('board_type', '')

        # 공지사항에서 공지사항 리스트만 가져오기
        board_category = CodeMaster.objects.filter(company=request_user.company, name="공지사항").last()
        qs = BoardMaster.objects.filter(company=request_user.company, category=board_category,
                                        board_type="notice").order_by('-id')

        # 새로운 보드타입 생성할때까지 미사용
        # if board_type == "tost":
        #     qs = BoardMaster.objects.filter(board_type=board_type).order_by('-id')

        # 기간 검색
        if fr_date:
            if isinstance(fr_date, str):
                fr_date = datetime.strptime(fr_date, "%Y-%m-%d").date()
                fr_date = datetime.combine(fr_date, time(0, 0, 0))  # 00:00:00 설정
                qs = qs.filter(start_date__gte=fr_date)

        if to_date:
            if isinstance(to_date, str):
                to_date = datetime.strptime(to_date, "%Y-%m-%d").date()
                to_date = datetime.combine(to_date, time(23, 59, 59))  # 23:59:59 설정
                qs = qs.filter(start_date__lte=to_date)

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

        if _page == '' or _size == '':
            results = [get_obj(row, request) for row in qs]
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

        results = [get_obj(row, request) for row in qs_ps]

        context = {
            'count': qs_ps.paginator.count,
            'previous': url_pre,
            'next': url_next,
            'results': results,
        }

        return JsonResponse(context, safe=False)


class Notice_Create(View):
    @transaction.atomic
    def post(self, request):
        try:
            request_user = request.user  # usermaster 객체
            user_id = request_user.id  # user의 pk_id
            user_id_code = request_user.user_id  # user의 id_code 텍스트
            company_id = request_user.company.id  # user의 company pk id

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

                    created_by=request_user,
                    updated_by=request_user,
                    created_at=d_today,
                    updated_at=d_today,
                    company_id=company_id,
                )

                # 본인이 작성한 글은 항상 읽음표시 등록
                ReadStatus.objects.create(
                    board=obj,
                    user=request_user,
                    is_read=True,
                    company_id=company_id
                )

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg})

        return JsonResponse({"id": obj.id, "success": True})


class Notice_Update(View):
    @transaction.atomic
    def post(self, request):
        try:
            request_user = request.user  # usermaster 객체

            notice_id = request.POST.get("id", "")
            if request_user.is_master:
                obj = get_object_or_404(BoardMaster, id=notice_id)
            else:
                obj = get_object_or_404(BoardMaster, id=notice_id, created_by=request_user)

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


class Notice_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            request_user = request.user
            notice_id = request.POST.get("id", "")
            if request_user.is_master:
                obj = get_object_or_404(BoardMaster, id=notice_id)
            else:
                obj = get_object_or_404(BoardMaster, id=notice_id, created_by=request_user)

            with transaction.atomic():
                if obj.upload_file:
                    obj.upload_file.delete(save=False)
                obj.delete()

            return JsonResponse({"id": notice_id, "success": True})

        except BoardMaster.DoesNotExist:
            return JsonResponse({'error': True, 'message': "해당 게시물을 찾을 수 없습니다."}, status=404)

        except Exception as e:
            transaction.set_rollback(True)
            return JsonResponse({'error': True, 'message': str(e)}, status=500)


def get_obj(obj, request):
    comment_count = CommentMaster.objects.filter(board=obj).count()
    is_read = ReadStatus.objects.filter(board=obj, user=request.user).first()
    if is_read:
        is_read = is_read.is_read
    else:
        is_read = False

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

        'created_by': {
            'id': obj.created_by.id,
            'name': obj.created_by.name,
            'profile_image': obj.created_by.profile_image.url if obj.created_by.profile_image else '',
            'team': obj.created_by.team.name if obj.created_by.team else '',
            'job_level': obj.created_by.job_level.name if obj.created_by.job_level else '',
        } if obj.created_by else '',
        'created_at': obj.created_at.date() if obj.created_at is not None else '',
        'created_at_datetime': obj.created_at.strftime('%Y-%m-%d %H:%M') if obj.created_at is not None else '',
        'updated_at': obj.updated_at.date() if obj.updated_at is not None else '',
        'updated_at_datetime': obj.updated_at.strftime('%Y-%m-%d %H:%M') if obj.updated_at is not None else '',
        'company_id': obj.company.id if obj.company is not None else '',
        'company_name': obj.company.company_info.first().company_name if obj.company.company_info.exists() else '',
    }


class Notice_Topfix_Toggle(View):
    @transaction.atomic
    def post(self, request, board_id):
        try:
            board = BoardMaster.objects.get(id=board_id)
            board.top_fixed_flag = not board.top_fixed_flag
            board.save()
            return JsonResponse({'success': True, 'top_fixed_flag': board.top_fixed_flag})
        except BoardMaster.DoesNotExist:
            return JsonResponse({'success': False, 'error': '게시글이 존재하지 않습니다.'})
