from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from api.models import UserMaster, CompanyInfo, CompanyAccess
from django.utils import timezone
from api.lib import get_excep_msg


class CompanyInfo_Read(View):
    def get(self, request, *args, **kwargs):
        request_user = request.user

        qs = CompanyInfo.objects.filter(company=request_user.company)

        results = [get_obj(row) for row in qs]
        context = {
            'results': results,
        }
        return JsonResponse(context, safe=False)


class CompanyInfo_Update(View):
    @transaction.atomic
    def post(self, request):
        try:
            request_user = request.user

            company_name = request.POST.get('company_name', '')
            ceo = request.POST.get('ceo', None) or None
            found_date = request.POST.get('found_date', None) or None
            license = request.POST.get('license', '')
            approval_email = request.POST.get('approval_email') == "true"
            annual_leave_payment = request.POST.get('annual_leave_payment', '')
            check_in = request.POST.get('check_in', None) or None
            check_out = request.POST.get('check_out', None) or None
            hourly_rate = request.POST.get('hourly_rate', None) or None
            logo = request.FILES.get('logo', None)
            stamp = request.FILES.get("stamp", None)
            logo_delete = request.POST.get("logo_delete") == "true"
            stamp_delete = request.POST.get("stamp_delete") == "true"

            obj = CompanyInfo.objects.get(company=request_user.company)

            obj.company_name = company_name
            obj.ceo_id = ceo
            obj.found_date = found_date
            obj.license = license
            obj.annual_leave_payment = annual_leave_payment
            obj.approval_email = approval_email
            obj.check_in = check_in
            obj.check_out = check_out
            obj.hourly_rate = hourly_rate

            for i in range(1, 6):
                if f'apv_memo_{i}' in request.POST:
                    setattr(obj, f'apv_memo_{i}', request.POST.get(f'apv_memo_{i}', ''))

            if logo_delete:
                obj.logo.delete(save=False)
                obj.logo = None
            elif logo:
                obj.logo = logo

            if stamp_delete:
                obj.stamp.delete(save=False)
                obj.stamp = None
            elif stamp:
                obj.stamp = stamp

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


class ApprovalInfo_Update(View):
    @transaction.atomic
    def post(self, request):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            if not (request_user.is_master or request_user.is_superuser):
                return JsonResponse({"status": "error", "message": "수정 권한이 없습니다."}, status=403)

            category = int(request.POST.get('category', ''))
            apv_memo = request.POST.get('apv_memo', '')

            # 동적 필드명
            field_name = f"apv_memo_{category}"
            update_fields = {field_name: apv_memo}

            CompanyInfo.objects.update_or_create(
                company=request_user.company,
                defaults=update_fields,
            )

            return JsonResponse({"status": "success", "message": "저장되었습니다."})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})


def get_obj(obj):
    return {
        'id': obj.id,
        'company_name': obj.company_name if obj.company_name else None,
        'ceo_id': obj.ceo.id if obj.ceo else None,
        'ceo_name': obj.ceo.name if obj.ceo else None,
        'found_date': obj.found_date if obj.found_date else None,
        'license': obj.license if obj.license else None,
        'logo': obj.logo.url if obj.logo else None,
        'stamp': obj.stamp.url if obj.stamp else None,
        'annual_leave_payment': obj.annual_leave_payment if obj.annual_leave_payment else None,
        'approval_email': obj.approval_email if obj.approval_email else None,
        'check_in': obj.check_in.strftime('%H:%M') if obj.check_in else '',
        'check_out': obj.check_out.strftime('%H:%M') if obj.check_out else None,
        'hourly_rate': obj.hourly_rate or '',
        'apv_memo_1': obj.apv_memo_1 or '',
        'apv_memo_2': obj.apv_memo_2 or '',
        'apv_memo_3': obj.apv_memo_3 or '',
        'apv_memo_4': obj.apv_memo_4 or '',
        'apv_memo_5': obj.apv_memo_5 or '',
    }


class CompanyAccess_Update(View):
    @transaction.atomic
    def post(self, request):
        try:
            request_user = request.user
            menu_factory = request.POST.get('menu_factory') == 'true'

            obj, created = CompanyAccess.objects.get_or_create(
                company=request_user.company,
                defaults={
                    'factory': menu_factory,
                }
            )

            if not created:
                obj.factory = menu_factory
                obj.save()


        except Exception as e:
            transaction.set_rollback(True)  # 트랜잭션 롤백 후 에러처리
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg})

        context = {
            "obj_id": obj.id
        }
        return JsonResponse(context)