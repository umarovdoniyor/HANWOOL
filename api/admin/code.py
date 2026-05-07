from django.views import View
from django.http import JsonResponse
from api.models import CodeMaster, CodeGroup
from api.lib import Pagenation, get_excep_msg
from django.db import transaction, IntegrityError
from django.db.models import Q, Count
from django.utils import timezone
from api.msgs import txt


class Codemaster_Read(View):
    def get(self, request, *args, **kwargs):
        request_user = request.user
        group_filter = request.GET.get('group_filter', '')

        ALLOWED_GROUPS = [
            CodeGroup.TEAM, CodeGroup.JOB_TITLE, CodeGroup.JOB_LEVEL,
            CodeGroup.BANK, CodeGroup.CARD_ACCOUNT, CodeGroup.COST_ACCOUNT,
            CodeGroup.CUSTOMER_CLASS, CodeGroup.RECRUIT_SITE,
            CodeGroup.BOARD_CATEGORY, CodeGroup.EVENT_CATEGORY,
            CodeGroup.PROJECT_CATEGORY, CodeGroup.ASSET_CATEGORY,
            CodeGroup.IP_ADDRESS, CodeGroup.DAILY_WAGE,
            CodeGroup.DAILY_WORKTIME, CodeGroup.MENU,
        ]
        qs = (
            CodeMaster.objects.filter(group__in=ALLOWED_GROUPS)
            .select_related('created_by', 'updated_by', 'company')
            .prefetch_related('company__company_info')
            .order_by('group', 'id')
        )
        if not request_user.is_superuser:
            qs = qs.filter(company=request_user.company)
            # 출장, 휴가는 전자결재에서 자동생성되는 필수값이기 때문에 수정 불가
            qs = qs.exclude(is_default=True)

        if group_filter:
            qs = qs.filter(group__contains=group_filter)

        # all_sch 검색
        all_sch = request.GET.get("all_sch", "").strip()
        if all_sch:
            filters = (
                    Q(name__icontains=all_sch) |
                    Q(desc1__icontains=all_sch) |
                    Q(desc2__icontains=all_sch) |
                    Q(desc3__icontains=all_sch) |
                    Q(company__name__icontains=all_sch)
            )
            qs = qs.filter(filters)

        # Pagination
        _page = int(request.GET.get('page', 1)) if request.GET.get('page', '1').isdigit() else 1
        _size = int(request.GET.get('page_size', 10)) if request.GET.get('page_size', '10').isdigit() else 10
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


class Codemaster_Create(View):
    @transaction.atomic
    def post(self, request):
        try:
            request_user = request.user
            group = request.POST.get('group', '')
            name = request.POST.get('name', '')
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')
            desc3 = request.POST.get('desc3', '')
            prj_cat = request.POST.get('prj_cat', '')
            price = request.POST.get('price', None) or None

            if group == CodeGroup.EVENT_CATEGORY:
                if not desc3:
                    desc3 = '#556ee6'

            if group == CodeGroup.PROJECT_CATEGORY:
                desc3 = prj_cat

            obj = CodeMaster.objects.create(
                group=group,
                name=name,
                desc1=desc1,
                desc2=desc2,
                desc3=desc3,
                price=price,

                created_by=request_user,
                updated_by=request_user,
                created_at=timezone.now(),
                updated_at=timezone.now(),
                company=request_user.company,
            )

            context = get_obj(obj)
            return JsonResponse(context)

        except IntegrityError:  # 중복 예외 처리
            transaction.set_rollback(True)
            return JsonResponse({'error': True, 'message': txt.error_1062}, status=400)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class Codemaster_Update(View):
    @transaction.atomic
    def post(self, request):
        try:
            request_user = request.user
            pk = request.POST.get('pk', '')
            group = request.POST.get('group', '')
            name = request.POST.get('name', '')
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')
            desc3 = request.POST.get('desc3', '')
            prj_cat = request.POST.get('prj_cat', '')
            price = request.POST.get('price', None) or None

            if group == CodeGroup.EVENT_CATEGORY:
                if not desc3:
                    desc3 = '#556ee6'
            else:
                desc3 = ''

            if group == CodeGroup.PROJECT_CATEGORY:
                desc3 = prj_cat

            obj = CodeMaster.objects.get(id=int(pk))
            if obj.is_default:
                return JsonResponse({'error': True, 'message': '기본값은 수정할 수 없습니다.'}, status=400)

            obj.group = group
            obj.name = name
            obj.desc1 = desc1
            obj.desc2 = desc2
            obj.desc3 = desc3
            obj.price = price

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

        except IntegrityError:  # 중복 예외 처리
            transaction.set_rollback(True)
            return JsonResponse({'error': True, 'message': txt.error_1062}, status=400)

        except Exception as e:
            transaction.set_rollback(True)  # 트랜잭션 롤백 후 에러처리
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg})

        context = get_obj(obj)
        return JsonResponse(context)


class Codemaster_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')

            obj = CodeMaster.objects.filter(id=int(pk)).first()
            if obj.is_default:
                return JsonResponse({'error': True, 'message': '기본값은 삭제할 수 없습니다.'}, status=400)
            elif obj:
                obj.delete()
            else:
                return JsonResponse({'error': True, 'message': txt.pk_not_exist})

        except Exception as e:
            transaction.set_rollback(True)  # 트랜잭션 롤백 후 에러처리
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg})

        context = get_obj(obj)
        return JsonResponse(context)


def get_obj(obj):
    return {
        'id': obj.id,
        'group_value': CodeGroup(obj.group).value if obj.group is not None else '',
        'group_label': CodeGroup(obj.group).label if obj.group is not None else '',
        'name': obj.name if obj.name is not None else '',
        'desc1': obj.desc1 if obj.desc1 is not None else '',
        'desc2': obj.desc2 if obj.desc2 is not None else '',
        'desc3': obj.desc3 if obj.desc3 is not None else '',
        'prj_cat': obj.desc3 if obj.desc3 is not None else '',
        'price': obj.price or '',

        'created_by_id': obj.created_by.id if obj.created_by is not None else '',
        'created_by_name': obj.created_by.name if obj.created_by is not None else '',
        'created_at': obj.created_at.date() if obj.created_at is not None else '',
        'updated_by_id': obj.updated_by.id if obj.updated_by is not None else '',
        'updated_by_name': obj.updated_by.name if obj.updated_by is not None else '',
        'updated_at': obj.updated_at.date() if obj.updated_at is not None else '',
        'company_id': obj.company.id if obj.company is not None else '',
        'company_name': (lambda ci: ci.company_name if ci else '')(obj.company.company_info.first() if obj.company is not None else None),
    }


def company_ip_list_fn(request):
    try:
        company_ip_list = CodeMaster.objects.filter(group=CodeGroup.IP_ADDRESS, company=request.user.company).values()
        context = {
            'company_ip_list': list(company_ip_list),
        }
        return JsonResponse(context)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)