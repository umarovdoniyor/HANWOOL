from api.models import BoardMaster, CodeMaster, CodeGroup, UserMaster
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Count


def blog_list_page(request):
    tost_company_master = UserMaster.objects.filter(is_superuser=True).first()
    tost_company = tost_company_master.company

    all_sch = request.GET.get("all_sch", "").strip()  # 검색어
    category = request.GET.get("category", "").strip()  # 카테고리
    page = request.GET.get("page", 1)  # 기본 페이지 번호 (기본값: 1)

    notice_list = BoardMaster.objects.filter(board_type="tost", is_blog=True).order_by('-id')

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

    board_category = CodeMaster.objects.filter(group=CodeGroup.BOARD_CATEGORY, company=tost_company).annotate(
        post_count=Count('board_category', filter=Q(board_category__board_type='tost', board_category__is_blog=True))
    ).filter(post_count__gt=0).order_by('id')
    total_notice_count = BoardMaster.objects.filter(board_type="tost", company=tost_company, is_blog=True).count()
    top_fixed_notices = (
        BoardMaster.objects.filter(board_type="tost", company=tost_company, is_blog=True, top_fixed_flag=True).order_by(
            '-id'))

    context = {
        'notices': notices,  # 변경된 변수명 적용
        'all_sch': all_sch,  # 검색어를 템플릿에 전달 (입력 필드 유지)
        'category': category,
        'board_category': board_category,
        'total_notice_count': total_notice_count,
        'top_fixed_notices': top_fixed_notices,
    }
    return render(request, 'brand/blog_list.html', context)


def blog_read_page(request, id):
    tost_company_master = UserMaster.objects.filter(is_superuser=True).first()
    tost_company = tost_company_master.company
    notice = get_object_or_404(BoardMaster, id=id)

    category = request.GET.get("category", "").strip()  # 카테고리
    notice_list = BoardMaster.objects.filter(board_type="tost", company=tost_company, is_blog=True).order_by('-id')
    board_category = CodeMaster.objects.filter(group=CodeGroup.BOARD_CATEGORY, company=tost_company).annotate(
        post_count=Count('board_category', filter=Q(board_category__board_type='tost', board_category__is_blog=True))
    ).filter(post_count__gt=0).order_by('id')
    total_notice_count = BoardMaster.objects.filter(board_type="tost", company=tost_company, is_blog=True).count()
    top_fixed_notices = (
        BoardMaster.objects.filter(board_type="tost", company=tost_company, is_blog=True, top_fixed_flag=True).order_by(
            '-id'))

    if category:
        notice_list = notice_list.filter(category__name=category)  # 카테고리 이름

    # 조회수 증가
    notice.views_count += 1
    notice.save(update_fields=["views_count"])

    context = {
        'notice': notice,
        'category': category,
        'board_category': board_category,
        'total_notice_count': total_notice_count,
        'top_fixed_notices': top_fixed_notices,
    }
    return render(request, 'brand/blog_read.html', context)
