from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, OuterRef, Subquery, Max
from api.models import UserMaster, FactoryItemIn, DailyWorkOrder, DailyWorker
from api.lib import Pagenation, get_excep_msg
from django.utils import timezone
from api.factory.factory_lib import get_itemin_code, get_user_info, get_workorder_code
import json
from datetime import timedelta
import calendar
from django.utils.dateparse import parse_date


class DailyWorkOrder_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')

        qs = DailyWorkOrder.objects.filter(company=request_user.company).order_by('-date', '-created_at')

        # 키워드 검색
        all_sch = request.GET.get("all_sch", '')
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_condition = (
                        Q(code__icontains=keyword) |
                        Q(desc1__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        # 기간 검색
        if fr_date:
            qs = qs.filter(date__gte=fr_date)
        if to_date:
            qs = qs.filter(date__lte=to_date)

        # sch_subsidiary 필터
        sch_subsidiary = request.GET.get('sch_subsidiary', '')
        if sch_subsidiary:
            qs = qs.filter(subsidiary_id=sch_subsidiary)

        # sch_customer 필터
        sch_customer = request.GET.get('sch_customer', '')
        if sch_customer:
            qs = qs.filter(customer_id=sch_customer)

        # sch_manager 필터
        sch_manager = request.GET.get('sch_manager', '')
        if sch_manager:
            qs = qs.filter(manager_id=sch_manager)

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

        context = {
            'count': qs_ps.paginator.count,
            'previous': url_pre,
            'next': url_next,
            'results': results,
        }

        return JsonResponse(context, safe=False)


class DailyWorkOrder_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)

            manager = request.POST.get('manager', '')
            manager = int(manager) if manager.isdigit() else None
            subsidiary = request.POST.get('subsidiary', '')
            subsidiary = int(subsidiary) if subsidiary.isdigit() else None
            customer = request.POST.get('customer', '')
            customer = int(customer) if customer.isdigit() else None
            date = request.POST.get('date', None) or None
            desc1 = request.POST.get('desc1', '')
            status = request.POST.get('status', '')

            selected_user_json = request.POST.get('selected_user', '[]')
            selected_user_ids = json.loads(selected_user_json)

            code = get_workorder_code(request_user.company)

            obj = DailyWorkOrder.objects.create(
                code=code,
                date=date,
                manager_id=manager,
                subsidiary_id=subsidiary,
                customer_id=customer,
                desc1=desc1,
                status=status,

                created_by=request_user,
                updated_by=request_user,
                created_at=timezone.now().date(),
                updated_at=timezone.now().date(),
                company=request_user.company,
            )

            # 근로자 명단 생성
            for user_id in selected_user_ids:
                DailyWorker.objects.create(
                    work_order=obj,
                    user_id=user_id,
                    sign_status="진행",
                    wage=obj.customer.default_wage,

                    created_by=request_user,
                    updated_by=request_user,
                    company=request_user.company,
                )

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class DailyWorkOrder_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            manager = request.POST.get('manager', '')
            manager = int(manager) if manager.isdigit() else None
            subsidiary = request.POST.get('subsidiary', '')
            subsidiary = int(subsidiary) if subsidiary.isdigit() else None
            customer = request.POST.get('customer', '')
            customer = int(customer) if customer.isdigit() else None
            date = request.POST.get('date', None) or None
            desc1 = request.POST.get('desc1', '')
            status = request.POST.get('status', '')

            selected_user_json = request.POST.get('selected_user', '[]')
            selected_user_ids = json.loads(selected_user_json)

            obj = get_object_or_404(DailyWorkOrder, pk=int(pk))

            obj.date = date
            obj.manager_id = manager
            obj.subsidiary_id = subsidiary
            obj.customer_id = customer
            obj.desc1 = desc1

            obj.updated_by = request_user
            obj.updated_at = timezone.now()

            # 기존 근로자 명단 검토하여 추가 혹은 삭제 처리
            existing_worker_ids = list(DailyWorker.objects.filter(work_order=obj).values_list('user_id', flat=True))
            to_add = set(selected_user_ids) - set(existing_worker_ids)
            to_delete = set(existing_worker_ids) - set(selected_user_ids)
            DailyWorker.objects.filter(work_order=obj, user_id__in=to_delete).delete()
            for user_id in to_add:
                DailyWorker.objects.create(
                    work_order=obj,
                    user_id=user_id,
                    sign_status="진행",
                    wage=obj.customer.default_wage,

                    created_by=request_user,
                    updated_by=request_user,
                    company=request_user.company,
                )
            if obj.status == status:
                ing_count = DailyWorker.objects.filter(work_order=obj, sign_status='진행').count()
                if ing_count > 0:
                    obj.status = '진행'
                else:
                    obj.status = '완료'
            else:
                obj.status = status
            obj.save()
            
            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class DailyWorkOrder_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(DailyWorkOrder, pk=int(pk))
            obj.delete()

            context = {'success': True}
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


def get_obj(obj):
    selected_user = DailyWorker.objects.filter(work_order_id=obj.id).count()
    signed_user = DailyWorker.objects.filter(work_order_id=obj.id, sign_status="완료").count()

    return {
        'id': obj.id,
        'code': obj.code or '',
        'date': obj.date or '',
        'desc1': obj.desc1 or '',
        'status': obj.status or '',
        'request_price': obj.request_price or 0,
        'pre_result_price': obj.pre_result_price or 0,
        'tax': obj.tax or 0,
        'result_price': obj.result_price or 0,

        'manager': get_user_info(obj.manager) if obj.manager else '',
        'subsidiary_id': obj.subsidiary.id if obj.subsidiary is not None else '',
        'subsidiary_name': obj.subsidiary.name if obj.subsidiary is not None else '',
        'customer_id': obj.customer.id if obj.customer is not None else '',
        'customer_name': obj.customer.name if obj.customer is not None else '',
        'selected_user': selected_user,
        'signed_user': signed_user,

        'created_by': get_user_info(obj.created_by) if obj.created_by else '',
        'updated_by': get_user_info(obj.updated_by) if obj.updated_by else '',
        'created_at': obj.created_at.strftime('%Y-%m-%d') if obj.created_at else '',
        'updated_at': obj.updated_at.strftime('%Y-%m-%d') if obj.updated_at else '',
        'company_id': obj.company.id if obj.company is not None else '',
        'company_name': obj.company.company_info.first().company_name if obj.company.company_info.exists() else '',
    }


class DailyWorker_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')

        qs = DailyWorker.objects.filter(company=request_user.company).order_by('id')

        # 키워드 검색
        all_sch = request.GET.get("all_sch", '')
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_condition = (
                        Q(user__name__icontains=keyword) |
                        Q(user__phone__icontains=keyword) |
                        Q(work_order__code__icontains=keyword) |
                        Q(desc1__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        # 기간 검색
        if fr_date:
            qs = qs.filter(work_order__date__gte=fr_date)
        if to_date:
            qs = qs.filter(work_order__date__lte=to_date)

        # DOID(workorder id) 필터
        DOID = request.GET.get('DOID', '')
        if DOID:
            qs = qs.filter(work_order_id=DOID)
        else:
            qs = qs.order_by('-work_order__date')

        # sch_status 필터
        sch_status = request.GET.get('sch_status', '')
        if sch_status:
            qs = qs.filter(sign_status=sch_status)

        # sch_subsidiary 필터
        sch_subsidiary = request.GET.get('sch_subsidiary', '')
        if sch_subsidiary:
            qs = qs.filter(work_order__subsidiary_id=sch_subsidiary)

        # sch_customer 필터
        sch_customer = request.GET.get('sch_customer', '')
        if sch_customer:
            qs = qs.filter(work_order__customer_id=sch_customer)

        # sch_is_salary_date 필터
        sch_is_salary_date = request.GET.get('sch_is_salary_date', '')
        if sch_is_salary_date == 'true':
            qs = qs.filter(salary_date__isnull=False)
        elif sch_is_salary_date == 'false':
            qs = qs.filter(salary_date__isnull=True)

        # price 필터 (청구액)
        price = request.GET.get('price') == 'true'
        customer_id = request.GET.get('customer_id', '')
        sch_year = request.GET.get('sch_year')
        sch_year = int(sch_year) if sch_year and sch_year.isdigit() else None
        sch_month = request.GET.get('sch_month')
        sch_month = int(sch_month) if sch_month and sch_month.isdigit() else None

        if price and sch_year and sch_month:
            # 해당 월의 마지막 일자 구하기
            last_day = calendar.monthrange(sch_year, sch_month)[1]
            sch_fr_date = f"{sch_year}-{sch_month:02d}-01"
            sch_to_date = f"{sch_year}-{sch_month:02d}-{last_day}"

            qs = qs.filter(work_order__customer_id=customer_id)
            qs = qs.filter(work_order__date__gte=sch_fr_date)
            qs = qs.filter(work_order__date__lte=sch_to_date)
            qs = qs.order_by('work_order__date')

        if _page == '' or _size == '':
            results = [get_obj_worker(row) for row in qs]
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

        results = [get_obj_worker(row) for row in qs_ps]

        context = {
            'count': qs_ps.paginator.count,
            'previous': url_pre,
            'next': url_next,
            'results': results,
        }

        return JsonResponse(context, safe=False)


class DailyWorker_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(DailyWorker, pk=int(pk))
            obj.delete()

            context = {'success': True}
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


def get_obj_worker(obj):
    return {
        'id': obj.id,
        'user': get_user_info(obj.user) if obj.user else '',
        'date': obj.date.strftime('%Y-%m-%d %H:%M') if obj.date else '',
        'desc1': obj.desc1 or '',
        'status': obj.sign_status or '',
        'image': obj.image.url if obj.image and obj.image.name else '',
        'pdf_url': obj.pdf.url if obj.pdf and obj.pdf.name else '',
        'pdf_name': obj.pdf.name if obj.pdf and obj.pdf.name else '',

        'wage_id': obj.wage.id if obj.wage is not None else '',
        'wage_name': obj.wage.name if obj.wage is not None else '',
        'wage_desc1': obj.wage.desc1 if obj.wage is not None else '',
        'wage_price': obj.wage.price if obj.wage is not None else '',

        'worktime_id': obj.worktime.id if obj.worktime is not None else '',
        'worktime_name': obj.worktime.name if obj.worktime is not None else '',

        'base_salary': obj.base_salary if obj else None,
        'extend_salary': obj.extend_salary if obj else None,
        'hanwool': obj.hanwool if obj else None,
        'tax': obj.tax if obj else None,
        'pre_result_price': obj.pre_result_price if obj else None,
        'result_price': obj.result_price if obj else None,
        'salary_date': obj.salary_date if obj else None,

        'late': obj.late if obj.late is not None else None,                 # 지각금
        'ot': obj.ot if obj.ot is not None else None,                       # 초과근무
        'night': obj.night if obj.night is not None else None,              # 야간근무
        'late_ot_night': obj.late_ot_night if obj.late_ot_night is not None else None,  # 지각+초과+야간
        'wk': obj.wk if obj.wk is not None else None,                       # 주휴수당
        'meal': obj.meal if obj.meal is not None else None,                 # 식대
        'tran': obj.tran if obj.tran is not None else None,                 # 교통비
        'early': obj.early if obj.early is not None else None,              # 조출수당
        'full': obj.full if obj.full is not None else None,                 # 만근수당
        'title': obj.title if obj.title is not None else None,              # 직책수당
        'cdc': obj.cdc if obj.cdc is not None else None,                    # CDC
        'extra': obj.extra if obj.extra is not None else None,              # 추가지급액
        'special': obj.special if obj.special is not None else None,        # 특별수당
        'promo': obj.promo if obj.promo is not None else None,              # 프로모션
        'work': obj.work if obj.work is not None else None,                 # 업무수당
        'total': obj.total if obj.total is not None else None,              # 청구금액

        'pension': obj.pension if obj.pension is not None else None,        # 국민연금
        'health': obj.health if obj.health is not None else None,           # 건강보험
        'emp': obj.emp if obj.emp is not None else None,                    # 고용보험
        'acc': obj.acc if obj.acc is not None else None,                    # 산재보험
        'fee': obj.fee if obj.fee is not None else None,                    # 수수료

        'start_time': obj.start_time.strftime('%H:%M') if obj.start_time else None,  # 출근시간
        'end_time': obj.end_time.strftime('%H:%M') if obj.end_time else None,  # 퇴근시간
        'basic_start_time': obj.basic_start_time.strftime('%H:%M') if obj.basic_start_time else None,  # 기준출근시간
        'basic_end_time': obj.basic_end_time.strftime('%H:%M') if obj.basic_end_time else None,  # 기준퇴근시간

        'work_dur': duration_to_hours(obj.work_dur),  # 근무시간
        'basic_work_dur': duration_to_hours(obj.basic_work_dur),  # 기준근무시간
        'ext_dur': duration_to_hours(obj.ext_dur),  # 연장근무시간
        'night_dur': duration_to_hours(obj.night_dur),  # 야간근무시간
        'late_dur': duration_to_hours(obj.late_dur),  # 지각시간
        'early_dur': duration_to_hours(obj.early_dur),  # 조출시간
        'total_dur': duration_to_hours(obj.total_dur),  # 총근무시간

        'work_order_id': obj.work_order.id if obj.work_order is not None else '',
        'work_order_date': obj.work_order.date if obj.work_order and obj.work_order is not None else '',
        'work_order_code': obj.work_order.code if obj.work_order and obj.work_order is not None else '',
        'subsidiary_id': obj.work_order.subsidiary.id if obj.work_order and obj.work_order.subsidiary is not None else '',
        'subsidiary_name': obj.work_order.subsidiary.name if obj.work_order and obj.work_order.subsidiary is not None else '',
        'customer_id': obj.work_order.customer.id if obj.work_order and obj.work_order.customer is not None else '',
        'customer_name': obj.work_order.customer.name if obj.work_order and obj.work_order.customer is not None else '',
        'customer_field': obj.work_order.customer.daily_field if obj.work_order and obj.work_order.customer is not None else '',

        'created_by': get_user_info(obj.created_by) if obj.created_by else '',
        'updated_by': get_user_info(obj.updated_by) if obj.updated_by else '',
        'created_at': obj.created_at.strftime('%Y-%m-%d') if obj.created_at else '',
        'updated_at': obj.updated_at.strftime('%Y-%m-%d') if obj.updated_at else '',
        'company_id': obj.company.id if obj.company is not None else '',
        'company_name': obj.company.company_info.first().company_name if obj.company.company_info.exists() else '',
    }


def duration_to_hours(duration):
    return round(duration.total_seconds() / 3600, 2) if duration else None


class DailyWorker_Wage(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            wage_data = json.loads(request.POST.get('wage_data', '[]'))

            for item in wage_data:
                worker_id = item.get('worker_id')
                wage_id = item.get('wage_id')
                worktime_id = item.get('worktime_id')

                if not worker_id or not wage_id or not worktime_id:
                    continue  # 데이터가 부족한 항목은 건너뜀

                obj = DailyWorker.objects.get(pk=int(worker_id))
                obj.wage_id = wage_id
                obj.worktime_id = worktime_id
                obj.updated_at = timezone.now()
                obj.save()

            context = {'success': True}
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)

class DailyWorker_Completed(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            worker_data = json.loads(request.POST.get('worker_data', '[]'))

            for item in worker_data:
                worker_id = item.get('worker_id')
                wage_id = item.get('wage_id')
                worktime_id = item.get('worktime_id')

                if not worker_id or not wage_id or not worktime_id:
                    continue  # 데이터가 부족한 항목은 건너뜀

                obj = DailyWorker.objects.get(pk=int(worker_id))
                obj.sign_status = "완료"
                obj.wage_id = wage_id
                obj.worktime_id = worktime_id
                obj.date = timezone.now()
                obj.updated_at = timezone.now()
                obj.save()
                
                obj_order = get_object_or_404(DailyWorkOrder, pk=int(obj.work_order_id))
                ing_count = DailyWorker.objects.filter(work_order_id=int(worker_id), sign_status='진행').count()
                if ing_count > 0:
                    obj_order.status = '진행'
                else:
                    obj_order.status = '완료'
                obj_order.save()

            context = {'success': True}
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class DailyWorker_Salary(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            salary_data = json.loads(request.POST.get('salary_data', '[]'))
            work_order_id = request.POST.get('work_order_id', '')
            total_result_price = 0
            total_request_price = 0
            total_pre_result_price = 0
            total_tax = 0

            total_pension = 0
            total_health = 0
            total_emp = 0
            total_acc = 0
            total_hanwool = 0

            for item in salary_data:
                worker_id = item.get('worker_id')
                if not worker_id:
                    continue

                obj = DailyWorker.objects.get(pk=int(worker_id))

                # 시간 필드
                obj.basic_start_time = item.get('basic_start_time') or None
                obj.start_time = item.get('start_time') or None
                obj.basic_end_time = item.get('basic_end_time') or None
                obj.end_time = item.get('end_time') or None

                obj.basic_work_dur = parse_duration(item.get('basic_work_dur'))
                obj.work_dur = parse_duration(item.get('work_dur'))
                obj.ext_dur = parse_duration(item.get('ext_dur'))
                obj.night_dur = parse_duration(item.get('night_dur'))
                obj.late_dur = parse_duration(item.get('late_dur'))
                obj.early_dur = parse_duration(item.get('early_dur'))
                obj.total_dur = parse_duration(item.get('total_dur'))

                # 급여 및 수당
                obj.base_salary = item.get('base_salary') or None
                obj.late = item.get('late') or None
                obj.ot = item.get('ot') or None
                obj.night = item.get('night') or None
                obj.late_ot_night = item.get('late_ot_night') or None
                obj.wk = item.get('wk') or None
                obj.meal = item.get('meal') or None
                obj.tran = item.get('tran') or None
                obj.early = item.get('early') or None
                obj.full = item.get('full') or None
                obj.title = item.get('title') or None
                obj.cdc = item.get('cdc') or None
                obj.extra = item.get('extra') or None
                obj.special = item.get('special') or None
                obj.promo = item.get('promo') or None
                obj.work = item.get('work') or None

                # 공제
                obj.pension = item.get('pension') or None
                obj.health = item.get('health') or None
                obj.emp = item.get('emp') or None
                obj.acc = item.get('acc') or None
                obj.fee = item.get('fee') or None
                obj.total = item.get('total') or None

                # 지급 영역
                obj.hanwool = item.get('hanwool') or None
                obj.pre_result_price = item.get('pre_result_price') or None
                obj.tax = item.get('tax') or None
                obj.result_price = item.get('result_price') or None

                # 기타
                obj.salary_date = item.get('salary_date') or None
                obj.desc1 = item.get('desc1') or ''
                obj.updated_at = timezone.now()
                obj.save()

                total_result_price += float(obj.result_price or 0)
                total_request_price += float(obj.total or 0)
                total_pre_result_price += float(obj.pre_result_price or 0)
                total_tax += float(obj.tax or 0)

                total_pension += float(obj.pension or 0)
                total_health += float(obj.health or 0)
                total_emp += float(obj.emp or 0)
                total_acc += float(obj.acc or 0)

            work_order_obj = get_object_or_404(DailyWorkOrder, pk=int(work_order_id))
            work_order_obj.result_price = total_result_price
            work_order_obj.request_price = total_request_price
            work_order_obj.pre_result_price = total_pre_result_price
            work_order_obj.tax = total_tax
            work_order_obj.profit = total_request_price - total_pre_result_price - total_pension - total_health - total_emp - total_acc
            work_order_obj.save()

            return JsonResponse({'success': True})

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


def parse_duration(val):
    if not val:
        return None
    try:
        return timedelta(hours=float(val))
    except:
        return None


class DailyWorker_SalaryDate(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            salary_data = json.loads(request.POST.get('salary_data', '[]'))

            for item in salary_data:
                worker_id = item.get('worker_id')
                if not worker_id:
                    continue

                obj = DailyWorker.objects.get(pk=int(worker_id))

                salary_date = parse_date(item.get('salary_date'))
                obj.salary_date = salary_date
                obj.updated_at = timezone.now()
                obj.save()

            return JsonResponse({'success': True})

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
@method_decorator(csrf_exempt, name='dispatch')
class DailyWorker_Sign(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            pk = request.POST.get('pk', '')
            work_order_id = request.POST.get('work_order_id', '')

            image_file = request.FILES.get('image')
            pdf = request.FILES.get('pdf')
            worktime_id = request.POST.get('worktime_id', '')
            wage_id = request.POST.get('wage_id', '')
            if not image_file:
                return JsonResponse({'error': True, 'message': "전자서명이 정상적으로 전송되지 않았습니다."})

            obj = get_object_or_404(DailyWorker, pk=int(pk))

            obj.sign_status = "완료"
            obj.image = image_file
            obj.pdf = pdf
            if (worktime_id) :
                obj.worktime_id = worktime_id
            if (wage_id) :
                obj.wage_id = wage_id
            obj.date = timezone.now()

            obj.updated_at = timezone.now()
            obj.save()

            # 전체 근무인원이 서명하면 일일근무 상태가 완료로 변경됨
            """
            work_order_obj = get_object_or_404(DailyWorkOrder, pk=int(work_order_id))
            selected_user = DailyWorker.objects.filter(work_order_id=work_order_obj.id).count()
            signed_user = DailyWorker.objects.filter(work_order_id=work_order_obj.id, sign_status="완료").count()
            if selected_user == signed_user:
                work_order_obj.status = "완료"
                work_order_obj.save()
            """
            work_order_obj = get_object_or_404(DailyWorkOrder, pk=int(work_order_id))
            selected_user = DailyWorker.objects \
                .filter(work_order_id = work_order_obj.id) \
                .exclude(pk = int(pk)) \
                .exclude(sign_status = "완료") \
                .count()
            if selected_user == 0:
                work_order_obj.status = "완료"
                work_order_obj.save()
            context = {'error': False, 'success': True}
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)
