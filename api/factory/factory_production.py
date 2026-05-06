from django.shortcuts import get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, Sum
from api.models import UserMaster, FactoryEvent, CodeMaster, CodeGroup, FactoryItemIn, FactoryItemOut, \
    FactoryProduction, FactoryProductionItem, FactoryBomStructure
from api.lib import Pagenation, get_excep_msg
from django.utils import timezone
from api.factory.inventory_list import get_item_stock
from api.basic_data.notification import noti_create_fn
from datetime import datetime, time
from api.factory.factory_lib import get_itemin_code, get_itemout_code, get_production_code, get_user_info, get_item_info, fk_int
import json


class FactoryProduction_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        fr_date = request.GET.get('fr_date', '')
        to_date = request.GET.get('to_date', '')

        qs = FactoryProduction.objects.filter(company=request_user.company).order_by('end_date', 'start_date')

        status_manage = request.GET.get('status_manage', '')
        if status_manage:
            qs = qs.filter(is_approved=True)

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
                            Q(item__item_code__icontains=keyword) |
                            Q(item__item_name__icontains=keyword) |
                            Q(desc1__icontains=keyword) |
                            Q(desc2__icontains=keyword) |
                            Q(desc3__icontains=keyword)
                    )
                    search_conditions |= search_condition
            qs = qs.filter(search_conditions)

        # 기간 검색
        if fr_date:
            qs = qs.filter(start_date__gte=fr_date)
        if to_date:
            qs = qs.filter(end_date__lte=to_date)

        # sch_is_approved 필터
        sch_is_approved = request.GET.get('sch_is_approved', '')
        if sch_is_approved == "미승인":
            qs = qs.filter(is_approved=0)
        elif sch_is_approved == "승인":
            qs = qs.filter(is_approved=1)

        # sch_status 필터
        sch_status = request.GET.get('sch_status', '')
        if sch_status == "진행":
            qs = qs.filter(Q(status="") | Q(status=None) | Q(status="대기") | Q(status="진행"))
        elif sch_status == "완료":
            qs = qs.filter(status="완료")

        # sch_item 필터
        sch_item = request.GET.get('sch_item', '')
        if sch_item:
            qs = qs.filter(item_id=sch_item)

        sch_id = request.GET.get('sch_id', '')
        if sch_id:
            qs = FactoryProduction.objects.filter(id=sch_id, company=request_user.company)

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


class FactoryProduction_Create(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)

            start_date = request.POST.get('start_date', None) or None
            end_date = request.POST.get('end_date', None) or None
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')
            desc3 = request.POST.get('desc3', '')
            total_qty = float(request.POST.get('total_qty', 0)) or None

            item = request.POST.get('item', '')
            item = int(item) if item.isdigit() else None
            approver = request.POST.get('approver', '')
            approver = int(approver) if approver.isdigit() else None
            warehouse = request.POST.get('warehouse', '')
            warehouse = int(warehouse) if warehouse.isdigit() else None

            process_data = json.loads(request.POST.get('processData'))

            obj = FactoryProduction.objects.create(
                code=get_production_code(request_user.company),
                item_id=item,
                approver_id=approver,
                warehouse_id=warehouse,
                start_date=start_date,
                end_date=end_date,
                desc1=desc1,
                desc2=desc2,
                desc3=desc3,
                total_qty=total_qty,
                status="대기",

                created_by=request_user,
                updated_by=request_user,
                created_at=timezone.now().date(),
                updated_at=timezone.now().date(),
                company=request_user.company,
            )

            for data in process_data:
                seq_no = data.get('seq_no')
                process_id = data.get('process_id')
                workshop = fk_int(data.get('workshop'))
                responsible = fk_int(data.get('responsible'))
                process_total_qty = data.get('total_qty')
                process_start_date = data.get('start_date')
                process_end_date = data.get('end_date')
                process_desc1 = data.get('process_desc1')

                # 생산 세부공정 생성
                obj_item = FactoryProductionItem.objects.create(
                    production_id=obj.id,
                    item_id=item,
                    total_qty=process_total_qty,
                    start_date=process_start_date,
                    end_date=process_end_date,
                    seq_no=seq_no,
                    process_id=process_id,
                    workshop_id=workshop,
                    responsible_id=responsible,
                    desc1=process_desc1,
                    status="대기",

                    created_by=request_user,
                    updated_by=request_user,
                    created_at=timezone.now().date(),
                    updated_at=timezone.now().date(),
                    company=request_user.company,
                )

            # 알림센터 메세지 전송
            item_name = obj.item.name if obj.item else "품목정보 없음"
            unit_name = obj.item.unit.name if obj.item and obj.item.unit else ""
            qty_display = int(obj.total_qty) if obj.total_qty and obj.total_qty.is_integer() else obj.total_qty  # 소수점 미포함시 정수표시

            noti_create_fn(
                content=f"[{obj.code}] {item_name} x {qty_display} {unit_name} 생산계획서 결재 요청",
                user=obj.approver,
                url=f"/factory/production/list/?sch_id={obj.id}",
                noti_type="production_approval_request"
            )

            context = get_obj(obj)
            return JsonResponse(context, safe=False)

        except Exception as e:
            transaction.set_rollback(True)
            msg = get_excep_msg(e)
            return JsonResponse({'error': True, 'message': msg}, status=500)


