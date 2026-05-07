from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from api.models import CompanyMaster, UserMaster, CompanyInfo, CompanyCard, CodeMaster
from api.lib import Pagenation, get_excep_msg
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth.hashers import make_password
import random
import string
from django.db.models import F
from django.contrib.auth import update_session_auth_hash
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, date, time
import json
from dateutil.relativedelta import relativedelta

# FKs accessed by get_obj() per row - keep in sync with the FK reads below.
_EMPLOYEE_RELATED_FKS = (
    'team', 'job_title', 'job_level', 'bank',
    'company_card', 'customer', 'subsidiary',
    'created_by', 'company',
)


class Employee_Read(View):
    def get(self, request, *args, **kwargs):
        request_user = request.user
        request_user_company = request_user.company
        user_is_superuser = request_user.is_superuser

        is_staff = request.GET.get("is_staff", "").strip()

        if user_is_superuser:
            qs = UserMaster.objects.all().order_by('company', 'work_type', 'team_id', F('seq_order').asc(nulls_last=True), 'join_date')
        else:
            if is_staff == "true":
                qs = (UserMaster.objects.filter(company=request_user_company, is_delete=0, is_superuser=0, is_observer=0)
                      .order_by('work_type', 'team_id', F('seq_order').asc(nulls_last=True), 'join_date'))
            else:
                qs = (UserMaster.objects.filter(company=request_user_company, is_staff=1, is_delete=0, is_superuser=0)
                      .order_by('work_type', 'team_id', F('seq_order').asc(nulls_last=True), 'join_date'))

        # 조직도 페이지는 바로 전달
        org_chart = request.GET.get('org_chart', '')
        if org_chart == 'true':
            qs = (UserMaster.objects.filter(company=request_user_company, is_staff=1, is_delete=0, is_superuser=0)
                  .select_related(*_EMPLOYEE_RELATED_FKS)
                  .prefetch_related('company__company_info')
                  .order_by('team_id', F('seq_order').asc(nulls_last=True), 'join_date'))
            results = [get_obj(row) for row in qs]
            context = {
                'results': results,
            }
            return JsonResponse(context, safe=False)

        # 일반사용자 정보수정 페이지
        myinfo = request.GET.get('myinfo', '')
        if myinfo == 'true':
            qs = UserMaster.objects.filter(id=request_user.id)

        # 키워드 검색
        all_sch = request.GET.get("all_sch", '')
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_condition = (
                        Q(employee_code__icontains=keyword) |
                        Q(name__icontains=keyword) |
                        Q(user_id__icontains=keyword) |
                        Q(team__name__icontains=keyword) |
                        Q(job_title__name__icontains=keyword) |
                        Q(job_level__name__icontains=keyword) |
                        Q(work_type__icontains=keyword) |
                        Q(email__icontains=keyword) |
                        Q(hire_type__icontains=keyword) |
                        Q(phone__icontains=keyword) |
                        Q(remark__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        # sch_work_type 필터
        sch_work_type = request.GET.get('sch_work_type', '')
        if sch_work_type:
            qs = qs.filter(work_type=sch_work_type)
            if sch_work_type == "단기직":
                qs = qs.order_by('-join_date', 'name')

        # sch_team 필터
        sch_team = request.GET.get('sch_team', '')
        if sch_team:
            qs = qs.filter(team_id=sch_team)

        # sch_job_title 필터
        sch_job_title = request.GET.get('sch_job_title', '')
        if sch_job_title:
            qs = qs.filter(job_title_id=sch_job_title)
            
        # sch_subsidiary_id 필터   
        sch_subsidiary_id = request.GET.get('subsidiary_id', '')
        if sch_subsidiary_id:
            qs = qs.filter(subsidiary_id=sch_subsidiary_id)

        # select로 특정 아이템 호출
        select = request.GET.get('select', '')
        if select:
            qs = UserMaster.objects.filter(id=select, company=request_user.company)

        qs = qs.select_related(*_EMPLOYEE_RELATED_FKS).prefetch_related('company__company_info')

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


class Employee_Create(View):
    @transaction.atomic
    def post(self, request):
        try:
            request_user = request.user
            new_company_master = request.POST.get('company_master', '').lower() == 'true'
            new_company_id = request.POST.get('new_company_id', '')

            employee_code = request.POST.get('employee_code', '')
            name = request.POST.get('name', '')
            user_id = request.POST.get('user_id', '')
            password = request.POST.get('password', '')
            join_date = request.POST.get('join_date', None) or None
            retire_date = request.POST.get('retire_date', None) or None
            work_type = request.POST.get('work_type', '')
            hire_type = request.POST.get('hire_type', '')
            seq_order = request.POST.get('seq_order', None) or None
            phone = request.POST.get('phone', '')
            email = request.POST.get('email', '')
            address = request.POST.get('address', '')
            remark = request.POST.get('remark', '')

            gender = request.POST.get('gender', '')
            rrn = request.POST.get('rrn', '')
            nation = request.POST.get('nation', '')
            insurance = request.POST.get('insurance', '')
            account_code = request.POST.get('account_code', '')
            account_name = request.POST.get('account_name', '')

            team_id = request.POST.get('team', None)
            team_id = int(team_id) if team_id.isdigit() else None
            job_level_id = request.POST.get('job_level', None)
            job_level_id = int(job_level_id) if job_level_id.isdigit() else None
            job_title_id = request.POST.get('job_title', None)
            job_title_id = int(job_title_id) if job_title_id.isdigit() else None
            company_card_id = request.POST.get('company_card', None)
            company_card_id = int(company_card_id) if company_card_id.isdigit() else None
            bank_id = request.POST.get('bank', None)
            bank_id = int(bank_id) if bank_id.isdigit() else None
            subsidiary_id = request.POST.get('subsidiary', None)
            subsidiary_id = int(subsidiary_id) if subsidiary_id.isdigit() else None

            profile_image = request.FILES.get('profile_image', None)
            if not profile_image:
                profile_image = 'profile_image/profile_default.png'

            is_staff = request.POST.get('is_staff', '').lower() == 'true'
            is_master = request.POST.get('is_master', '').lower() == 'true'
            leave_manage_access = request.POST.get('leave_manage_access', '').lower() == 'true'

            created_at = timezone.now()

            if not employee_code:
                employee_code = get_employee_code(request.POST)

            if not user_id:
                user_id = employee_code

            if new_company_master:
                new_company = CompanyMaster.objects.get(pk=new_company_id)
                obj = UserMaster.objects.create_user(
                    user_id=user_id,
                    password=password,
                    name=f"{new_company.name} 관리자",
                )
                obj.is_master = True
                obj.employee_code = employee_code
                obj.company = new_company

            else:
                obj = UserMaster.objects.create_user(
                    user_id=user_id,
                    password=password,
                    name=name,
                )
                obj.is_master = is_master
                obj.leave_manage_access = leave_manage_access
                obj.employee_code = employee_code  # 사번
                obj.join_date = join_date
                obj.retire_date = retire_date
                obj.work_type = work_type
                obj.hire_type = hire_type
                obj.seq_order = seq_order
                obj.phone = phone
                obj.email = email
                obj.address = address
                obj.remark = remark

                obj.gender = gender
                obj.rrn = rrn
                obj.nation = nation
                obj.insurance = insurance
                obj.account_code = account_code
                obj.account_name = account_name
                obj.company_card_id = company_card_id
                obj.bank_id = bank_id
                obj.subsidiary_id = subsidiary_id

                obj.team_id = team_id
                obj.job_level_id = job_level_id
                obj.job_title_id = job_title_id
                obj.profile_image = profile_image
                obj.is_staff = is_staff
                obj.company = request_user.company

            obj.created_at = created_at
            obj.created_by = request_user
            obj.save()

            # 법인카드 > 사용자 정보에 등록
            if company_card_id:
                user_obj = get_object_or_404(CompanyCard, pk=int(company_card_id))
                user_obj.owner_id = obj.id
                user_obj.save()

        except IntegrityError as e:  # 중복 user_id 예외 처리
            transaction.set_rollback(True)
            return JsonResponse({'error': True, 'message': '이미 등록된 접속 ID입니다.'}, status=400)

        except Exception as e:
            transaction.set_rollback(True)  # 트랜잭션 롤백 후 에러처리
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg})

        context = get_obj(obj)
        return JsonResponse(context)


