msg_error = "입력한 데이터에 오류가 존재합니다.\n"
msg_1062 = "중복된 데이터가 존재합니다.\n"
msg_create_fail = "등록 실패했습니다.\n"
msg_update_fail = "수정 실패했습니다.\n"
msg_delete_fail = "삭제 실패했습니다.\n"

msg_pk = "pk가 존재하지 않습니다.\n"
msg_fk = "fk가 존재하지 않습니다.\n"

# 가능한 아래쪽 사용
class txt:
    def __init__(self):

        # 공통
        self.error = "에러가 발생했습니다. \n관리자에게 문의하세요."
        self.error_input = "입력한 데이터에 오류가 존재합니다."
        self.error_1062 = "중복된 데이터가 존재합니다."
        self.error_1452 = "[셀렉트바] 를 다시 확인하세요."  # 어떤 경우인지 기록 필요
        self.error_1048 = "[셀렉트바] 를 다시 확인하세요."  # Null 이 허용되지 않는 경우

        self.error_not_exist = "처리하고자 하는 데이터 가 존재하지 않습니다."
        self.pk_not_exist = "삭제하고자 하는 데이터 가 존재하지 않습니다."
        self.error_day = "날짜를 확인해주세요."

        self.create_fail = "등록 실패했습니다. \n관리자에게 문의하세요."
        self.msg_update_fail = "수정 실패했습니다. \n관리자에게 문의하세요."
        self.msg_update_fail = "수정 실패했습니다. \n관리자에게 문의하세요."

        self.msg_update_fail_warehouse = "가상창고는 수정할 수 없습니다."
        self.msg_delete_fail_warehouse = "가상창고는 삭제할 수 없습니다."

        self.bom_do_not_same = '[BOM 형식의 품번]은 [BOM의 품번]과 동일할 수 없습니다.'

        self.cant_del_byself = '본인 계정을 스스로 지울 수 없습니다.'
        self.cant_normal_del_master = '일반 사용자가 업체 계정을 지울 수 없습니다.'

txt = txt()