from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, OuterRef, Subquery, Max, Sum, Value
from api.models import UserMaster, CodeMaster, MonthlySales, DailyReport, FactoryCustomer, CodeGroup
from api.lib import Pagenation, get_excep_msg
from datetime import datetime, date
from collections import defaultdict
from django.utils import timezone
from api.factory.factory_lib import get_user_info
from django.db.models.functions import TruncDate, TruncMonth, Coalesce
import json


# 센터에 따라 통계처리
class Performance_Data(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        a_year_filter = request.GET.get('a_year_filter', '')
        sch_customer = request.GET.get('sch_customer', '')

        # 기준연도 검증
        try:
            a_year_filter = int(a_year_filter)
        except (ValueError, TypeError):
            return JsonResponse({'error': '기준연도에 오류가 있습니다.'}, status=400)

        # 페이지 안전 처리
        try:
            page = int(_page) if _page else 1
        except ValueError:
            page = 1
        size = int(_size) if _size else 20

        qs = MonthlySales.objects.filter(
            year=a_year_filter,
            company=request_user.company
        ).select_related("customer")

        # 센터 검색 조건 추가
        if sch_customer:
            qs = qs.filter(customer__id__icontains=sch_customer)

        # --- 월별 전체 합계 (그래프 용) ---
        monthly_qs = (
            qs.values('month')
            .annotate(total_price=Coalesce(Sum('total_price'), Value(0.0)))
            .order_by('month')
        )
        monthly_summary = [
            {
                'month': f"{str(a_year_filter)[-2:]}/{str(row['month']).zfill(2)}",
                'total_price': row['total_price'],
            }
            for row in monthly_qs
        ]

        # --- 고객별 연간 총합 (정렬 기준) ---
        customer_total_qs = (
            qs.values('customer_id', 'customer__name')
            .annotate(grand_total=Coalesce(Sum('total_price'), Value(0.0)))
            .order_by('-grand_total')  # 연매출순
        )
        customer_totals = {
            row['customer_id']: {
                'customer_name': row['customer__name'] or '미지정',
                'grand_total': row['grand_total'],
            }
            for row in customer_total_qs
        }
        # 고객 id를 연매출순으로 배열화
        ordered_customer_ids = list(customer_totals.keys())

        # --- 월별 Customer 합계 (테이블 용) ---
        monthly_customer_dict = defaultdict(lambda: defaultdict(float))

        customer_qs = (
            qs.values('month', 'customer_id')
            .annotate(total_price=Coalesce(Sum('total_price'), Value(0.0)))
            .order_by('month', 'customer_id')
        )
        for row in customer_qs:
            month = row['month']
            cust_id = row['customer_id']
            monthly_customer_dict[month][cust_id] += row['total_price'] or 0

        monthly_customer_summary = defaultdict(list)
        for month, cust_data in monthly_customer_dict.items():
            month_key = f"{str(a_year_filter)[-2:]}/{str(month).zfill(2)}"
            # 연매출 순서대로 append
            for cust_id in ordered_customer_ids:
                if cust_id in cust_data:
                    monthly_customer_summary[month_key].append({
                        'customer_id': cust_id,
                        'customer_name': customer_totals[cust_id]['customer_name'],
                        'total_price': cust_data[cust_id],
                        'grand_total': customer_totals[cust_id]['grand_total'],
                    })

        # --- 페이지네이션 (선택적 고객별 상세 리스트) ---
        qs_ordered = qs.order_by('-year', '-month', '-id')
        qs_ps = Pagenation(qs_ordered, size, page)

        pre = page - 1
        url_pre = f"/?page_size={size}&page={pre}" if pre >= 1 else None
        nxt = page + 1
        url_next = f"/?page_size={size}&page={nxt}" if nxt <= qs_ps.paginator.num_pages else None

        results = [get_obj(row) for row in qs_ps]

        context = {
            'count': qs_ps.paginator.count,
            'previous': url_pre,
            'next': url_next,
            'results': results,
            'monthly_summary': monthly_summary,                # 그래프용
            'monthly_customer_summary': monthly_customer_summary,  # 테이블용 (연매출순)
        }
        return JsonResponse(context, safe=False)


# 센터별 취합 기준
def get_obj(obj: MonthlySales):
    return {
        'id': obj.id,
        'year': obj.year,
        'month': obj.month,
        'customer_id': obj.customer.id if obj.customer else None,
        'customer_name': obj.customer.name if obj.customer else "미지정",
        'total_price': obj.total_price or 0,
        'is_send': obj.is_send,
        'is_done': obj.is_done,
        'paid_price': obj.paid_price or 0,
        'paid_date': obj.paid_date,
        'desc1': obj.desc1,
    }


class HumanPerformance_Data(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        a_year_filter = request.GET.get('a_year_filter', '')

        # 기준연도 검증
        try:
            a_year_filter = int(a_year_filter)
        except (ValueError, TypeError):
            return JsonResponse({'error': '기준연도에 오류가 있습니다.'}, status=400)

        # 1. 고객사 조회
        customers = FactoryCustomer.objects.filter(
            company=request_user.company
        ).exclude(customer_class__name="관리법인")

        # 2. 해당 연도의 DailyReport 조회
        reports = DailyReport.objects.filter(
            company=request_user.company,
            date__year=a_year_filter
        )

        # 3. 고객사별 월별 합산 데이터 구조 초기화
        result = {}
        for c in customers:
            cid = str(c.id)
            result[cid] = {
                "id": cid,
                "name": c.name,
                "monthly": {str(m): {"req": 0, "in": 0} for m in range(1, 13)}
            }

        # 4. DailyReport 집계
        for report in reports:
            month = report.date.month
            data_json = report.data or {}

            for cid, worktypes in data_json.items():
                if cid not in result:
                    continue

                for wt in worktypes:
                    # wt = ["물류", 10, 9, 1] 구조
                    if isinstance(wt, list) and len(wt) >= 4:
                        req_val = wt[1]  # 요청인원
                        in_val = wt[2]  # 투입인원
                        result[cid]["monthly"][str(month)]["req"] += req_val
                        result[cid]["monthly"][str(month)]["in"] += in_val

        # 5. 응답 리턴
        return JsonResponse({
            "year": a_year_filter,
            "groups": list(result.values())
        })


class TeamPerformance_Data(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        a_year_filter = request.GET.get('a_year_filter', '')

        try:
            a_year_filter = int(a_year_filter)
        except (ValueError, TypeError):
            return JsonResponse({'error': '기준연도에 오류가 있습니다.'}, status=400)

        # 1. 모든 팀 목록 불러오기
        teams = CodeMaster.objects.filter(
            company=request_user.company,
            group=CodeGroup.TEAM,
            desc1="관리부서"
        )

        # 2. 결과 dict 초기화
        result = {}
        for t in teams:
            result[str(t.id)] = {
                "id": str(t.id),
                "name": t.name,
                "monthly": {str(m): {"req": 0, "in": 0} for m in range(1, 13)}
            }

        # "미분류" 팀 추가
        result["unassigned"] = {
            "id": "unassigned",
            "name": "미분류",
            "monthly": {str(m): {"req": 0, "in": 0} for m in range(1, 13)}
        }

        # 3. 고객사 정보 (팀 매핑용)
        customers = FactoryCustomer.objects.filter(
            company=request_user.company
        ).exclude(customer_class__name="관리법인").select_related("manager__team")

        customer_map = {str(c.id): c for c in customers}

        # 4. DailyReport 조회 및 집계
        reports = DailyReport.objects.filter(
            company=request_user.company,
            date__year=a_year_filter
        )

        for report in reports:
            month = str(report.date.month)
            data_json = report.data or {}

            for cid, worktypes in data_json.items():
                customer = customer_map.get(str(cid))
                if not customer:
                    continue

                team = customer.manager.team if (customer.manager and customer.manager.team) else None
                tid = str(team.id) if team else "unassigned"

                # 안전 처리
                if tid not in result:
                    result[tid] = {
                        "id": tid,
                        "name": team.name if team else "미분류",
                        "monthly": {str(m): {"req": 0, "in": 0} for m in range(1, 13)}
                    }

                for wt in worktypes:
                    if isinstance(wt, list) and len(wt) >= 4:
                        req_val = int(wt[1] or 0)
                        in_val = int(wt[2] or 0)
                        result[tid]["monthly"][month]["req"] += req_val
                        result[tid]["monthly"][month]["in"] += in_val

        # 5. 결과 반환
        return JsonResponse({
            "year": a_year_filter,
            "teams": list(result.values())
        })
