from django.views import View
from django.http import JsonResponse
from api.models import CompanyMaster, CodeMaster, UserMaster, CompanyInfo
from api.lib import Pagenation, get_excep_msg
from django.db import transaction, IntegrityError
from django.db.models import Q, Count, Subquery, OuterRef
from django.utils import timezone
from api.msgs import txt
from datetime import datetime
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from api.basic_data.notification import noti_create_fn


class Company_Read(View):
    def get(self, request, *args, **kwargs):
        qs = CompanyMaster.objects.all().order_by('id')

        # 업체 마스터 ID / 활성 사용자
        master_user_subquery = UserMaster.objects.filter(
            company_id=OuterRef('id'), is_master=True, is_observer=False,
        ).order_by('id').values('id')[:1]

        qs = qs.annotate(
            master_user_id=Subquery(master_user_subquery),
            active_users=Count('user_company', filter=Q(user_company__is_staff=True))
        )

        # all_sch 검색
        all_sch = request.GET.get("all_sch", "").strip()
        if all_sch:
            filters = (
                    Q(code__icontains=all_sch) |
                    Q(name__icontains=all_sch)
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


@method_decorator(csrf_exempt, name='dispatch')
class Company_Create(View):
    @transaction.atomic
    def post(self, request):
        try:
            is_self_signup = request.POST.get('self_signup') == 'True'
            request_user = request.user
            tost_company_master = UserMaster.objects.filter(is_superuser=True).first()

            code = request.POST.get('code', '')
            if not code:
                code = get_company_code(request.POST)
            name = request.POST.get('name', '')
            master_id = request.POST.get('master_id', '')
            password = request.POST.get('password', 'tost2025')
            signup_email = request.POST.get('signup_email', '')

            # 신규업체 생성
            new_company_obj = CompanyMaster.objects.create(
                code=code,
                name=name,
                is_valid=True,
                created_at=timezone.now(),
                signup_email=signup_email,
            )

            # 신규업체 관리자 생성
            new_company = CompanyMaster.objects.get(pk=new_company_obj.id)
            company_master_code = code+'M'
            company_master_obj = UserMaster.objects.create_user(
                user_id=master_id,
                password=password,
                name="관리자",
            )
            company_master_obj.is_master = True
            company_master_obj.is_staff = True
            company_master_obj.email = signup_email
            company_master_obj.employee_code = company_master_code
            company_master_obj.company = new_company
            company_master_obj.join_date = timezone.now()
            company_master_obj.created_by = tost_company_master
            company_master_obj.updated_by = tost_company_master
            company_master_obj.save()

            # 신규업체 기본 코드마스터 생성
            CodeMaster.objects.create(group='board_category', name='공지사항', is_default=True, company=new_company_obj)
            CodeMaster.objects.create(group='event_category', name='회사 일정', desc3="#0d6efd", is_default=True, company=new_company_obj)
            CodeMaster.objects.create(group='event_category', name='회사 휴무', desc3="#dc3545", is_default=True, company=new_company_obj)
            CodeMaster.objects.create(group='event_category', name='휴가', desc3="#6c757d", is_default=True, company=new_company_obj)
            CodeMaster.objects.create(group='event_category', name='출장', desc3="#198754", is_default=True, company=new_company_obj)
            CodeMaster.objects.create(group='job_level', name='사원', company=new_company_obj)
            CodeMaster.objects.create(group='job_level', name='대리', company=new_company_obj)
            CodeMaster.objects.create(group='job_level', name='과장', company=new_company_obj)
            CodeMaster.objects.create(group='job_level', name='차장', company=new_company_obj)
            CodeMaster.objects.create(group='job_level', name='부장', company=new_company_obj)
            CodeMaster.objects.create(group='job_level', name='이사', company=new_company_obj)
            CodeMaster.objects.create(group='job_level', name='대표', company=new_company_obj)
            CodeMaster.objects.create(group='job_title', name='Project Manager', company=new_company_obj)
            CodeMaster.objects.create(group='job_title', name='Team Manager', company=new_company_obj)
            CodeMaster.objects.create(group='job_title', name='Director', company=new_company_obj)
            CodeMaster.objects.create(group='job_title', name='CEO', company=new_company_obj)
            CodeMaster.objects.create(group='team', name='경영지원팀', company=new_company_obj)
            CodeMaster.objects.create(group='team', name='경영기획팀', company=new_company_obj)
            CodeMaster.objects.create(group='team', name='개발팀', company=new_company_obj)
            CodeMaster.objects.create(group='team', name='생산팀', company=new_company_obj)
            CodeMaster.objects.create(group='team', name='영업팀', company=new_company_obj)
            CodeMaster.objects.create(group='team', name='구매팀', company=new_company_obj)
            CompanyInfo.objects.create(ceo=company_master_obj, company=new_company_obj, company_name=new_company_obj.name)

            # 알림센터 메세지 전송
            noti_create_fn(
                content=f"[{new_company_obj.name}] {company_master_obj.email}",
                user=UserMaster.objects.filter(is_superuser=True).first(),
                url=f"/admin/company/list/",
                noti_type="company_create"
            )

            context = {
                'id': new_company_obj.id,
                'code': new_company_obj.code,
                'name': new_company_obj.name,
            }
            return JsonResponse(context)

        except IntegrityError as e:  # 중복 예외 처리
            transaction.set_rollback(True)
            print(f"[중복 에러 발생] {str(e)}")
            return JsonResponse({'error': True, 'message': txt.error_1062}, status=400)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class Company_Update(View):
    @transaction.atomic
    def post(self, request):
        try:
            request_user = request.user

            pk = request.POST.get('pk', '')
            code = request.POST.get('code', '')
            name = request.POST.get('name', '')
            is_valid = request.POST.get('is_valid', '').lower() == 'true'
            expire_date_str = request.POST.get('expire_date', '')
            expire_date = datetime.strptime(expire_date_str, '%Y-%m-%d') if expire_date_str else None
            signup_email = request.POST.get('signup_email', '')

            if not code:
                code = get_company_code(request.POST)

            obj = CompanyMaster.objects.get(id=int(pk))

            obj.code = code
            obj.name = name
            obj.is_valid = is_valid
            obj.expire_date = expire_date
            obj.signup_email = signup_email

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

        context = {
            'id': obj.id,
            'code': obj.code,
            'name': obj.name,
        }
        return JsonResponse(context)


class Company_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            obj = CompanyMaster.objects.filter(id=int(pk)).first()

            if not obj:
                return JsonResponse({'error': True, 'message': txt.pk_not_exist})

            info = obj.company_info.first()
            if info:
                if info.logo:
                    info.logo.delete(save=False)
                if info.stamp:
                    info.stamp.delete(save=False)

            obj.delete()

            context = {
                'id': obj.id,
                'code': obj.code,
                'name': obj.name,
            }
            return JsonResponse(context)

        except Exception as e:
            transaction.set_rollback(True)  # 트랜잭션 롤백 후 에러처리
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg})