class Employee_Update(View):
    @transaction.atomic
    def post(self, request):
        try:
            request_user = request.user

            pk = request.POST.get('pk', '')
            employee_code = request.POST.get('employee_code', '')
            name = request.POST.get('name', '')
            user_id = request.POST.get('user_id', '')
            password = request.POST.get('password', '')
            join_date = request.POST.get('join_date', None) or None
            retire_date = request.POST.get('retire_date', None) or None
            work_type = request.POST.get('work_type', '')
            hire_type = request.POST.get('hire_type', '')
            seq_order = request.POST.get('seq_order', None) or None
            phone = request.POST.get('phone', '')
            email = request.POST.get('email', '')
            address = request.POST.get('address', '')
            remark = request.POST.get('remark', '')

            gender = request.POST.get('gender', '')
            rrn = request.POST.get('rrn', '')
            nation = request.POST.get('nation', '')
            insurance = request.POST.get('insurance', '')
            account_code = request.POST.get('account_code', '')
            account_name = request.POST.get('account_name', '')

            team_id = request.POST.get('team', None)
            team_id = int(team_id) if team_id.isdigit() else None
            job_level_id = request.POST.get('job_level', None)
            job_level_id = int(job_level_id) if job_level_id.isdigit() else None
            job_title_id = request.POST.get('job_title', None)
            job_title_id = int(job_title_id) if job_title_id.isdigit() else None
            company_card_id = request.POST.get('company_card', None)
            company_card_id = int(company_card_id) if company_card_id.isdigit() else None
            bank_id = request.POST.get('bank', None)
            bank_id = int(bank_id) if bank_id.isdigit() else None
            subsidiary_id = request.POST.get('subsidiary', None)
            subsidiary_id = int(subsidiary_id) if subsidiary_id.isdigit() else None

            image_clear = request.POST.get('image_clear', 'false') == 'true'
            profile_image = request.FILES.get('profile_image', None)
            default_profile_image = 'profile_image/profile_default.png'

            is_staff = request.POST.get('is_staff', '').lower() == 'true'
            is_master = request.POST.get('is_master', '').lower() == 'true'
            leave_manage_access = request.POST.get('leave_manage_access', '').lower() == 'true'
            menu_access = request.POST.get('menu_access', '')

            updated_at = timezone.now()

            if not employee_code:
                employee_code = get_employee_code(request.POST)

            if not user_id:
                user_id = employee_code

            if not is_staff:
                is_active = False
            else:
                is_active = True

            obj = UserMaster.objects.get(id=int(pk))

            # 관찰자 계정은 항상 퇴사처리 & 계정활성화
            if obj.is_observer:
                is_staff = False
                is_active = True

            # 마스터 계정 최소 1명 유지 로직
            if obj.is_master and not is_master:
                master_count = UserMaster.objects.filter(company=obj.company, is_master=True).exclude(
                    id=obj.id).count()
                if master_count == 0:
                    return JsonResponse({'error': True, 'message': '최소 한 명의 마스터 계정이 필요하여 수정이 제한됩니다.'}, status=400)

            if obj.is_observer:
                is_staff = False
                is_active = True

            obj.user_id = user_id
            obj.name = name
            obj.is_master = is_master
            obj.leave_manage_access = leave_manage_access
            obj.employee_code = employee_code  # 사번
            obj.join_date = join_date
            obj.retire_date = retire_date
            obj.work_type = work_type
            obj.hire_type = hire_type
            obj.seq_order = seq_order
            obj.phone = phone
            obj.email = email
            obj.address = address
            obj.remark = remark

            obj.gender = gender
            obj.rrn = rrn
            obj.nation = nation
            obj.insurance = insurance
            obj.account_code = account_code
            obj.account_name = account_name
            obj.company_card_id = company_card_id
            obj.bank_id = bank_id
            obj.subsidiary_id = subsidiary_id

            obj.team_id = team_id
            obj.job_level_id = job_level_id
            obj.job_title_id = job_title_id
            obj.is_staff = is_staff
            obj.is_active = is_active

            if password:
                obj.password = make_password(password)
                if request_user.pk == obj.pk:
                    update_session_auth_hash(request, obj)

            # 기본 프로필 이미지 삭제 예외처리
            if image_clear and obj.profile_image and 'profile_image/profile_default.png' not in obj.profile_image.name:
                obj.profile_image.delete(save=False)
                obj.profile_image = default_profile_image

            if profile_image:
                obj.profile_image = profile_image

            obj.menu_access = menu_access
            obj.updated_at = updated_at
            obj.updated_by = request_user
            obj.save()

            # 법인카드 > 사용자 정보에 등록
            if company_card_id:
                user_obj = get_object_or_404(CompanyCard, pk=int(company_card_id))
                user_obj.owner_id = obj.id
                user_obj.save()

        except IntegrityError as e:  # 중복 user_id 예외 처리
            transaction.set_rollback(True)
            return JsonResponse({'error': True, 'message': '이미 등록된 접속 ID입니다.'}, status=400)

        except Exception as e:
            transaction.set_rollback(True)  # 트랜잭션 롤백 후 에러처리
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg})

        context = get_obj(obj)
        return JsonResponse(context)


