from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q
from api.models import UserMaster, FactoryCustomer
from api.lib import Pagenation, get_excep_msg
from django.utils import timezone
from api.factory.factory_lib import get_customer_code
import json


class FactoryCustomer_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')

        qs = FactoryCustomer.objects.filter(company=request_user.company).order_by('code')

        # 사용여부 필터
        sch_customer_type = request.GET.get('sch_customer_type', '')
        if sch_customer_type == "공급사":
            qs = qs.filter(customer_type="공급사")
        elif sch_customer_type == "고객사":
            qs = qs.filter(customer_type="고객사")
        elif sch_customer_type == "공급사&고객사":
            qs = qs.filter(customer_type="공급사&고객사")

        # 키워드 검색
        all_sch = request.GET.get("all_sch", '')
        if all_sch:
            search_keywords = all_sch.split(',')
            search_conditions = Q()
            for keyword in search_keywords:
                keyword = keyword.strip()
                if keyword:
                    search_condition = (
                        Q(name__icontains=keyword) |
                        Q(code__icontains=keyword) |
                        Q(desc1__icontains=keyword) |
                        Q(address__icontains=keyword) |
                        Q(type__icontains=keyword) |
                        Q(item__icontains=keyword) |
                        Q(charge_name__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        # sch_customer_class 필터
        sch_customer_class = request.GET.get('sch_customer_class', '')
        if sch_customer_class:
            qs = qs.filter(customer_class_id=sch_customer_class)

        # sch_customer 필터
        sch_customer = request.GET.get('sch_customer', '')
        if sch_customer:
            qs = qs.filter(id=sch_customer)

        # sch_subsidiary 필터
        sch_subsidiary = request.GET.get('sch_subsidiary', '')
        if sch_subsidiary:
            qs = qs.filter(subsidiary_code_id=sch_subsidiary)

        # center 필터
        center = request.GET.get('center') == 'true'
        if center:
            qs = qs.exclude(customer_class__name="관리법인")

        # select로 특정 아이템 호출
        select = request.GET.get('select', '')
        if select:
            qs = FactoryCustomer.objects.filter(id=select, company=request_user.company)

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


class FactoryCustomer_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)

            code = request.POST.get('code', '')
            name = request.POST.get('name', '')
            desc1 = request.POST.get('desc1', '')
            license = request.POST.get('license', '')
            owner_name = request.POST.get('owner_name', '')
            charge_name = request.POST.get('charge_name', '')
            address = request.POST.get('address', '')
            type = request.POST.get('type', '')
            item = request.POST.get('item', '')
            tel = request.POST.get('tel', '')
            fax = request.POST.get('fax', '')
            email = request.POST.get('email', '')
            mobile = request.POST.get('mobile', '')
            # customer_type = request.POST.get('customer_type', '')
            desc2 = request.POST.get('desc2', '')
            desc3 = request.POST.get('desc3', '')
            desc4 = request.POST.get('desc4', '')
            general_work_type = request.POST.get('general_work_type', '')
            image = request.FILES.get('image', None)
            is_valid = request.POST.get('is_valid', '').lower() == 'true'

            manager_id = request.POST.get('manager', None)
            manager_id = int(manager_id) if manager_id.isdigit() else None
            customer_class_id = request.POST.get('customer_class', None)
            customer_class_id = int(customer_class_id) if customer_class_id.isdigit() else None
            default_wage_id = request.POST.get('default_wage', None)
            default_wage_id = int(default_wage_id) if default_wage_id.isdigit() else None
            subsidiary_id = request.POST.get('subsidiary', None)
            subsidiary_id = int(subsidiary_id) if subsidiary_id.isdigit() else None

            if not code:
                code = get_customer_code(request_user.company)

            obj = FactoryCustomer.objects.create(
                code=code,
                name=name,
                desc1=desc1,
                license=license,
                owner_name=owner_name,
                charge_name=charge_name,
                address=address,
                type=type,
                item=item,
                tel=tel,
                fax=fax,
                email=email,
                mobile=mobile,
                # customer_type=customer_type,
                manager_id=manager_id,
                customer_class_id=customer_class_id,
                default_wage_id=default_wage_id,
                desc2=desc2,
                desc3=desc3,
                desc4=desc4,
                general_work_type=general_work_type,
                image=image,
                is_valid=is_valid,
                subsidiary_code_id=subsidiary_id,

                created_by=request_user,
                updated_by=request_user,
                created_at=timezone.now().date(),
                updated_at=timezone.now().date(),
                company=request_user.company,
            )

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class FactoryCustomer_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            code = request.POST.get('code', '')
            name = request.POST.get('name', '')
            desc1 = request.POST.get('desc1', '')
            license = request.POST.get('license', '')
            owner_name = request.POST.get('owner_name', '')
            charge_name = request.POST.get('charge_name', '')
            address = request.POST.get('address', '')
            type = request.POST.get('type', '')
            item = request.POST.get('item', '')
            tel = request.POST.get('tel', '')
            fax = request.POST.get('fax', '')
            email = request.POST.get('email', '')
            mobile = request.POST.get('mobile', '')
            # customer_type = request.POST.get('customer_type', '')
            desc2 = request.POST.get('desc2', '')
            desc3 = request.POST.get('desc3', '')
            desc4 = request.POST.get('desc4', '')
            general_work_type = request.POST.get('general_work_type', '')
            image = request.FILES.get('image', None)
            image_clear = request.POST.get('image_clear', 'false') == 'true'
            is_valid = request.POST.get('is_valid', '').lower() == 'true'

            manager_id = request.POST.get('manager', None)
            manager_id = int(manager_id) if manager_id.isdigit() else None
            customer_class_id = request.POST.get('customer_class', None)
            customer_class_id = int(customer_class_id) if customer_class_id.isdigit() else None
            default_wage_id = request.POST.get('default_wage', None)
            default_wage_id = int(default_wage_id) if default_wage_id.isdigit() else None
            subsidiary_id = request.POST.get('subsidiary', None)
            subsidiary_id = int(subsidiary_id) if subsidiary_id.isdigit() else None

            if not code:
                code = get_customer_code(request_user.company)

            obj = get_object_or_404(FactoryCustomer, pk=int(pk))

            obj.code = code
            obj.name = name
            obj.desc1 = desc1
            obj.license = license
            obj.owner_name = owner_name
            obj.charge_name = charge_name
            obj.address = address
            obj.type = type
            obj.item = item
            obj.tel = tel
            obj.fax = fax
            obj.email = email
            obj.mobile = mobile
            # obj.customer_type = customer_type
            obj.manager_id = manager_id
            obj.customer_class_id = customer_class_id
            obj.default_wage_id = default_wage_id
            obj.desc2 = desc2
            obj.desc3 = desc3
            obj.desc4 = desc4
            obj.general_work_type = general_work_type
            obj.is_valid = is_valid
            obj.subsidiary_code_id = subsidiary_id

            if image_clear and obj.image:
                obj.image.delete(save=False)
                obj.image = None

            if image:
                obj.image = image

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class FactoryCustomer_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(FactoryCustomer, pk=int(pk))
            if obj.image:
                obj.image.delete(save=False)
            obj.delete()

            context = {'success': True}
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


def get_obj(obj):
    return {
        'id': obj.id,
        'name': obj.name or '',
        'code': obj.code or '',
        'desc1': obj.desc1 or '',
        'desc2': obj.desc2 or '',
        'desc3': obj.desc3 or '',
        'desc4': obj.desc4 or '',
        'general_work_type': obj.general_work_type or '',
        'license': obj.license or '',
        'owner_name': obj.owner_name or '',
        'charge_name': obj.charge_name or '',
        'address': obj.address or '',
        'type': obj.type or '',
        'item': obj.item or '',
        'tel': obj.tel or '',
        'fax': obj.fax or '',
        'email': obj.email or '',
        'mobile': obj.mobile or '',
        'customer_type': obj.customer_type or '',
        'image': obj.image.url if obj.image and obj.image.name else '',

        'manager': get_user_info(obj.manager) if obj.manager else '',
        'customer_class_id': obj.customer_class.id if obj.customer_class is not None else '',
        'customer_class_name': obj.customer_class.name if obj.customer_class is not None else '',
        'default_wage_id': obj.default_wage.id if obj.default_wage is not None else '',
        'default_wage_name': obj.default_wage.name if obj.default_wage is not None else '',
        'default_wage_desc1': obj.default_wage.desc1 if obj.default_wage is not None else '',
        'daily_field': obj.daily_field or '',
        'is_valid': obj.is_valid,
        'subsidiary_id': obj.subsidiary_code.id if obj.subsidiary_code is not None else '',
        'subsidiary_name': obj.subsidiary_code.name if obj.subsidiary_code is not None else '',

        'created_by': get_user_info(obj.created_by) if obj.created_by else '',
        'updated_by': get_user_info(obj.updated_by) if obj.updated_by else '',
        'created_at': obj.created_at.strftime('%Y-%m-%d') if obj.created_at else '',
        'updated_at': obj.updated_at.strftime('%Y-%m-%d') if obj.updated_at else '',
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


# 거래처의 급여항목 설정
class FactoryCustomerSalary_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            salary_data = json.loads(request.POST.get('salary_data', '[]'))

            for row in salary_data:
                pk = row.get('id')
                daily_field = row.get('daily_field', [])

                if not pk:
                    continue

                obj = get_object_or_404(FactoryCustomer, pk=int(pk))
                obj.daily_field = daily_field
                obj.save()

            return JsonResponse({'success': True, 'message': '저장되었습니다.'})

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)