def get_company_code(obj):
    prefix = 'TOST-'
    default_number = 1

    # prefix로 시작하는 기존 회사 코드 조회
    res = CompanyMaster.objects.filter(code__startswith=prefix)

    # 가장 큰 번호 찾기
    max_number = 0
    for company in res:
        try:
            num_part = int(company.code.replace(prefix, ''))
            max_number = max(max_number, num_part)
        except ValueError:
            continue

    # 새로운 번호 시도
    new_number = max_number + 1

    # 중복 검사 및 중복이면 다음 번호로 증가
    while True:
        new_code = f"{prefix}{new_number:06d}"
        if not CompanyMaster.objects.filter(code=new_code).exists():
            return new_code
        new_number += 1


def get_obj(obj):
    try:
        custom_company_name = CompanyInfo.objects.get(company=obj).company_name
    except CompanyInfo.DoesNotExist:
        custom_company_name = ''

    company_master = UserMaster.objects.filter(id=obj.master_user_id).first()

    return {
        'id': obj.id,
        'code': obj.code if obj.code is not None else '',
        'name': obj.name if obj.name is not None else '',
        'custom_company_name': custom_company_name,
        'master_user_id': company_master.user_id if obj.master_user_id is not None else '',
        'master_last_login': company_master.last_login.strftime('%Y-%m-%d %H:%M') if company_master and company_master.last_login else '',
        'active_users': obj.active_users if obj.active_users is not None else '',
        'is_valid': obj.is_valid if obj.is_valid is not None else '',
        'expire_date': obj.expire_date if obj.expire_date is not None else '',
        'exit_request': obj.exit_request if obj.exit_request is not None else '',
        'signup_email': obj.signup_email if obj.signup_email is not None else '',

        'created_at': obj.created_at.date() if obj.created_at is not None else '',
    }


class Company_Exit(View):
    @transaction.atomic
    def post(self, request):
        try:
            request_user = request.user
            exit_company = request.user.company
            company_exit = request.POST.get('company_exit', '')

            if company_exit:
                obj = CompanyMaster.objects.get(id=exit_company.id)

                obj.is_valid = False
                obj.expire_date = timezone.now().date()
                obj.exit_request = company_exit

                obj.updated_by = request_user
                obj.updated_at = timezone.now()
                obj.save()

                # 알림센터 메세지 전송
                noti_create_fn(
                    content=f"[{exit_company.name}] 업체 탈퇴 요청",
                    user=UserMaster.objects.filter(is_superuser=True).first(),
                    url=f"/admin/company/list/",
                    noti_type="company_delete"
                )

        except IntegrityError:  # 중복 예외 처리
            transaction.set_rollback(True)
            return JsonResponse({'error': True, 'message': txt.error_1062}, status=400)

        except Exception as e:
            transaction.set_rollback(True)  # 트랜잭션 롤백 후 에러처리
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg})

        context = {
            'id': obj.id,
            'code': obj.code,
            'name': obj.name,
        }
        return JsonResponse(context)