class Employee_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            request_user = request.user
            pk = request.POST.get('pk', '')

            def random_user_id(user_id):
                suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
                return f"{user_id}_{suffix}"

            obj = UserMaster.objects.get(id=int(pk))

            # 마스터 계정 최소 1명 유지 로직
            if obj.is_master:
                master_count = UserMaster.objects.filter(company=obj.company, is_master=True).exclude(id=obj.id).count()
                if master_count == 0:
                    return JsonResponse({'error': True, 'message': '최소 한 명의 마스터 계정이 필요하여 삭제가 제한됩니다.'}, status=400)

            obj.user_id = random_user_id(obj.user_id)
            obj.is_active = False
            obj.is_delete = True
            obj.is_staff = False
            obj.is_master = False
            obj.updated_at = timezone.now()
            obj.updated_by = request_user
            obj.save()

        except Exception as e:
            transaction.set_rollback(True)  # 트랜잭션 롤백 후 에러처리
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg})

        context = get_obj(obj)
        return JsonResponse(context)


def get_employee_code(obj):
    join_date = obj.get('join_date', '')
    if not join_date:
        raise ValueError("[입사일] 항목이 올바르지 않습니다.")

    date_parts = join_date.split('-')
    date = date_parts[0][2:] + date_parts[1] + date_parts[2]  # YYMMDD 조합
    prefix = 'TI-' + date
    order = '00'

    res = UserMaster.objects.filter(employee_code__istartswith=prefix)
    if res.exists():
        latest_entry = res.order_by('-employee_code').first()
        if latest_entry and latest_entry.employee_code:
            try:
                num = latest_entry.employee_code[-2:]  # 마지막 2자리 추출
                if num.isdigit():  # 숫자인 경우에만 변환
                    order = str(int(num) + 1).zfill(2)
            except (ValueError, AttributeError):
                raise ValueError("Failed to process existing codes for prefix.")

    return prefix + order


