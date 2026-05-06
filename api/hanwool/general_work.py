from django.forms import IntegerField
from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.db.models import F, Q, OuterRef, Subquery, Max, Count
from api.models import UserMaster, GeneralWorkOrder, GeneralWorker, GeneralWorkerSalary
from api.lib import Pagenation, get_excep_msg
from django.utils import timezone
from api.factory.factory_lib import get_itemin_code, get_user_info, get_workorder_code
import json
from datetime import date, datetime
from calendar import monthrange
from django.db.models.functions import Coalesce


class GeneralWorkOrder_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')

        qs = GeneralWorkOrder.objects.filter(company=request_user.company).order_by('subsidiary__name', 'customer__name')

        # 키워드 검색
        all_sch = request.GET.get("all_sch", '')
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_condition = (
                        Q(desc1__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

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

        sch_contract_completed = request.GET.get("sch_contract_completed", '')
        if sch_contract_completed == "Y":
            user_count_subquery = GeneralWorker.objects.filter(
                work_order_id = OuterRef('id'), sign_status="진행"
            ).values('work_order_id') \
            .annotate(
                total = Count('id')
            ) \
            .values('total')
            qs = qs.annotate(
                signed_user_total = Coalesce(Subquery(user_count_subquery), 0)
            ) \
            .exclude(signed_user_total__gt=0)
            
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


class GeneralWorkOrder_Create(View):
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
            desc1 = request.POST.get('desc1', '')
            status = request.POST.get('status', '')

            selected_user_json = request.POST.get('selected_user', '[]')
            selected_user_ids = json.loads(selected_user_json)

            # obj 생성 직전, 거래처 중복 검사
            if GeneralWorkOrder.objects.filter(
                    customer_id=customer,
                    company=request_user.company
            ).exists():
                return JsonResponse(
                    {'error': True, 'message': '해당 거래처로 이미 파견관리 데이터가 존재합니다.'},
                    status=400
                )

            obj = GeneralWorkOrder.objects.create(
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
                GeneralWorker.objects.create(
                    work_order=obj,
                    user_id=user_id,
                    sign_status="진행",
                    customer_id=customer,
                    last_work_order=obj.id,

                    created_by=request_user,
                    updated_by=request_user,
                    company=request_user.company,
                )

            # 사용자 정보에도 customer 값부여 (중복근무등록 방지)
            UserMaster.objects.filter(id__in=selected_user_ids).update(customer_id=customer)

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class GeneralWorkOrder_Update(View):
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
            desc1 = request.POST.get('desc1', '')
            status = request.POST.get('status', '')

            selected_user_json = request.POST.get('selected_user', '[]')
            selected_user_ids = json.loads(selected_user_json)

            obj = get_object_or_404(GeneralWorkOrder, pk=int(pk))

            # obj 수정 직전, 거래처 중복 검사 (자기 자신 제외)
            if GeneralWorkOrder.objects.filter(
                    customer_id=customer,
                    company=request_user.company
            ).exclude(pk=obj.pk).exists():
                return JsonResponse(
                    {'error': True, 'message': '해당 거래처로 이미 파견관리 데이터가 존재합니다.'},
                    status=400
                )

            obj.manager_id = manager
            obj.subsidiary_id = subsidiary
            obj.customer_id = customer
            obj.desc1 = desc1
            obj.status = status

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            # 기존 근로자 명단 검토하여 추가 혹은 삭제 처리
            existing_worker_ids = list(
                GeneralWorker.objects.filter(work_order=obj).values_list('user_id', flat=True)
            )
            to_add = set(selected_user_ids) - set(existing_worker_ids)
            to_delete = set(existing_worker_ids) - set(selected_user_ids)

            # sign_status="완료" → work_order만 None, 그 외 → 삭제
            if to_delete:
                # 완료자는 연결만 해제 (급여정보도 해제)
                completed_workers = GeneralWorker.objects.filter(
                    work_order=obj, user_id__in=to_delete, sign_status="완료"
                )
                for w in completed_workers:
                    GeneralWorkerSalary.objects.filter(worker=w).update(worker=None)
                    w.last_work_order = obj.id
                    w.work_order = None
                    w.updated_by = request_user
                    w.save()

                # 미완료자는 삭제
                GeneralWorker.objects.filter(
                    work_order=obj, user_id__in=to_delete
                ).exclude(sign_status="완료").delete()

                # 사용자정보에도 customer값 제거
                UserMaster.objects.filter(id__in=to_delete).update(customer_id=None)

            # 새로 추가
            for user_id in to_add:
                new_worker = GeneralWorker.objects.create(
                    work_order=obj,
                    user_id=user_id,
                    sign_status="진행",
                    customer_id=customer,
                    last_work_order=obj.id,

                    created_by=request_user,
                    updated_by=request_user,
                    company=request_user.company,
                )

                # 기존 정규직 급여정보 연결 (아래 4가지 필터 조건에 맞으면 연결)
                GeneralWorkerSalary.objects.filter(
                    user_id=user_id,
                    worker__isnull=True,
                    work_order=obj,
                    company=request_user.company,
                ).update(worker=new_worker)

            # 사용자정보에도 customer 값부여 (중복근무등록 방지)
            UserMaster.objects.filter(id__in=selected_user_ids).update(customer_id=customer)

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class GeneralWorkOrder_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(GeneralWorkOrder, pk=int(pk))

            # 해당 work_order에 포함된 사용자정보에도 customer값 제거
            worker_ids = list(
                GeneralWorker.objects.filter(work_order=obj, company=request.user.company)
                .values_list('user_id', flat=True)
            )
            UserMaster.objects.filter(
                id__in=worker_ids, customer_id=obj.customer_id, company=request.user.company,
            ).update(customer_id=None)

            # 전자서명이 완료된 항목들은 worker_list 항목들 연결해제
            GeneralWorker.objects.filter(work_order=obj, sign_status="완료").update(work_order=None)

            # 전자서명이 완료되지 않은 worker_list 항목들도 제거
            GeneralWorker.objects.filter(work_order=obj).exclude(sign_status="완료").delete()

            obj.delete()

            context = {'success': True}
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


def get_obj(obj):
    selected_user = GeneralWorker.objects.filter(work_order_id=obj.id).count()
    signed_user = GeneralWorker.objects.filter(work_order_id=obj.id, sign_status="완료").count()

    return {
        'id': obj.id,
        'desc1': obj.desc1 or '',
        'status': obj.status or '',

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


class GeneralWorker_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')

        qs = GeneralWorker.objects.filter(company=request_user.company).order_by('id')

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
                        Q(desc1__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        # 기간 검색
        if fr_date:
            qs = qs.filter(start_date__gte=fr_date)
        if to_date:
            qs = qs.filter(start_date__lte=to_date)

        # DOID(workorder id) 필터
        DOID = request.GET.get('DOID', '')
        if DOID:
            qs = qs.filter(work_order_id=DOID)
        else:
            qs = qs.order_by('-start_date')

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


class GeneralWorker_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(GeneralWorker, pk=int(pk))
            obj.delete()

            context = {'success': True}
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


def get_obj_worker(obj):
    work_order = obj.work_order
    if not work_order:
        work_order = GeneralWorkOrder.objects.filter(id=obj.last_work_order).first()

    return {
        'id': obj.id,
        'user': get_user_info(obj.user) if obj.user else '',
        'start_date': obj.start_date or '',
        'end_date': obj.end_date or '',
        'date': obj.date.strftime('%Y-%m-%d %H:%M') if obj.date else '',
        'desc1': obj.desc1 or '',
        'status': obj.sign_status or '',
        'image': obj.image.url if obj.image and obj.image.name else '',
        'last_work_order': obj.last_work_order or '',
        'doc_url': obj.doc.url if obj.doc and obj.doc.name else '',
        'doc_name': obj.doc.name if obj.doc and obj.doc.name else '',
        'pdf_url': obj.pdf.url if obj.pdf and obj.pdf.name else '',
        'pdf_name': obj.pdf.name if obj.pdf and obj.pdf.name else '',

        'work_order_id': work_order.id if work_order is not None else '',
        'subsidiary_id': work_order.subsidiary.id if work_order and work_order.subsidiary is not None else '',
        'subsidiary_name': work_order.subsidiary.name if work_order and work_order.subsidiary is not None else '',
        'customer_id': work_order.customer.id if work_order and work_order.customer is not None else '',
        'customer_name': work_order.customer.name if work_order and work_order.customer is not None else '',
        'job_title_name': obj.user.job_title.name if obj.user and obj.user.job_title is not None else '',

        'created_by': get_user_info(obj.created_by) if obj.created_by else '',
        'updated_by': get_user_info(obj.updated_by) if obj.updated_by else '',
        'created_at': obj.created_at.strftime('%Y-%m-%d') if obj.created_at else '',
        'updated_at': obj.updated_at.strftime('%Y-%m-%d') if obj.updated_at else '',
        'company_id': obj.company.id if obj.company is not None else '',
        'company_name': obj.company.company_info.first().company_name if obj.company.company_info.exists() else '',
    }


class GeneralWorker_Contract(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            save_data = json.loads(request.POST.get('save_data', '[]'))
            doc_clear_map = json.loads(request.POST.get('doc_clear_map', '{}'))

            for item in save_data:
                worker_id = item.get('worker_id')
                start_date = item.get('start_date')
                end_date = item.get('end_date')
                doc = request.FILES.get(f'doc_file_{worker_id}', None)
                doc_clear = doc_clear_map.get(worker_id, False)

                if not worker_id:
                    continue  # 데이터가 부족한 항목은 건너뜀

                obj = GeneralWorker.objects.get(pk=int(worker_id))
                obj.start_date = start_date
                obj.end_date = end_date

                if doc_clear and obj.doc:
                    obj.doc.delete(save=False)
                    obj.doc = None
                if doc:
                    obj.doc = doc

                obj.updated_at = timezone.now()
                obj.save()

            context = {'success': True}
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


# 보험 비율 (제조직 / 물류직)
MANUFACTURING_INSURANCE = [
    {"k": "mgmt", "name": "관리비", "rate": 0.06},
    {"k": "pension", "name": "국민연금", "rate": 0.0475},
    {"k": "health", "name": "건강보험", "rate": 0.03595},
    {"k": "emp", "name": "고용보험", "rate": 0.0155},
    {"k": "acc", "name": "산재보험", "rate": 0.00964},   # 제조업 비율
    {"k": "ltc", "name": "장기요양", "rate": 0.1314},   # 건강보험 × 12.95%
    {"k": "retire", "name": "퇴직적립금", "rate": 0.083},
    
]

LOGISTICS_INSURANCE = [
    {"k": "mgmt", "name": "관리비", "rate": 0.06},
    {"k": "pension", "name": "국민연금", "rate": 0.0475},
    {"k": "health", "name": "건강보험", "rate": 0.03595},
    {"k": "emp", "name": "고용보험", "rate": 0.0155},
    {"k": "acc", "name": "산재보험", "rate": 0.00964},    # 물류업 비율
    {"k": "ltc", "name": "장기요양", "rate": 0.1314},   # 건강보험 × 12.95%
    {"k": "retire", "name": "퇴직적립금", "rate": 0.083},
]

class GeneralWorkerSalary_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        sch_year = request.GET.get('sch_year', '')
        sch_month = request.GET.get('sch_month', '')
        sch_customer = request.GET.get('sch_customer', '')
        work_order = request.GET.get('work_order', '')

        if not (sch_year.isdigit() and sch_month.isdigit()):
            return JsonResponse({'results': []}, safe=False)

        # work_order 값 없으면 → 바로 빈 배열 리턴
        if not str(work_order).isdigit():
            return JsonResponse({'results': []}, safe=False)

        sch_year_i = int(sch_year)
        sch_month_i = int(sch_month)
        target_date = date(sch_year_i, sch_month_i, 1)
        days = monthrange(sch_year_i, sch_month_i)[1]
        blank = [None] * days

        # 근로자 목록 필터
        workers_qs = GeneralWorker.objects.filter(work_order_id=work_order, company=request_user.company)
        if sch_customer and str(sch_customer).isdigit():
            workers_qs = workers_qs.filter(customer_id=int(sch_customer))

        # 키워드 검색
        all_sch = request.GET.get("all_sch", '')
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_condition = (
                        Q(user__name__icontains=keyword)
                    )
                    search_conditions |= search_condition
            workers_qs = workers_qs.filter(search_conditions)

        # 해당 월의 기존 급여 데이터 미리 조회
        salary_map = {
            s.worker_id: s for s in GeneralWorkerSalary.objects.filter(
                company=request_user.company,
                date=target_date
            )
        }

        # work_order 객체 미리 조회 (보험 분기용)
        work_order_obj = get_object_or_404(GeneralWorkOrder, id=work_order)

        # 보험 분기 처리
        if work_order_obj.customer.general_work_type == "제조직":
            default_insurance = MANUFACTURING_INSURANCE
        elif work_order_obj.customer.general_work_type == "물류직":
            default_insurance = LOGISTICS_INSURANCE
        else:
            default_insurance = MANUFACTURING_INSURANCE  # fallback

        results = []
        for w in workers_qs.select_related('user'):
            salary_obj = salary_map.get(w.id)  # 있으면 불러오기

            results.append({
                'id': salary_obj.id if salary_obj else None,
                'date': target_date,
                'year': sch_year_i,
                'month': sch_month_i,
                'hourly_rate': getattr(salary_obj, 'hourly_rate', 0),
                'extra_price': getattr(salary_obj, 'extra_price', 0),
                'extra_price2': getattr(salary_obj, 'extra_price2', 0),  # 기타직접비2
                'extra_indirect_price': getattr(salary_obj, 'extra_indirect_price', 0),
                'extra_indirect_price2': getattr(salary_obj, 'extra_indirect_price2', 0),
                'etc_price': getattr(salary_obj, 'etc_price', 0),
                'sum_price': getattr(salary_obj, 'sum_price', 0),
                'final_price': getattr(salary_obj, 'final_price', 0),

                'user': get_user_info(w.user) if getattr(w, 'user', None) else None,
                'worker_id': w.id,
                'worker_name': getattr(w, 'name', ''),
                'work_order': w.work_order_id,

                'work_data': getattr(salary_obj, 'work_data', blank[:]),
                'ot_data': getattr(salary_obj, 'ot_data', blank[:]),
                'night_data': getattr(salary_obj, 'night_data', blank[:]),
                'sat_data': getattr(salary_obj, 'sat_data', blank[:]),
                'sat_ot_data': getattr(salary_obj, 'sat_ot_data', blank[:]),
                'weekly_data': getattr(salary_obj, 'weekly_data', blank[:]),
                'etc_data': getattr(salary_obj, 'etc_data', blank[:]),
                'annual_data': getattr(salary_obj, 'annual_data', blank[:]),
                'insurance_data': getattr(salary_obj, 'insurance_data', default_insurance),
                'default_insurance': default_insurance,

                'company_id': request_user.company.id if request_user.company else None,
                'company_name': (
                    request_user.company.company_info.first().company_name
                    if request_user.company and request_user.company.company_info.exists()
                    else ''
                ),
            })

        return JsonResponse({'results': results}, safe=False)


class GeneralWorkerSalary_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            salary_json = request.POST.get('salary_data', '[]')
            data = json.loads(salary_json)

            for rec in data:
                worker_obj = get_object_or_404(GeneralWorker, id=rec.get('worker_id'), company=request_user.company)

                date_str = rec.get('date')
                if not date_str:
                    y, m = rec.get('year'), rec.get('month')
                    if y and m:
                        date_str = f"{int(y):04d}-{int(m):02d}-01"
                if not date_str:
                    raise ValueError("date 값이 없습니다.")
                save_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                GeneralWorkerSalary.objects.update_or_create(
                    company=request_user.company,
                    worker=worker_obj,
                    work_order_id=rec.get('work_order_id'),
                    user_id=worker_obj.user.id,
                    date=save_date,
                    defaults={
                        'sum_price': rec.get('sum_price', 0),  # 직접비
                        'extra_price': rec.get('extra_price', 0),  # 기타 직접비1
                        'extra_price2': rec.get('extra_price2', 0),  # 기타 직접비2
                        'insurance_data': rec.get('insurance_data', []),
                        'profit': rec.get('mgmt_price', 0),
                        'extra_indirect_price': rec.get('extra_indirect_price', 0),  # 기타 직접비1
                        'extra_indirect_price2': rec.get('extra_indirect_price2', 0),  # 기타 직접비2
                        'final_price': rec.get('final_price', 0),  # 총 청구액
                        'created_by': request_user,
                        'updated_by': request_user,
                    }
                )

            return JsonResponse({'success': True})

        except Exception as e:
            transaction.set_rollback(True)
            return JsonResponse({'error': True, 'message': str(e)}, status=500)


# # 기존 시급별/일급별 급여정산방식
# class GeneralWorkerSalary_Update(View):
#     @transaction.atomic
#     def post(self, request, *args, **kwargs):
#         try:
#             request_user = get_object_or_404(UserMaster, id=request.user.id)
#             salary_json = request.POST.get('salary_data', '[]')
#             data = json.loads(salary_json)
#
#             for rec in data:
#                 worker_obj = get_object_or_404(GeneralWorker, id=rec.get('worker_id'), company=request_user.company)
#
#                 date_str = rec.get('date')
#                 if not date_str:
#                     y, m = rec.get('year'), rec.get('month')
#                     if y and m:
#                         date_str = f"{int(y):04d}-{int(m):02d}-01"
#                 if not date_str:
#                     raise ValueError("date 값이 없습니다.")
#                 save_date = datetime.strptime(date_str, "%Y-%m-%d").date()
#
#                 GeneralWorkerSalary.objects.update_or_create(
#                     company=request_user.company,
#                     worker=worker_obj,
#                     work_order_id=rec.get('work_order_id'),
#                     user_id=worker_obj.user.id,
#                     date=save_date,
#                     defaults={
#                         'hourly_rate': rec.get('hourly_rate', 0),
#                         'extra_price': rec.get('extra_price', 0),  # 직접인건비 기타금액
#                         'etc_price': rec.get('etc_price', 0),      # 간접비 기타금액
#                         'work_data': rec.get('work_data', []),
#                         'ot_data': rec.get('ot_data', []),
#                         'night_data': rec.get('night_data', []),
#                         'sat_data': rec.get('sat_data', []),
#                         'sat_ot_data': rec.get('sat_ot_data', []),
#                         'weekly_data': rec.get('weekly_data', []),
#                         'etc_data': rec.get('etc_data', []),
#                         'annual_data': rec.get('annual_data', []),
#                         'insurance_data': rec.get('insurance_data', []),
#                         'sum_price': rec.get('sum_price', 0),
#                         'final_price': rec.get('final_price', 0),
#                         'profit': rec.get('mgmt_price', 0),
#                         'created_by': request_user,
#                         'updated_by': request_user,
#                     }
#                 )
#
#             return JsonResponse({'success': True})
#
#         except Exception as e:
#             transaction.set_rollback(True)
#             return JsonResponse({'error': True, 'message': str(e)}, status=500)


from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
@method_decorator(csrf_exempt, name='dispatch')
class GeneralWorker_Sign(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            pk = request.POST.get('pk', '')
            work_order_id = request.POST.get('work_order_id', '')

            image_file = request.FILES.get('image')
            pdf = request.FILES.get('pdf')
            start_date = request.POST.get('start_date', '')
            end_date = request.POST.get('end_date', '')
            if not image_file:
                return JsonResponse({'error': True, 'message': "전자서명이 정상적으로 전송되지 않았습니다."})

            obj = get_object_or_404(GeneralWorker, pk=int(pk))

            obj.sign_status = "완료"
            obj.image = image_file
            obj.pdf = pdf
            if start_date:
                obj.start_date = start_date
            if end_date:
                obj.end_date = end_date
            obj.date = timezone.now()

            obj.updated_at = timezone.now()
            obj.save()

            context = {'error': False, 'success': True}
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)
