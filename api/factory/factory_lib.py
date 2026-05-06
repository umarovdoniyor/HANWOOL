from api.models import UserMaster, FactoryPurchase, FactoryPurchaseItem, FactoryEvent, CodeMaster, CodeGroup, \
    FactoryItemIn, FactoryItemOut, FactoryItem, FactoryCustomer, FactoryProduction, FactoryQuotation, \
    FactoryCustomerOrder, DailyWorkOrder
from string import ascii_uppercase


def get_item_code(company):
    prefix = 'IT-'
    order = '0000001'

    res = FactoryItem.objects.filter(code__istartswith=prefix, company=company)
    if res.exists():
        latest_entry = res.order_by('-code').first()
        if latest_entry and latest_entry.code:
            try:
                num = latest_entry.code.replace(prefix, '')
                if num.isdigit():
                    order = str(int(num) + 1).zfill(7)
            except (ValueError, AttributeError):
                raise ValueError("기존 코드 처리 중 오류 발생")

    # 중복 피하기 위해 루프 돌며 고유 코드 생성
    while FactoryItem.objects.filter(code=prefix + order, company=company).exists():
        order = str(int(order) + 1).zfill(5)

    return prefix + order


def get_itemin_code(company):
    prefix = 'WI-'
    order = '0000001'

    res = FactoryItemIn.objects.filter(code__istartswith=prefix, company=company)
    if res.exists():
        latest_entry = res.order_by('-code').first()
        if latest_entry and latest_entry.code:
            try:
                num = latest_entry.code.replace(prefix, '')
                if num.isdigit():
                    order = str(int(num) + 1).zfill(7)
            except (ValueError, AttributeError):
                raise ValueError("기존 코드 처리 중 오류 발생")

    # 중복 피하기 위해 루프 돌며 고유 코드 생성
    while FactoryItemIn.objects.filter(code=prefix + order, company=company).exists():
        order = str(int(order) + 1).zfill(7)

    return prefix + order


def get_itemout_code(company):
    prefix = 'WO-'
    order = '0000001'

    res = FactoryItemOut.objects.filter(code__istartswith=prefix, company=company)
    if res.exists():
        latest_entry = res.order_by('-code').first()
        if latest_entry and latest_entry.code:
            try:
                num = latest_entry.code.replace(prefix, '')
                if num.isdigit():
                    order = str(int(num) + 1).zfill(7)
            except (ValueError, AttributeError):
                raise ValueError("기존 코드 처리 중 오류 발생")

    # 중복 피하기 위해 루프 돌며 고유 코드 생성
    while FactoryItemOut.objects.filter(code=prefix + order, company=company).exists():
        order = str(int(order) + 1).zfill(7)

    return prefix + order


def get_customer_code(company):
    prefix = 'CS-'
    order = '0001'

    res = FactoryCustomer.objects.filter(code__istartswith=prefix, company=company)
    if res.exists():
        latest_entry = res.order_by('-code').first()
        if latest_entry and latest_entry.code:
            try:
                num = latest_entry.code.replace(prefix, '')
                if num.isdigit():
                    order = str(int(num) + 1).zfill(4)
            except (ValueError, AttributeError):
                raise ValueError("기존 코드 처리 중 오류 발생")

    # 중복 피하기 위해 루프 돌며 고유 코드 생성
    while FactoryCustomer.objects.filter(code=prefix + order, company=company).exists():
        order = str(int(order) + 1).zfill(4)

    return prefix + order


def get_purchase_code(company):
    prefix = 'PO-'
    order = '0000001'

    res = FactoryPurchase.objects.filter(code__istartswith=prefix, company=company)
    if res.exists():
        latest_entry = res.order_by('-code').first()
        if latest_entry and latest_entry.code:
            try:
                num = latest_entry.code.replace(prefix, '')
                if num.isdigit():
                    order = str(int(num) + 1).zfill(7)
            except (ValueError, AttributeError):
                raise ValueError("기존 코드 처리 중 오류 발생")

    # 중복 피하기 위해 루프 돌며 고유 코드 생성
    while FactoryPurchase.objects.filter(code=prefix + order, company=company).exists():
        order = str(int(order) + 1).zfill(7)

    return prefix + order


def get_production_code(company):
    prefix = 'MO-'
    order = '0000001'

    res = FactoryProduction.objects.filter(code__istartswith=prefix, company=company)
    if res.exists():
        latest_entry = res.order_by('-code').first()
        if latest_entry and latest_entry.code:
            try:
                num = latest_entry.code.replace(prefix, '')
                if num.isdigit():
                    order = str(int(num) + 1).zfill(7)
            except (ValueError, AttributeError):
                raise ValueError("기존 코드 처리 중 오류 발생")

    # 중복 피하기 위해 루프 돌며 고유 코드 생성
    while FactoryProduction.objects.filter(code=prefix + order, company=company).exists():
        order = str(int(order) + 1).zfill(7)

    return prefix + order


def get_quotation_code(company):
    prefix = 'CQ-'
    order = '0000001'

    res = FactoryQuotation.objects.filter(code__istartswith=prefix, company=company)
    if res.exists():
        latest_entry = res.order_by('-code').first()
        if latest_entry and latest_entry.code:
            try:
                num = latest_entry.code.replace(prefix, '')
                if num.isdigit():
                    order = str(int(num) + 1).zfill(7)
            except (ValueError, AttributeError):
                raise ValueError("기존 코드 처리 중 오류 발생")

    # 중복 피하기 위해 루프 돌며 고유 코드 생성
    while FactoryQuotation.objects.filter(code=prefix + order, company=company).exists():
        order = str(int(order) + 1).zfill(7)

    return prefix + order