def get_obj(obj):
    today = date.today()
    join_date = obj.join_date
    retire_date = obj.retire_date
    if isinstance(join_date, str):
        try:
            join_date = datetime.strptime(join_date, "%Y-%m-%d").date()
        except ValueError:
            join_date = today
    elif isinstance(join_date, datetime):
        join_date = join_date.date()
    elif join_date is None:
        join_date = today

    monthly_leave = 0
    if retire_date is None:
        diff = relativedelta(today, join_date)
        for idx in range(diff.years):
            if idx <= 1:
                monthly_leave += 15
            else:
                monthly_leave += (idx - 1) + 15
            
    return {
        'id': obj.id,
        'user_id': obj.user_id if obj.user_id is not None else '',  # 사용자 ID
        'password': obj.password if obj.user_id is not None else '',  # 비밀번호
        'name': obj.name if obj.name is not None else '',  # 사용자 이름
        'employee_code': obj.employee_code if obj.employee_code is not None else '',  # 사용자 사번
        'email': obj.email if obj.email is not None else '',
        'phone': obj.phone if obj.phone is not None else '',
        'address': obj.address if obj.address is not None else '',
        'hire_type': obj.hire_type if obj.hire_type is not None else '',
        'join_date': obj.join_date if obj.join_date is not None else '',
        'retire_date': obj.retire_date if obj.retire_date is not None else '',
        'monthly_leave': monthly_leave,
        'work_type': obj.work_type if obj.work_type is not None else '',
        'remark': obj.remark if obj.remark is not None else '',
        'is_active': obj.is_active if obj.is_active is not None else '',
        'is_delete': obj.is_delete if obj.is_delete is not None else '',
        'is_staff': obj.is_staff if obj.is_staff is not None else '',
        'is_master': obj.is_master if obj.is_master is not None else '',
        'leave_manage_access': obj.leave_manage_access if obj.leave_manage_access is not None else '',
        'profile_image': obj.profile_image.url if obj.profile_image and obj.profile_image.name else '',
        'seq_order': obj.seq_order if obj.seq_order is not None else '',
        'last_login': obj.last_login.strftime('%Y-%m-%d %H:%M') if obj.last_login else '',
        'working_years': (today - join_date).days // 365,

        'team_id': obj.team.id if obj.team is not None else '',
        'team_name': obj.team.name if obj.team is not None else '',
        'job_title_id': obj.job_title.id if obj.job_title is not None else '',
        'job_title_name': obj.job_title.name if obj.job_title is not None else '',
        'job_level_id': obj.job_level.id if obj.job_level is not None else '',
        'job_level_name': obj.job_level.name if obj.job_level is not None else '',

        'gender': obj.gender if obj.gender is not None else '',
        'rrn': obj.rrn if obj.rrn is not None else '',
        'nation': obj.nation if obj.nation is not None else '',
        'insurance': obj.insurance if obj.insurance is not None else '',
        'account_code': obj.account_code if obj.account_code is not None else '',
        'account_name': obj.account_name if obj.account_name is not None else '',
        'company_card_id': obj.company_card.id if obj.company_card is not None else '',
        'company_card_code': obj.company_card.code if obj.company_card is not None else '',
        'bank_id': obj.bank.id if obj.bank is not None else '',
        'bank_name': obj.bank.name if obj.bank is not None else '',
        'customer_id': obj.customer.id if obj.customer is not None else '',
        'customer_name': obj.customer.name if obj.customer is not None else '',
        'subsidiary_id': obj.subsidiary.id if obj.subsidiary is not None else '',
        'subsidiary_name': obj.subsidiary.name if obj.subsidiary is not None else '',

        'created_by_id': obj.created_by.id if obj.created_by is not None else '',
        'created_by_name': obj.created_by.name if obj.created_by is not None else '',
        'created_at': obj.created_at if obj.created_at is not None else '',
        'company_id': obj.company.id if obj.company is not None else '',
        'company_name': (lambda ci: ci.company_name if ci else '')(obj.company.company_info.first() if obj.company is not None else None),
    
        'menu_access': obj.menu_access if obj.menu_access is not None else '',
    }


