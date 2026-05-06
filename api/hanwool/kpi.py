from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, OuterRef, Count, Subquery, Max, Sum, Value
from api.models import CodeGroup, UserMaster, MonthlySales, CompanyCardHistory, Recruit, \
                    GeneralCost, DailyWorker, CodeMaster, FactoryCustomer, DailyWorkOrder, \
                    GeneralWorkerSalary, SalaryMaster, SalaryItem
from api.lib import Pagenation, get_excep_msg
from datetime import datetime, date
from collections import defaultdict
from django.utils import timezone
from api.factory.factory_lib import get_user_info
from django.db.models.functions import ExtractYear, ExtractMonth, Coalesce
from django.db.models import Sum, F, FloatField, ExpressionWrapper
import json
from django.core import serializers

# 거래처에 따라 월별 매출/영업이익 통계처리
class KpiCustomer_Data(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        a_year_filter = request.GET.get('a_year_filter', '')
        sch_customer_class = request.GET.get('sch_customer_class', '')

        # 기준연도 검증
        try:
            a_year_filter = int(a_year_filter)
        except (ValueError, TypeError):
            return JsonResponse({'error': '기준연도에 오류가 있습니다.'}, status=400)

        # 기본 QuerySet
        qs = MonthlySales.objects.filter(
            year=a_year_filter,
            company=request_user.company
        ).select_related("customer__customer_class")

        # 특정 거래처분류 검색
        if sch_customer_class:
            qs = qs.filter(customer__customer_class__id=sch_customer_class)

        # --- 월별 전체 합계 (그래프 용) ---
        monthly_qs = (
            qs.values("month")
            .annotate(
                total_sales=Coalesce(Sum("total_price"), Value(0.0)),
                total_profit=Coalesce(Sum("daily_profit"), Value(0.0)) +
                             Coalesce(Sum("general_profit"), Value(0.0)),
            )
            .order_by("month")
        )
        monthly_summary = [
            {
                "month": f"{str(a_year_filter)[-2:]}/{str(row['month']).zfill(2)}",
                "total_sales": row["total_sales"],      # 매출
                "total_profit": row["total_profit"],    # 영업이익
            }
            for row in monthly_qs
        ]

        # --- 월별 customer_class 합계 (테이블 용) ---
        monthly_class_dict = defaultdict(lambda: defaultdict(lambda: {"sales": 0, "profit": 0}))
        class_qs = (
            qs.values("month", "customer__customer_class_id", "customer__customer_class__name")
            .annotate(
                total_sales=Coalesce(Sum("total_price"), Value(0.0)),
                total_profit=Coalesce(Sum("daily_profit"), Value(0.0)) +
                             Coalesce(Sum("general_profit"), Value(0.0)),
            )
            .order_by("month", "customer__customer_class_id")
        )

        for row in class_qs:
            month = row["month"]
            class_id = row["customer__customer_class_id"]
            class_name = row["customer__customer_class__name"] or "미지정"
            monthly_class_dict[month][class_id]["sales"] += row["total_sales"] or 0
            monthly_class_dict[month][class_id]["profit"] += row["total_profit"] or 0
            monthly_class_dict[month][class_id]["name"] = class_name

        monthly_customer_class_summary = defaultdict(list)
        for month, class_data in monthly_class_dict.items():
            month_key = f"{str(a_year_filter)[-2:]}/{str(month).zfill(2)}"
            for class_id, values in class_data.items():
                monthly_customer_class_summary[month_key].append({
                    "customer_class_id": class_id,
                    "customer_class_name": values["name"],
                    "total_sales": values["sales"],
                    "total_profit": values["profit"],
                })

        context = {
            "monthly_summary": monthly_summary,                              # 그래프용
            "monthly_customer_class_summary": monthly_customer_class_summary # 테이블용
        }
        return JsonResponse(context, safe=False)

# 관리법인에 따라 월별 매출/영업이익/비용/순이익 통계처리
class KpiSubsidiary_Data(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        a_year_filter = request.GET.get('a_year_filter', '')

        try:
            a_year_filter = int(a_year_filter)
        except (ValueError, TypeError):
            return JsonResponse({'error': '기준연도에 오류가 있습니다.'}, status=400)

        # ============================================================== #
        # 1) 매출 & 영업이익 (전체 월별 합산 → monthly_summary)
        # ============================================================== #
        qs = MonthlySales.objects.filter(
            year=a_year_filter,
            company=request_user.company
        )

        monthly_sales_qs = (
            qs.values("month")
            .annotate(
                total_sales=Coalesce(Sum("total_price"), Value(0.0)),
                operating_profit=Coalesce(Sum("daily_profit"), Value(0.0)) +
                                 Coalesce(Sum("general_profit"), Value(0.0)),
            )
            .order_by("month")
        )

        # --- 비용 (전체 합산 dict) ---
        card_qs = CompanyCardHistory.objects.filter(
            date__year=a_year_filter,
            company=request_user.company
        ).values("date__month").annotate(
            total_cost=Coalesce(Sum("price"), Value(0.0))
        )
        card_cost_dict = {row["date__month"]: row["total_cost"] for row in card_qs}

        recruit_qs = Recruit.objects.filter(
            start_date__year=a_year_filter,
            company=request_user.company
        ).values("start_date__month").annotate(
            total_cost=Coalesce(Sum("price"), Value(0.0))
        )
        recruit_cost_dict = {row["start_date__month"]: row["total_cost"] for row in recruit_qs}

        gc_qs = GeneralCost.objects.filter(
            date__year=a_year_filter,
            company=request_user.company
        ).values("date__month").annotate(
            total_cost=Coalesce(Sum("price"), Value(0.0))
        )
        gc_cost_dict = {row["date__month"]: row["total_cost"] for row in gc_qs}

        # --- 최종 monthly_summary ---
        monthly_summary = []
        for month_num in range(1, 13):  # 1월~12월 모두 돌기
            sales_row = next((row for row in monthly_sales_qs if row["month"] == month_num), None)
            sales = sales_row["total_sales"] if sales_row else 0
            op_profit = sales_row["operating_profit"] if sales_row else 0

            total_cost = (
                card_cost_dict.get(month_num, 0) +
                recruit_cost_dict.get(month_num, 0) +
                gc_cost_dict.get(month_num, 0)
            )
            final_profit = op_profit - total_cost
            margin = round((final_profit / sales) * 100, 1) if sales > 0 else 0.0

            monthly_summary.append({
                "month": f"{str(a_year_filter)[-2:]}/{str(month_num).zfill(2)}",
                "total_sales": sales,
                "operating_profit": op_profit,
                "total_cost": total_cost,
                "final_profit": final_profit,
                "margin": margin,
            })

        # ============================================================== #
        # 2) 관리법인별 dict (법인별 상세 통계 → monthly_subsidiary_summary)
        # ============================================================== #
        monthly_subsidiary_dict = defaultdict(lambda: defaultdict(lambda: {
            "sales": 0, "operating_profit": 0,
            "cost": 0, "final_profit": 0, "margin": 0,
            "name": ""
        }))

        # 매출 & 영업이익 (법인별)
        sales_qs = (
            qs.values("month", "subsidiary_id", "subsidiary__name")
            .annotate(
                total_sales=Coalesce(Sum("total_price"), Value(0.0)),
                operating_profit=Coalesce(Sum("daily_profit"), Value(0.0)) +
                                 Coalesce(Sum("general_profit"), Value(0.0)),
            )
        )
        for row in sales_qs:
            m, sid, sname = row["month"], row["subsidiary_id"], row["subsidiary__name"] or "미지정"
            monthly_subsidiary_dict[m][sid]["sales"] += row["total_sales"]
            monthly_subsidiary_dict[m][sid]["operating_profit"] += row["operating_profit"]
            monthly_subsidiary_dict[m][sid]["name"] = sname

        # 비용 (CompanyCardHistory)
        card_qs = CompanyCardHistory.objects.filter(
            date__year=a_year_filter,
            company=request_user.company
        ).values("date__month", "user__subsidiary_id", "user__subsidiary__name").annotate(
            total_cost=Coalesce(Sum("price"), Value(0.0))
        )
        for row in card_qs:
            m, sid, sname = row["date__month"], row["user__subsidiary_id"], row["user__subsidiary__name"] or "미지정"
            monthly_subsidiary_dict[m][sid]["cost"] += row["total_cost"]
            monthly_subsidiary_dict[m][sid]["name"] = sname

        # 비용 (Recruit)
        recruit_qs = Recruit.objects.filter(
            start_date__year=a_year_filter,
            company=request_user.company
        ).values("start_date__month", "user__subsidiary_id", "user__subsidiary__name").annotate(
            total_cost=Coalesce(Sum("price"), Value(0.0))
        )
        for row in recruit_qs:
            m, sid, sname = row["start_date__month"], row["user__subsidiary_id"], row["user__subsidiary__name"] or "미지정"
            monthly_subsidiary_dict[m][sid]["cost"] += row["total_cost"]
            monthly_subsidiary_dict[m][sid]["name"] = sname

        # 비용 (GeneralCost)
        gc_qs = GeneralCost.objects.filter(
            date__year=a_year_filter,
            company=request_user.company
        ).values("date__month", "subsidiary_id", "subsidiary__name").annotate(
            total_cost=Coalesce(Sum("price"), Value(0.0))
        )
        for row in gc_qs:
            m, sid, sname = row["date__month"], row["subsidiary_id"], row["subsidiary__name"] or "미지정"
            monthly_subsidiary_dict[m][sid]["cost"] += row["total_cost"]
            monthly_subsidiary_dict[m][sid]["name"] = sname

        # 순이익 & 이익률 계산 + "전체 법인" 추가
        monthly_subsidiary_summary = defaultdict(list)
        for month, sub_data in monthly_subsidiary_dict.items():
            month_key = f"{str(a_year_filter)[-2:]}/{str(month).zfill(2)}"
            rows = []
            total_sales, total_op, total_cost = 0, 0, 0

            for sub_id, values in sub_data.items():
                sales = values["sales"]
                op_profit = values["operating_profit"]
                cost = values["cost"]
                final_profit = op_profit - cost
                margin = round((final_profit / sales) * 100, 1) if sales > 0 else 0.0

                total_sales += sales
                total_op += op_profit
                total_cost += cost

                rows.append({
                    "subsidiary_id": sub_id,
                    "subsidiary_name": values["name"],
                    "total_sales": sales,
                    "operating_profit": op_profit,
                    "total_cost": cost,
                    "final_profit": final_profit,
                    "margin": margin,
                })

            # --- 전체 법인 행 추가 ---
            final_profit_all = total_op - total_cost
            margin_all = round((final_profit_all / total_sales) * 100, 1) if total_sales > 0 else 0.0
            all_row = {
                "subsidiary_id": "ALL",
                "subsidiary_name": "전체 법인",
                "total_sales": total_sales,
                "operating_profit": total_op,
                "total_cost": total_cost,
                "final_profit": final_profit_all,
                "margin": margin_all,
            }

            rows.sort(key=lambda x: (x["subsidiary_name"] == "미지정", x["subsidiary_name"]))
            monthly_subsidiary_summary[month_key] = [all_row] + rows

        # ============================================================== #
        # 최종 결과
        # ============================================================== #
        context = {
            "monthly_summary": monthly_summary,                       # 전체 법인 합산 (그래프용)
            "monthly_subsidiary_summary": monthly_subsidiary_summary  # 법인별 상세 + 전체 법인
        }
        return JsonResponse(context, safe=False)
   
# 센터에 따라 월별 매출/영업이익/비용/순이익 통계처리
class KpiCenter_Data(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        a_year_filter = request.GET.get('a_year_filter', '')

        try:
            a_year_filter = int(a_year_filter)
        except (ValueError, TypeError):
            return JsonResponse({'error': '기준연도에 오류가 있습니다.'}, status=400)

        # ============================================================== #
        # 1) 매출 & 영업이익 (전체 월별 합산 → monthly_summary)
        # ============================================================== #
        qs = MonthlySales.objects.filter(
            year=a_year_filter,
            company=request_user.company,
            subsidiary__isnull=True,
        )

        monthly_sales_qs = (
            qs.values("month")
            .annotate(
                total_sales=Coalesce(Sum("total_price"), Value(0.0)),
                operating_profit=Coalesce(Sum("daily_profit"), Value(0.0)) +
                                 Coalesce(Sum("general_profit"), Value(0.0)),
            )
            .order_by("month")
        )

        # --- 비용 (전체 합산 dict) ---
        card_qs = CompanyCardHistory.objects.filter(
            date__year=a_year_filter,
            company=request_user.company,
            user__subsidiary__isnull=True
        ).values("date__month").annotate(
            total_cost=Coalesce(Sum("price"), Value(0.0))
        )
        card_cost_dict = {row["date__month"]: row["total_cost"] for row in card_qs}

        recruit_qs = Recruit.objects.filter(
            start_date__year=a_year_filter,
            company=request_user.company,
            subsidiary__isnull=True
        ).values("start_date__month").annotate(
            total_cost=Coalesce(Sum("price"), Value(0.0))
        )
        recruit_cost_dict = {row["start_date__month"]: row["total_cost"] for row in recruit_qs}

        gc_qs = GeneralCost.objects.filter(
            date__year=a_year_filter,
            company=request_user.company,
            subsidiary__isnull=True
        ).values("date__month").annotate(
            total_cost=Coalesce(Sum("price"), Value(0.0))
        )
        gc_cost_dict = {row["date__month"]: row["total_cost"] for row in gc_qs}

        # --- 최종 monthly_summary ---
        monthly_summary = []
        for month_num in range(1, 13):  # 1월~12월 모두 돌기
            sales_row = next((row for row in monthly_sales_qs if row["month"] == month_num), None)
            sales = sales_row["total_sales"] if sales_row else 0
            op_profit = sales_row["operating_profit"] if sales_row else 0

            total_cost = (
                card_cost_dict.get(month_num, 0) +
                recruit_cost_dict.get(month_num, 0) +
                gc_cost_dict.get(month_num, 0)
            )
            final_profit = op_profit - total_cost
            margin = round((final_profit / sales) * 100, 1) if sales > 0 else 0.0

            monthly_summary.append({
                "month": f"{str(a_year_filter)[-2:]}/{str(month_num).zfill(2)}",
                "total_sales": sales,
                "operating_profit": op_profit,
                "total_cost": total_cost,
                "final_profit": final_profit,
                "margin": margin,
            })

        # ============================================================== #
        # 2) 센터별 dict (센터별 상세 통계 → monthly_center_summary)
        # ============================================================== #
        monthly_center_dict = defaultdict(lambda: defaultdict(lambda: {
            "sales": 0, "operating_profit": 0,
            "cost": 0, "final_profit": 0, "margin": 0,
            "name": ""
        }))

        # 매출 & 영업이익 (센터별)
        sales_qs = (
            qs.values("month", "customer_id", "customer__name")
            .annotate(
                total_sales=Coalesce(Sum("total_price"), Value(0.0)),
                operating_profit=Coalesce(Sum("daily_profit"), Value(0.0)) +
                                 Coalesce(Sum("general_profit"), Value(0.0)),
            )
        )
        for row in sales_qs:
            m, sid, sname = row["month"], row["customer_id"], row["customer__name"] or "미지정"
            monthly_center_dict[m][sid]["sales"] += row["total_sales"]
            monthly_center_dict[m][sid]["operating_profit"] += row["operating_profit"]
            monthly_center_dict[m][sid]["name"] = sname

        # 비용 (CompanyCardHistory)
        card_qs = CompanyCardHistory.objects.filter(
            date__year=a_year_filter,
            company=request_user.company,
            user__subsidiary__isnull=True
        ).values("date__month", "user__customer_id", "user__customer__name").annotate(
            total_cost=Coalesce(Sum("price"), Value(0.0))
        )
        for row in card_qs:
            m, sid, sname = row["date__month"], row["user__customer_id"], row["user__customer__name"] or "미지정"
            monthly_center_dict[m][sid]["cost"] += row["total_cost"]
            monthly_center_dict[m][sid]["name"] = sname

        # 비용 (Recruit)
        recruit_qs = Recruit.objects.filter(
            start_date__year=a_year_filter,
            company=request_user.company,
            subsidiary__isnull=True
        ).values("start_date__month", "user__customer_id", "user__customer__name").annotate(
            total_cost=Coalesce(Sum("price"), Value(0.0))
        )
        for row in recruit_qs:
            m, sid, sname = row["start_date__month"], row["user__customer_id"], row["user__customer__name"] or "미지정"
            monthly_center_dict[m][sid]["cost"] += row["total_cost"]
            monthly_center_dict[m][sid]["name"] = sname

        """
        # 비용 (GeneralCost)
        gc_qs = GeneralCost.objects.filter(
            date__year=a_year_filter,
            company=request_user.company,
            subsidiary__isnull=True
        ).values("date__month", "customer_id", "customer__name").annotate(
            total_cost=Coalesce(Sum("price"), Value(0.0))
        )
        for row in gc_qs:
            m, sid, sname = row["date__month"], row["customer_id"], row["customer__name"] or "미지정"
            monthly_center_dict[m][sid]["cost"] += row["total_cost"]
            monthly_center_dict[m][sid]["name"] = sname
        """

        # 순이익 & 이익률 계산 + "전체 법인" 추가
        monthly_center_summary = defaultdict(list)
        for month, sub_data in monthly_center_dict.items():
            month_key = f"{str(a_year_filter)[-2:]}/{str(month).zfill(2)}"
            rows = []
            total_sales, total_op, total_cost = 0, 0, 0

            for sub_id, values in sub_data.items():
                sales = values["sales"]
                op_profit = values["operating_profit"]
                cost = values["cost"]
                final_profit = op_profit - cost
                margin = round((final_profit / sales) * 100, 1) if sales > 0 else 0.0

                total_sales += sales
                total_op += op_profit
                total_cost += cost

                rows.append({
                    "customer_id": sub_id,
                    "customer_name": values["name"],
                    "total_sales": sales,
                    "operating_profit": op_profit,
                    "total_cost": cost,
                    "final_profit": final_profit,
                    "margin": margin,
                })

            # --- 전체 센터 행 추가 ---
            final_profit_all = total_op - total_cost
            margin_all = round((final_profit_all / total_sales) * 100, 1) if total_sales > 0 else 0.0
            all_row = {
                "customer_id": "ALL",
                "customer_name": "전체 센터",
                "total_sales": total_sales,
                "operating_profit": total_op,
                "total_cost": total_cost,
                "final_profit": final_profit_all,
                "margin": margin_all,
            }

            rows.sort(key=lambda x: (x["customer_name"] == "미지정", x["customer_name"]))
            monthly_center_summary[month_key] = [all_row] + rows

        # ============================================================== #
        # 최종 결과
        # ============================================================== #
        context = {
            "monthly_summary": monthly_summary,                       # 전체 법인 합산 (그래프용)
            "monthly_center_summary": monthly_center_summary  # 센터별 상세 + 전체 법인
        }
        
        return JsonResponse(context, safe=False)

class KpiSubsidiary_Summary(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        sch_year = request.GET.get('sch_year', datetime.now().year)
        sch_month = request.GET.get('sch_month', datetime.now().month)
        sch_subsidiary = request.GET.get('sch_subsidiary', "")
        
        try:
            sch_year = int(sch_year)
        except (ValueError, TypeError):
            return JsonResponse({'error': '기준연도에 오류가 있습니다.'}, status=400)
        qs = FactoryCustomer.objects \
            .select_related('customer_class') \
            .filter(customer_class__group = 'customer_class', customer_class__name="관리법인") \
            .order_by('order', 'name') \
            .values()
        if sch_subsidiary:
            qs = qs.filter(id=sch_subsidiary)    
        subsidiary_list = []
        subsidiary_id_list = []
        for row in qs:
            salary_list = []
            if row["name"] == "한울":
                salary_qs = SalaryItem.objects.filter(company=request.user.company)
                if sch_year:
                    salary_qs = salary_qs.filter(salary__year=sch_year)
                salary_qs = salary_qs.annotate(
                    sum_salalry = Coalesce(Sum('real_salary'), Value(0))
                )
                salary_qs = salary_qs.order_by("salary__month") \
                    .values("salary__year", "salary__month", "sum_salalry")
                for salary_row in salary_qs:
                    salary_list.append({
                        "subsidiary_id": row["id"],
                        "year": salary_row["salary__year"],
                        "month": salary_row["salary__month"],
                        "total_cost": salary_row["sum_salalry"],
                    })
            subsidiary_list.append({
                "id": row["id"],
                "code": row["code"],
                "name": row["name"],
                "sum_salalry": salary_list
            })
            subsidiary_id_list.append(row["id"])
        if len(subsidiary_list) == 1:
            sch_subsidiary = subsidiary_list[0]["id"]
        
        daily_sales_qs = DailyWorkOrder.objects \
            .filter(
                subsidiary_id__in=subsidiary_id_list
            ) \
            .values("subsidiary_id") \
            .annotate(
                year = ExtractYear('date'),
                month = ExtractMonth('date'),
                sum_request_price = Coalesce(Sum('request_price'), Value(0.0)),
                sum_result_price = Coalesce(Sum('pre_result_price'), Value(0.0))
            ) \
            .order_by('subsidiary_id', 'year', 'month')
        if sch_year:
            daily_sales_qs = daily_sales_qs.filter(year=sch_year)
        if sch_subsidiary:
            daily_sales_qs = daily_sales_qs.filter(subsidiary_id=sch_subsidiary)
        daily_summary_list = []
        for row in daily_sales_qs:
            daily_summary_list.append({
                "subsidiary_id": row["subsidiary_id"],
                "year": row["year"],
                "month": row["month"],
                "sum_request_price": row["sum_request_price"],
                "sum_result_price": row["sum_result_price"]
            })
            
        general_sales_qs = GeneralWorkerSalary.objects \
            .filter(
                work_order__subsidiary_id__in=subsidiary_id_list
            ) \
            .values("work_order__subsidiary_id") \
            .annotate(
                year = ExtractYear('date'),
                month = ExtractMonth('date'),
                sum_request_price = Coalesce(Sum('final_price'), Value(0.0)),
                sum_result_price = Coalesce(Sum('sum_price') + Sum('extra_price') + Sum('extra_price2'), Value(0.0))
            ) \
            .order_by('work_order__subsidiary_id', 'year', 'month')
        if sch_year:
            general_sales_qs = general_sales_qs.filter(year=sch_year)
        if sch_subsidiary:
            general_sales_qs = general_sales_qs.filter(work_order__subsidiary_id=sch_subsidiary)
        general_summary_list = []
        for row in general_sales_qs:
            general_summary_list.append({
                "subsidiary_id": row["work_order__subsidiary_id"],
                "year": row["year"],
                "month": row["month"],
                "sum_request_price": row["sum_request_price"],
                "sum_result_price": row["sum_result_price"]
            })
        
        monthly_sales_qs = MonthlySales.objects \
            .filter(
                subsidiary_id__in=subsidiary_id_list
            ) \
            .values("subsidiary_id", "year", "month") \
            .annotate(
                sum_request_price = Coalesce(Sum('daily_price') + Sum('general_price'), Value(0.0)),
            ) \
            .order_by('subsidiary_id', 'year', 'month')
        monthly_sales_list = []
        for row in monthly_sales_qs:
            monthly_sales_list.append({
                "subsidiary_id": row["subsidiary_id"],
                "year": row["year"],
                "month": row["month"],
                "sum_request_price": row["sum_request_price"],
            })
            
        recruit_qs = Recruit.objects.filter(
            start_date__year=sch_year,
            subsidiary_id__in=subsidiary_id_list
        ) \
        .values("subsidiary_id", "start_date__year", "start_date__month") \
        .annotate(
            total_cost=Coalesce(Sum("price"), Value(0.0))
        )
        if sch_year:
            recruit_qs = recruit_qs.filter(start_date__startswith=sch_year)
        if sch_subsidiary:
            recruit_qs = recruit_qs.filter(subsidiary_id=sch_subsidiary)
        recruit_list = []
        for row in recruit_qs:
            recruit_list.append({
                "subsidiary_id": row["subsidiary_id"],
                "year": row["start_date__year"],
                "month": row["start_date__month"],
                "total_cost": row["total_cost"],
            })
        
        cost_qs = GeneralCost.objects.filter(
            date__year=sch_year,
            subsidiary_id__in=subsidiary_id_list
        ) \
        .values("subsidiary_id", "date__year", "date__month") \
        .annotate(
            total_cost=Coalesce(Sum("price"), Value(0.0))
        )
        if sch_year:
            cost_qs = cost_qs.filter(date__startswith=sch_year)
        if sch_subsidiary:
            cost_qs = cost_qs.filter(subsidiary_id=sch_subsidiary)
        cost_list = []
        for row in cost_qs:
            cost_list.append({
                "subsidiary_id": row["subsidiary_id"],
                "year": row["date__year"],
                "month": row["date__month"],
                "total_cost": row["total_cost"],
            })
        
        card_qs = CompanyCardHistory.objects.filter(
            date__year=sch_year,
            user__subsidiary_id__in=subsidiary_id_list
        ) \
        .values("user__subsidiary_id", "date__year", "date__month") \
        .annotate(
            total_cost=Coalesce(Sum("price"), Value(0.0))
        )
        if sch_year:
            card_qs = card_qs.filter(date__startswith=sch_year)
        if sch_subsidiary:
            card_qs = card_qs.filter(user__subsidiary_id=sch_subsidiary)
        card_list = []
        for row in card_qs:
            card_list.append({
                "subsidiary_id": row["user__subsidiary_id"],
                "year": row["date__year"],
                "month": row["date__month"],
                "total_cost": row["total_cost"],
            })
        
        context = {
            "subsidiary_list": subsidiary_list,
            "monthly_sales_list": monthly_sales_list,
            "daily_summary_list": daily_summary_list,
            "general_summary_list": general_summary_list,
            "recruit_list": recruit_list,
            "cost_list": cost_list,
            "card_list": card_list
        }
        return JsonResponse(context, safe=False)

class KpiCustomer_Summary(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        company = request.user.company
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        sch_year = request.GET.get('sch_year', datetime.now().year)
        sch_month = request.GET.get('sch_month', datetime.now().month)
        sch_customer_class = request.GET.get('sch_customer_class', '')
        query = request.GET.get('q', '')

        try:
            sch_year = int(sch_year)
        except (ValueError, TypeError):
            return JsonResponse({'error': '기준연도에 오류가 있습니다.'}, status=400)
        
        qs = CodeMaster.objects.filter(group=CodeGroup.CUSTOMER_CLASS, name__icontains=query, company=company) \
                                .order_by('name') \
                                .values('id', 'name')
                                
        # 특정 거래처분류 검색
        if sch_customer_class:
            qs = qs.filter(id=sch_customer_class)
        customer_list = []
        customer_id_list = []
        for row in qs:
            customer_list.append({
                "id": row["id"],
                "name": row["name"]
            })
            customer_id_list.append(row["id"])
        
        daily_sales_qs = DailyWorkOrder.objects \
            .filter(
                customer__customer_class_id__in=customer_id_list
            ) \
            .values("customer__customer_class_id") \
            .annotate(
                year = ExtractYear('date'),
                month = ExtractMonth('date'),
                sum_request_price = Coalesce(Sum('request_price'), Value(0.0)),
                sum_result_price = Coalesce(Sum('pre_result_price'), Value(0.0)),
                profit = Coalesce(Sum('profit'), Value(0.0))
            ) \
            .order_by('customer__customer_class_id', 'year', 'month')
        if sch_year:
            daily_sales_qs = daily_sales_qs.filter(year=sch_year)
        if sch_customer_class:
            daily_sales_qs = daily_sales_qs.filter(customer__customer_class_id=sch_customer_class)
        daily_summary_list = []
        for row in daily_sales_qs:
            daily_summary_list.append({
                "customer_id": row["customer__customer_class_id"],
                "year": row["year"],
                "month": row["month"],
                "sum_request_price": row["sum_request_price"],
                "sum_result_price": row["sum_result_price"],
            })
        
        general_sales_qs = GeneralWorkerSalary.objects \
            .filter(
                work_order__customer__customer_class_id__in=customer_id_list
            ) \
            .values("work_order__customer__customer_class_id") \
            .annotate(
                year = ExtractYear('date'),
                month = ExtractMonth('date'),
                sum_request_price = Coalesce(Sum('final_price'), Value(0.0)),
                sum_result_price = Coalesce(Sum('sum_price') + Sum('extra_price') + Sum('extra_price2'), Value(0.0)),
                profit = Coalesce(Sum('profit'), Value(0.0))
            ) \
            .order_by('work_order__customer__customer_class_id', 'year', 'month')
        if sch_year:
            general_sales_qs = general_sales_qs.filter(year=sch_year)
        if sch_customer_class:
            general_sales_qs = general_sales_qs.filter(work_order__customer__customer_class_id=sch_customer_class)
        general_summary_list = []
        for row in general_sales_qs:
            general_summary_list.append({
                "customer_id": row["work_order__customer__customer_class_id"],
                "year": row["year"],
                "month": row["month"],
                "sum_request_price": row["sum_request_price"],
                "sum_result_price": row["sum_result_price"],
            })
        
        monthly_sales_qs = MonthlySales.objects \
            .filter(
                customer__customer_class_id__in=customer_id_list
            ) \
            .values("customer__customer_class_id", "year", "month") \
            .annotate(
                sum_request_price = Coalesce(Sum('daily_price') + Sum('general_price'), Value(0.0)),
            ) \
            .order_by('customer__customer_class_id', 'year', 'month')
        monthly_sales_list = []
        for row in monthly_sales_qs:
            monthly_sales_list.append({
                "customer_id": row["customer__customer_class_id"],
                "year": row["year"],
                "month": row["month"],
                "sum_request_price": row["sum_request_price"],
            })
            
        recruit_qs = Recruit.objects.filter(
            start_date__year=sch_year,
            customer__customer_class_id__in=customer_id_list
        ) \
        .values("customer__customer_class_id", "start_date__year", "start_date__month") \
        .annotate(
            total_cost=Coalesce(Sum("price"), Value(0.0))
        )
        if sch_year:
            recruit_qs = recruit_qs.filter(start_date__startswith=sch_year)
        if sch_customer_class:
            recruit_qs = recruit_qs.filter(customer__customer_class_id=sch_customer_class)

        recruit_list = []
        for row in recruit_qs:
            recruit_list.append({
                "customer_id": row["customer__customer_class_id"],
                "year": row["start_date__year"],
                "month": row["start_date__month"],
                "total_cost": row["total_cost"],
            })
        
        cost_qs = GeneralCost.objects.filter(
            date__year=sch_year,
            customer__customer_class_id__in=customer_id_list
        ).values("customer__customer_class_id", "date__year", "date__month").annotate(
            total_cost=Coalesce(Sum("price"), Value(0.0))
        )
        if sch_year:
            cost_qs = cost_qs.filter(date__startswith=sch_year)
        if sch_customer_class:
            cost_qs = cost_qs.filter(customer__customer_class_id=sch_customer_class)

        cost_list = []
        for row in cost_qs:
            cost_list.append({
                "customer_id": row["customer__customer_class_id"],
                "year": row["date__year"],
                "month": row["date__month"],
                "total_cost": row["total_cost"],
            })

        card_qs = CompanyCardHistory.objects.filter(
            date__year=sch_year,
            user__customer__customer_class_id__in=customer_id_list
        ) \
        .values("user__customer__customer_class_id", "date__year", "date__month") \
        .annotate(
            total_cost=Coalesce(Sum("price"), Value(0.0))
        )
        if sch_year:
            card_qs = card_qs.filter(date__startswith=sch_year)
        if sch_customer_class:
            card_qs = card_qs.filter(user__customer__customer_class_id=sch_customer_class)
        card_list = []
        for row in card_qs:
            card_list.append({
                "subsidiary_id": row["user__customer__customer_class_id"],
                "year": row["date__year"],
                "month": row["date__month"],
                "total_cost": row["total_cost"],
            })

        context = {
            "customer_list": customer_list,
            "monthly_sales_list": monthly_sales_list,
            "daily_summary_list": daily_summary_list,
            "general_summary_list": general_summary_list,
            "recruit_list": recruit_list,
            "cost_list": cost_list,
            "card_list": card_list
        }
        return JsonResponse(context, safe=False)

class KpiCenter_Summary(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        sch_year = request.GET.get('sch_year', datetime.now().year)
        sch_month = request.GET.get('sch_month', '')
        sch_customer_class = request.GET.get('sch_customer_class', '')

        sch_date = sch_year
        if sch_month:
            sch_date = f"{sch_year}-{str(sch_month).zfill(2)}"
            
        try:
            sch_year = int(sch_year)
        except (ValueError, TypeError):
            return JsonResponse({'error': '기준연도에 오류가 있습니다.'}, status=400)
        
        qs = FactoryCustomer.objects \
            .select_related('customer_class') \
            .filter(customer_class__group='customer_class') \
            .exclude(customer_class__name="관리법인") 
        
        # 특정 거래처분류 검색
        if sch_customer_class:
            qs = qs.filter(id=sch_customer_class)
        qs = qs.order_by('id') \
            .values()
        customer_list = []
        customer_id_list = []
        for row in qs:
            customer_list.append({
                "id": row["id"],
                "code": row["code"],
                "name": row["name"]
            })
            customer_id_list.append(row["id"])

        daily_sales_qs = DailyWorkOrder.objects \
                                .filter(
                                    customer_id__in=customer_id_list
                                )
        if sch_date:
            daily_sales_qs = daily_sales_qs.filter(date__startswith=sch_date)
        if sch_customer_class:
            daily_sales_qs = daily_sales_qs.filter(customer_id=sch_customer_class)
        daily_sales_qs = daily_sales_qs.values("customer_id") \
            .annotate(
                year = ExtractYear('date'),
                month = ExtractMonth('date'),
                sum_request_price = Coalesce(Sum('request_price'), Value(0.0)),
                sum_result_price = Coalesce(Sum('pre_result_price'), Value(0.0)),
                profit = Coalesce(Sum('profit'), Value(0.0))
            ) \
            .order_by('customer_id', 'year', 'month')
        daily_summary_list = []
        for row in daily_sales_qs:
            daily_summary_list.append({
                "customer_id": row["customer_id"],
                "year": row["year"],
                "month": row["month"],
                "sum_request_price": row["sum_request_price"],
                "sum_result_price": row["sum_result_price"],
                "profit": row["profit"]
            })
        
        general_sales_qs = GeneralWorkerSalary.objects \
            .filter(
                Q(work_order__customer_id__in=customer_id_list) | Q(worker__customer_id__in=customer_id_list)
            )
        if sch_date:
            general_sales_qs = general_sales_qs.filter(date__startswith=sch_date)
        if sch_customer_class:
            general_sales_qs = general_sales_qs.filter(work_order__customer_id=sch_customer_class)
        general_sales_qs = general_sales_qs.values("work_order__customer_id", "worker__customer_id") \
            .annotate(
                date_year = ExtractYear('date'),
                date_month = ExtractMonth('date'),
                sum_request_price = Coalesce(Sum('final_price'), Value(0.0)),
                sum_result_price = Coalesce(Sum('sum_price') + Sum('extra_price') + Sum('extra_price2'), Value(0.0)),
                profit = Coalesce(Sum('profit'), Value(0.0))
            ) \
            .order_by('work_order__customer_id', 'worker__customer_id', 'date_year', 'date_month')
        general_summary_list = []
        for row in general_sales_qs:
            general_summary_list.append({
                "customer_id": row["work_order__customer_id"] if row["work_order__customer_id"] else row["worker__customer_id"],
                "year": row["date_year"],
                "month": row["date_month"],
                "sum_request_price": row["sum_request_price"],
                "sum_result_price": row["sum_result_price"],
                "profit": row["profit"],
            })

        monthly_sales_qs = MonthlySales.objects \
            .filter(
                customer_id__in=customer_id_list
            )
        if sch_year:
            monthly_sales_qs = monthly_sales_qs.filter(year=int(sch_year))
        if sch_month:
            monthly_sales_qs = monthly_sales_qs.filter(month=int(sch_month))
        monthly_sales_qs = monthly_sales_qs.values("customer_id", "year", "month") \
                            .annotate(
                                sum_request_price = Coalesce(Sum('daily_price') + Sum('general_price'), Value(0.0)),
                            ) \
                            .order_by('customer_id', 'year', 'month')
        monthly_sales_list = []
        for row in monthly_sales_qs:
            monthly_sales_list.append({
                "customer_id": row["customer_id"],
                "year": row["year"],
                "month": row["month"],
                "sum_request_price": row["sum_request_price"],
            })

        recruit_qs = Recruit.objects.filter(
            start_date__year=sch_year,
            customer_id__in=customer_id_list
        )
        if sch_date:
            recruit_qs = recruit_qs.filter(start_date__startswith=sch_date)
        if sch_customer_class:
            recruit_qs = recruit_qs.filter(customer_id=sch_customer_class)
        recruit_qs = recruit_qs.exclude(customer__customer_class__name="관리법인") \
        .values("customer_id", "start_date__year", "start_date__month") \
        .annotate(
            total_cost=Coalesce(Sum("price"), Value(0.0))
        )
        recruit_list = []
        for row in recruit_qs:
            recruit_list.append({
                "customer_id": row["customer_id"],
                "year": row["start_date__year"],
                "month": row["start_date__month"],
                "total_cost": row["total_cost"],
            })

        cost_qs = GeneralCost.objects.filter(
            date__year=sch_year,
            customer_id__in=customer_id_list
        )
        
        if sch_date:
            cost_qs = cost_qs.filter(date__startswith=sch_date)
        if sch_customer_class:
            cost_qs = cost_qs.filter(customer_id=sch_customer_class)
        cost_qs = cost_qs.values("customer_id", "date__year", "date__month") \
        .annotate(
            total_cost=Coalesce(Sum("price"), Value(0.0))
        )
        cost_list = []
        for row in cost_qs:
            cost_list.append({
                "customer_id": row["customer_id"],
                "year": row["date__year"],
                "month": row["date__month"],
                "total_cost": row["total_cost"],
            })
        
        card_qs = CompanyCardHistory.objects.filter(
            date__year=sch_year,
            user__customer__customer_class_id__in=customer_id_list
        )
        if sch_date:
            card_qs = card_qs.filter(date__startswith=sch_date)
        if sch_customer_class:
            card_qs = card_qs.filter(user__customer__customer_class_id=sch_customer_class)
        card_qs = card_qs.values("user__customer__customer_class_id", "date__year", "date__month") \
        .annotate(
            total_cost=Coalesce(Sum("price"), Value(0.0))
        )
        card_list = []
        for row in card_qs:
            card_list.append({
                "subsidiary_id": row["user__customer__customer_class_id"],
                "start_date_year": row["date__year"],
                "start_date_month": row["date__month"],
                "total_cost": row["total_cost"],
            })
        context = {
            "customer_list": customer_list,
            "monthly_sales_list": monthly_sales_list,
            "daily_summary_list": daily_summary_list,
            "general_summary_list": general_summary_list,
            "recruit_list": recruit_list,
            "cost_list": cost_list,
            "card_list": card_list,
            "sch_date": sch_date
        }
        return JsonResponse(context, safe=False)
  