# 견죽 수주시 CQ-코드를 전달받아 CO전환생성
def get_customer_order_code_from_quotation(quotation_code, company):
    if not quotation_code.startswith('CQ-'):
        raise ValueError("올바르지 않은 견적서 코드입니다 (CQ-로 시작해야 함)")

    base_code = quotation_code.replace('CQ-', 'CO-', 1)

    for suffix in [''] + list(ascii_uppercase):  # '', 'A', 'B', ..., 'Z'
        code = base_code + suffix
        if not FactoryCustomerOrder.objects.filter(code=code, company=company).exists():
            return code

    raise ValueError("고유한 주문서 코드를 생성할 수 없습니다 (A~Z까지 모두 사용됨)")


# 직접 발주 등록시 CN코드로 CO생성
def get_customer_order_code(company):
    prefix = 'CN-'
    order = '0000001'

    res = FactoryCustomerOrder.objects.filter(code__istartswith=prefix, company=company)
    if res.exists():
        latest_entry = res.order_by('-code').first()
        if latest_entry and latest_entry.code:
            try:
                num = latest_entry.code.replace(prefix, '')
                if num.isdigit():
                    order = str(int(num) + 1).zfill(7)
            except (ValueError, AttributeError):
                raise ValueError("기존 코드 처리 중 오류 발생")

    # 중복 피하기 위해 루프 돌며 고유 코드 생성
    while FactoryCustomerOrder.objects.filter(code=prefix + order, company=company).exists():
        order = str(int(order) + 1).zfill(7)

    return prefix + order


# 일일근무관리 문서번호 생성
def get_workorder_code(company):
    prefix = 'DO-'
    order = '000000001'

    res = DailyWorkOrder.objects.filter(code__istartswith=prefix, company=company)
    if res.exists():
        latest_entry = res.order_by('-code').first()
        if latest_entry and latest_entry.code:
            try:
                num = latest_entry.code.replace(prefix, '')
                if num.isdigit():
                    order = str(int(num) + 1).zfill(9)
            except (ValueError, AttributeError):
                raise ValueError("기존 코드 처리 중 오류 발생")

    # 중복 피하기 위해 루프 돌며 고유 코드 생성
    while DailyWorkOrder.objects.filter(code=prefix + order, company=company).exists():
        order = str(int(order) + 1).zfill(7)

    return prefix + order


def get_user_info(user):
    return {
        'id': user.id,
        'name': user.name,
        'profile_image': user.profile_image.url if user.profile_image and user.profile_image.name else '',
        'team': user.team.name if user.team else '',
        'job_level': user.job_level.name if user.job_level else '',
        'job_title': user.job_title.name if user.job_title else '',
        'phone': user.phone,
        'rrn': user.rrn,
        'bank_name': user.bank.name if user.bank else '',
        'account_code': user.account_code,
        'account_name': user.account_name,
    }

def get_item_info(item):
    try:
        from api.factory.inventory_list import get_item_stock
        in_total_sum, in_faulty_sum, in_result_sum, out_result_sum, item_stock = get_item_stock(item.id)
    except Exception:
        in_total_sum = in_faulty_sum = in_result_sum = out_result_sum = item_stock = 0

    return {
        'id': item.id,
        'name': item.name or '',
        'code': item.code or '',
        'desc1': item.desc1 or '',
        'desc2': item.desc2 or '',
        'desc3': item.desc3 or '',
        'safety_stock': item.safety_stock or '',
        'moq': item.moq or '',
        'buy_price': item.buy_price or 0,
        'sell_price': item.sell_price or 0,
        'std_cost': item.std_cost or 0,
        # 'qr_code': item.qr_code or 0,
        'is_valid': item.is_valid,
        'img': item.img.url if item.img and item.img.name else '',
        'doc_url': item.doc.url if item.doc and item.doc.name else '',
        'doc_name': item.doc.name if item.doc and item.doc.name else '',

        'unit_id': item.unit.id if item.unit is not None else '',
        'unit_name': item.unit.name if item.unit is not None else '',
        'item_class_id': item.item_class.id if item.item_class is not None else '',
        'item_class_name': item.item_class.name if item.item_class is not None else '',
        'warehouse_id': item.warehouse.id if item.warehouse is not None else '',
        'warehouse_name': item.warehouse.name if item.warehouse is not None else '',
        'supplier_id': item.supplier.id if item.supplier is not None else '',
        'supplier_name': item.supplier.name if item.supplier is not None else '',

        'in_total_sum': in_total_sum,
        'in_faulty_sum': in_faulty_sum,
        'in_result_sum': in_result_sum,
        'out_result_sum': out_result_sum,
        'item_stock': item_stock,

        'created_by': get_user_info(item.created_by) if item.created_by else '',
        'updated_by': get_user_info(item.updated_by) if item.updated_by else '',
        'created_at': item.created_at.strftime('%Y-%m-%d') if item.created_at else '',
        'updated_at': item.updated_at.strftime('%Y-%m-%d') if item.updated_at else '',
        'company_id': item.company.id if item.company is not None else '',
        'company_name': item.company.company_info.first().company_name if item.company.company_info.exists() else '',
    }

def fk_int(val):
    if val in (None, '', 'undefined', 'null'):
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def to_float(value):
    try:
        return float(value) if value not in (None, '', 'None') else 0
    except (TypeError, ValueError):
        return 0