class Myinfo_Update(View):
    @transaction.atomic
    def post(self, request):
        try:
            request_user = request.user

            phone = request.POST.get('phone', '')
            email = request.POST.get('email', '')
            address = request.POST.get('address', '')
            current_password = request.POST.get('current_password', None)
            new_password = request.POST.get('new_password', None)
            profile_image = request.FILES.get('profile_image', None)
            profile_image_deleted = request.POST.get("profile_image_deleted") == "true"
            company_change = request.POST.get('company_change', '')

            obj = UserMaster.objects.get(id=request_user.id)

            if current_password and new_password:
                if not obj.check_password(current_password):
                    return JsonResponse({'error': True, 'message': '현재 비밀번호가 일치하지 않습니다.'})
                if len(new_password) < 4:
                    return JsonResponse({'error': True, 'message': '새 비밀번호는 최소 4자 이상이어야 합니다.'})
                obj.set_password(new_password)
                update_session_auth_hash(request, obj)  # 비밀번호 변경 후 세션 유지

            obj.phone = phone
            obj.email = email
            obj.address = address

            if profile_image_deleted:
                # 기본 프로필 이미지 삭제 예외처리
                if obj.profile_image and 'profile_image/profile_default.png' not in obj.profile_image.name:
                    obj.profile_image.delete(save=False)
                obj.profile_image = 'profile_image/profile_default.png'
            elif profile_image:
                obj.profile_image = profile_image

            if company_change:
                if request.user.is_observer:
                    obj.company_id = company_change

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()


        except Exception as e:
            transaction.set_rollback(True)  # 트랜잭션 롤백 후 에러처리
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg})

        context = {
            "obj_id": obj.id
        }
        return JsonResponse(context)


@method_decorator(csrf_exempt, name='dispatch')
class Master_Password_Reset(View):
    @transaction.atomic
    def post(self, request):
        try:
            user_id = request.POST.get('user_id', '')
            password = request.POST.get('password', None)

            obj = UserMaster.objects.filter(user_id=user_id).first()

            if password:
                if len(password) < 4:
                    return JsonResponse({'error': True, 'message': '새 비밀번호는 최소 4자 이상이어야 합니다.'})
                obj.set_password(password)

            obj.updated_by = obj
            obj.updated_at = timezone.now()
            obj.save()


        except Exception as e:
            transaction.set_rollback(True)  # 트랜잭션 롤백 후 에러처리
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg})

        context = {
            "obj_id": obj.id
        }
        return JsonResponse(context)
