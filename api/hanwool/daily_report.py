from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from api.models import UserMaster, DailyReport, FactoryCustomer, CompanyInfo
from django.utils import timezone
import json


class DailyReport_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        fr_date = request.GET.get('fr_date')

        # 고객사 조회
        customers = FactoryCustomer.objects.filter(
            is_valid=1, company=request_user.company
        ).select_related("customer_class").exclude(customer_class__name="관리법인")

        # 회사 정보 (수정 중 사용자 조회용)
        company_info = CompanyInfo.objects.filter(company=request_user.company).select_related("updating_user").first()
        updating_user_id = company_info.updating_user.id if company_info and company_info.updating_user else None
        updating_user_name = company_info.updating_user.name if company_info and company_info.updating_user else None

        # DailyReport 단일 row 조회
        report = DailyReport.objects.filter(
            company=request_user.company, date=fr_date
        ).first()

        data_json = report.data if report else {}
        manager_json = report.manager if report else {}
        version = report.version if report else 1

        # 회사 소속 모든 매니저 조회
        managers = UserMaster.objects.filter(
            work_type="관리직", is_staff=1, company=request_user.company
        ).order_by('id')

        manager_status = {}
        for m in managers:
            key = str(m.id)
            display_name = f"{m.name} {m.job_level.name}" if m.job_level else m.name
            manager_status[key] = {
                "display": display_name,
                "msg": manager_json.get(key, "")
            }

        # 그룹/센터별 데이터 구성
        groups = {}
        for c in customers:
            group = c.customer_class.name if c.customer_class else "기타"
            center_id = str(c.id)
            center_name = c.name

            if group not in groups:
                groups[group] = {"group": group, "centers": {}}

            groups[group]["centers"][center_id] = {
                "name": center_name,
                "worktypes": data_json.get(center_id, [])
            }

        return JsonResponse({
            "version": version,
            "updating_user": updating_user_name,
            "updating_user_id": updating_user_id,
            "managers": manager_status,
            "groups": list(groups.values()),
        })


# 동시저장 출돌방지용
class DailyReport_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = request.user
            fr_date = request.POST.get('fr_date')

            if not fr_date:
                return JsonResponse({'error': True, 'message': '기준일이 없습니다.'}, status=400)

            # JSON 파싱
            try:
                status_data = json.loads(request.POST.get('status_data', '{}'))  # deltaCenters
            except Exception:
                status_data = {}

            try:
                manager_data = json.loads(request.POST.get('managers', '{}'))  # deltaManagers
            except Exception:
                manager_data = {}

            # 회사 정보 확인 및 잠금
            company_info = CompanyInfo.objects.select_for_update().filter(company=request_user.company).first()
            if not company_info:
                return JsonResponse({'error': True, 'message': '회사 정보가 없습니다.'}, status=404)

            if company_info.updating_user and company_info.updating_user != request_user:
                return JsonResponse({
                    "error": True,
                    "message": f"{company_info.updating_user.name}님이 현재 수정 중입니다. 잠시 후 다시 시도해주세요.",
                }, status=409)

            # === 기존 데이터 가져오기 ===
            obj, _ = DailyReport.objects.select_for_update().get_or_create(
                company=request_user.company,
                date=fr_date,
                defaults={
                    "data": {},
                    "manager": {},
                    "created_by": request_user,
                    "updated_by": request_user,
                }
            )

            original_data = obj.data or {}
            merged_data = dict(original_data)  # deepcopy 개념

            # === 부분 병합 ===
            for center_id, worktype_rows in status_data.items():
                # 빈 값이면 삭제
                if not worktype_rows or not any(r for r in worktype_rows if any(r)):
                    if center_id in merged_data:
                        del merged_data[center_id]
                    continue

                # 정상적인 경우 갱신
                filtered_rows = []
                for r in worktype_rows:
                    work_type = str(r[0]).strip() if len(r) > 0 else ""
                    v1 = int(r[1]) if len(r) > 1 and str(r[1]).isdigit() else 0
                    v2 = int(r[2]) if len(r) > 2 and str(r[2]).isdigit() else 0
                    v3 = int(r[3]) if len(r) > 3 and str(r[3]).isdigit() else 0
                    if work_type or (v1 or v2 or v3):
                        filtered_rows.append([work_type, v1, v2, v3])

                merged_data[center_id] = filtered_rows

            # === 매니저 병합 ===
            merged_manager = obj.manager or {}
            for k, v in manager_data.items():
                if v == "":
                    merged_manager.pop(str(k), None)  # 빈값이면 삭제
                else:
                    merged_manager[str(k)] = v

            # === 최종 저장 ===
            obj.data = merged_data
            obj.manager = merged_manager
            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            # 잠금 해제
            company_info.updating_user = None
            company_info.save()

            return JsonResponse({
                "success": True,
                "message": f"{fr_date} 데이터가 부분 병합되어 저장되었습니다.",
                "data": merged_data
            })

        except Exception as e:
            return JsonResponse({'error': True, 'message': str(e)}, status=500)