class FactoryProduction_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            start_date = request.POST.get('start_date', None) or None
            end_date = request.POST.get('end_date', None) or None
            desc1 = request.POST.get('desc1', '')
            desc2 = request.POST.get('desc2', '')
            desc3 = request.POST.get('desc3', '')
            total_qty = float(request.POST.get('total_qty', 0)) or None
            status = request.POST.get('status', '')

            item = request.POST.get('item', '')
            item = int(item) if item.isdigit() else None
            approver = request.POST.get('approver', '')
            approver = int(approver) if approver.isdigit() else None
            warehouse = request.POST.get('warehouse', '')
            warehouse = int(warehouse) if warehouse.isdigit() else None

            process_data = json.loads(request.POST.get('processData'))

            obj = get_object_or_404(FactoryProduction, pk=int(pk))

            obj.start_date = start_date
            obj.end_date = end_date
            obj.desc1 = desc1
            obj.desc2 = desc2
            obj.desc3 = desc3
            obj.total_qty = total_qty
            obj.status = status

            obj.item_id = item
            obj.approver_id = approver
            obj.warehouse_id = warehouse

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            # 기존 공정계획 삭제 후 재생성
            exist_obj_items = FactoryProductionItem.objects.filter(production=int(pk))
            if exist_obj_items:
                for exist_obj_item in exist_obj_items:
                    exist_obj_item.delete()

            for data in process_data:
                seq_no = data.get('seq_no')
                process_id = data.get('process_id')
                workshop = fk_int(data.get('workshop'))
                responsible = fk_int(data.get('responsible'))
                process_total_qty = data.get('total_qty')
                process_start_date = data.get('start_date')
                process_end_date = data.get('end_date')
                process_desc1 = data.get('process_desc1')

                # 생산 세부공정 생성
                obj_item = FactoryProductionItem.objects.create(
                    production_id=obj.id,
                    item_id=item,
                    total_qty=process_total_qty,
                    start_date=process_start_date,
                    end_date=process_end_date,
                    seq_no=seq_no,
                    process_id=process_id,
                    workshop_id=workshop,
                    responsible_id=responsible,
                    desc1=process_desc1,
                    status="대기",

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


class FactoryProduction_Approve(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            obj = get_object_or_404(FactoryProduction, pk=int(pk))

            if obj.approver_id != request_user.id:
                return JsonResponse({"error": True, "message": "[결재 승인자] 가 아닙니다."})

            obj.is_approved = True

            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            # 알림센터 메세지 전송
            item_name = obj.item.name if obj.item else "품목정보 없음"
            unit_name = obj.item.unit.name if obj.item and obj.item.unit else ""
            qty_display = int(obj.total_qty) if obj.total_qty and obj.total_qty.is_integer() else obj.total_qty  # 소수점 미포함시 정수표시

            noti_create_fn(
                content=f"[{obj.code}] {item_name} x {qty_display} {unit_name} 생산계획서 결재 승인",
                user=obj.created_by,
                url=f"/factory/production/list/?sch_id={obj.id}",
                noti_type="production_approval_approved"
            )

            # 생산일정 캘린더 등록
            event_category = CodeMaster.objects.filter(group=CodeGroup.FACTORY_EVENT_CATEGORY, name="생산 일정",
                                                       is_default=True, company=request_user.company).first()

            FactoryEvent.objects.create(
                production=obj,
                title=f"[{obj.code}] {obj.item.name} x {qty_display}",
                category=event_category,
                start_date=datetime.combine(obj.start_date, time.min),
                end_date=datetime.combine(obj.end_date, time(hour=23, minute=59)),
                event_url=f"/factory/production/status/?sch_id={obj.id}",
                desc=f"[생산 참고사항1] {obj.desc1 or '-'}\n[생산 참고사항2] {obj.desc2 or '-'}",
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


class FactoryProduction_Delete(View):
    @transaction.atomic
    def post(self, request):
        try:
            pk = request.POST.get('pk', '')
            if (pk == ''):
                return JsonResponse({'error': True, 'message': "삭제할 항목이 선택되지 않았습니다."})

            obj = get_object_or_404(FactoryProduction, pk=int(pk))
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
        'code': obj.code or '',
        'is_approved': obj.is_approved,
        'status': obj.status or '',
        'start_date': obj.start_date or '',
        'end_date': obj.end_date or '',
        'total_qty': obj.total_qty or '',
        'receive_qty': obj.receive_qty or '',
        'faulty_qty': obj.faulty_qty or '',
        'result_qty': obj.result_qty or '',
        'desc1': obj.desc1 or '',
        'desc2': obj.desc2 or '',
        'desc3': obj.desc3 or '',

        'warehouse_id': obj.warehouse.id if obj.warehouse is not None else '',
        'warehouse_name': obj.warehouse.name if obj.warehouse is not None else '',
        'item': get_item_info(obj.item) if obj.item else '',
        'approver': get_user_info(obj.approver) if obj.approver else '',

        'created_by': get_user_info(obj.created_by) if obj.created_by else '',
        'updated_by': get_user_info(obj.updated_by) if obj.updated_by else '',
        'created_at': obj.created_at.strftime('%Y-%m-%d') if obj.created_at else '',
        'updated_at': obj.updated_at.strftime('%Y-%m-%d') if obj.updated_at else '',
        'company_id': obj.company.id if obj.company is not None else '',
        'company_name': obj.company.company_info.first().company_name if obj.company.company_info.exists() else '',
    }


class FactoryProductionItem_Read(View):
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        request_user = get_object_or_404(UserMaster, id=request.user.id)
        _page = request.GET.get('page', '')
        _size = request.GET.get('page_size', '')
        production = request.GET.get('production', '')

        qs = FactoryProductionItem.objects.filter(production=production, company=request_user.company).order_by('id')

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

        results = [get_obj_items(row) for row in qs_ps]

        context = {
            'count': qs_ps.paginator.count,
            'previous': url_pre,
            'next': url_next,
            'results': results,
        }

        return JsonResponse(context, safe=False)


class FactoryProductionItem_Update(View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            request_user = get_object_or_404(UserMaster, id=request.user.id)
            pk = request.POST.get('pk', '')

            status = request.POST.get('status', '')
            process_data = json.loads(request.POST.get('processData'))

            obj = get_object_or_404(FactoryProduction, pk=int(pk))

            # 이미 완료된 생산계획서 수정 방지
            if obj.status == "완료":
                return JsonResponse({"error": True, "message": "이미 생산진행 상태가 완료된 생산계획서입니다."})

            obj.status = status
            obj.updated_by = request_user
            obj.updated_at = timezone.now()
            obj.save()

            # 기존 생산품목 수정
            for data in process_data:
                row_id = data.get('row_id')
                try:
                    obj_item = FactoryProductionItem.objects.get(id=int(row_id))
                except FactoryProductionItem.DoesNotExist:
                    continue

                obj_item.desc1 = data.get('process_desc1') or None
                obj_item.start_date = data.get('start_date') or None
                obj_item.end_date = data.get('end_date') or None
                obj_item.receive_qty = data.get('receive_qty') or None
                obj_item.faulty_qty = data.get('faulty_qty') or None
                obj_item.faulty_class_id = data.get('faulty_class') or None
                obj_item.result_qty = data.get('result_qty') or None
                obj_item.desc2 = data.get('process_desc2') or None
                obj_item.status = "완료" if obj.status == "완료" else data.get('process_status') or None

                obj_item.updated_by = request_user
                obj_item.updated_at = timezone.now()
                obj_item.save()

            # 생산계획서도 업데이트
            item_qs = FactoryProductionItem.objects.filter(production=obj)
            first_item = item_qs.order_by('id').first()
            last_item = item_qs.order_by('id').last()

            obj.receive_qty = first_item.receive_qty or 0 if first_item else 0
            obj.result_qty = last_item.result_qty or 0 if last_item else 0
            obj.start_date = first_item.start_date if first_item and first_item.start_date else obj.start_date
            obj.end_date = last_item.end_date if last_item and last_item.end_date else obj.end_date
            obj.faulty_qty = item_qs.aggregate(total=Sum('faulty_qty'))['total'] or 0
            obj.save()

            # status가 완료일 경우, 재고입고 & 재고출고 등록
            if obj.status == "완료":
                FactoryItemIn.objects.create(
                    code=get_itemin_code(request_user.company),
                    date=obj.end_date,
                    desc1=f"생산완료 입고 ({obj.code})",
                    desc2=obj.desc1,
                    total_amount=obj.receive_qty,
                    faulty_amount=0,
                    result_amount=(obj.result_qty or 0) + (obj.faulty_qty or 0),

                    item_id=obj.item_id,
                    warehouse_id=obj.warehouse_id,
                    production_id=obj.id,

                    created_by=request_user,
                    updated_by=request_user,
                    created_at=timezone.now().date(),
                    updated_at=timezone.now().date(),
                    company=request_user.company,
                )

                # obj.item_id 기준 BOM 구조 조회
                bom_list = FactoryBomStructure.objects.filter(parent_item=obj.item_id, company=request_user.company)
                for bom in bom_list:
                    if not bom.child_item:
                        continue  # 연결된 자재 없을 경우 스킵

                    # 총 출고수량 = child_qty × 생산수량
                    total_qty = (bom.child_qty or 0) * (obj.receive_qty or 0)
                    if total_qty <= 0:
                        continue

                    FactoryItemOut.objects.create(
                        code=get_itemout_code(request_user.company),
                        date=obj.start_date,
                        desc1=f"생산자재 출고 ({obj.code})",
                        desc2=obj.desc1,
                        total_amount=total_qty,
                        faulty_amount=0,
                        result_amount=total_qty,

                        item=bom.child_item,
                        warehouse=bom.child_item.warehouse,
                        production=obj,

                        created_by=request_user,
                        updated_by=request_user,
                        created_at=timezone.now().date(),
                        updated_at=timezone.now().date(),
                        company=request_user.company,
                    )

                # 불량 출고 (불량정보 있는 공정만)
                for data in process_data:
                    faulty_class = data.get('faulty_class')
                    faulty_qty = float(data.get('faulty_qty') or 0)

                    if faulty_qty > 0:
                        if faulty_class:
                            faulty_class_name = CodeMaster.objects.filter(id=faulty_class).first()
                            faulty_class_name = faulty_class_name.name if faulty_class_name else "미입력"
                        else:
                            faulty_class_name = "미입력"

                        FactoryItemOut.objects.create(
                            code=get_itemout_code(request_user.company),
                            date=obj.end_date,
                            desc1=f"생산불량 출고 ({obj.code})",
                            desc2=f"불량사유: {faulty_class_name}",
                            total_amount=faulty_qty,
                            faulty_amount=faulty_qty,
                            result_amount=faulty_qty,

                            item_id=obj.item_id,
                            warehouse_id=obj.warehouse_id,
                            faulty_class_id=faulty_class,
                            production_id=obj.id,

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


def get_obj_items(obj):
    return {
        'id': obj.id,
        'production_id': obj.production.id if obj.production is not None else '',
        'item_id': obj.item.id if obj.item is not None else '',
        'item_class': obj.item.item_class.name if obj.item.item_class is not None else '',
        'item_warehouse': obj.item.warehouse.id if obj.item.warehouse is not None else '',
        'total_qty': obj.total_qty or '',
        'desc1': obj.desc1 or '',
        'desc2': obj.desc2 or '',
        'start_date': obj.start_date or '',
        'end_date': obj.end_date or '',

        'status': obj.status or '',
        'seq_no': obj.seq_no or '',
        'process_id': obj.process.id if obj.process is not None else '',
        'process_name': obj.process.name if obj.process is not None else '',
        'workshop_id': obj.workshop.id if obj.workshop is not None else '',
        'workshop_name': obj.workshop.name if obj.workshop is not None else '',
        'responsible': get_user_info(obj.responsible) if obj.responsible is not None else '',

        'receive_date': obj.receive_date or '',
        'receive_qty': obj.receive_qty or '',
        'faulty_qty': obj.faulty_qty or '',
        'result_qty': obj.result_qty or '',
        'faulty_class_id': obj.faulty_class.id  if obj.faulty_class is not None else '',
        'faulty_class_name': obj.faulty_class.name if obj.faulty_class is not None else '',
    }
