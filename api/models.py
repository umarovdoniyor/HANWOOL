from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from datetime import time, date, timedelta, datetime
from api.lib import path_and_rename


class CompanyMaster(models.Model):
    class Meta:
        unique_together = ('code', 'name')

    code = models.CharField(max_length=100, unique=True, verbose_name='회사코드')
    name = models.CharField(max_length=100, verbose_name='회사명')
    permissions = models.CharField(max_length=100, null=True, verbose_name='회사권한')
    is_valid = models.BooleanField(default=True, verbose_name='서비스 현황')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='최초등록일')
    expire_date = models.DateField(blank=True, null=True, verbose_name='서비스 종료일')
    signup_email = models.EmailField(max_length=100, blank=True, null=True, verbose_name='가입등록 메일')
    exit_request = models.CharField(max_length=100, null=True, blank=True, verbose_name='탈퇴요청')
    factory = models.CharField(max_length=255, null=True, blank=True)  # 팩토리 사용여부(미사용, 사용, 만료)


class CustomUserMaster(BaseUserManager):
    def usermodel(self, user_id, password, name):
        user = self.model(user_id=user_id, name=name)
        user.set_password(password)
        return user

    def create_user(self, user_id, password, name=""):
        user = self.usermodel(user_id, password, name)
        user.save(using=self._db)
        return user

    def create_superuser(self, user_id, password, name=""):
        user = self.usermodel(user_id, password, name)
        user.is_superuser = True
        user.save(using=self._db)
        return user


class UserMaster(AbstractBaseUser, PermissionsMixin):
    class Meta:
        unique_together = ('company', 'employee_code')

    objects = CustomUserMaster()
    USERNAME_FIELD = 'user_id'

    user_id = models.CharField(max_length=100, unique=True, verbose_name='사용자 계정')
    email = models.EmailField(max_length=100, blank=True, null=True, verbose_name='사용자 메일')
    name = models.CharField(max_length=100, blank=True, null=True, verbose_name='사용자 이름')
    employee_code = models.CharField(max_length=30, unique=True, blank=True, null=True, verbose_name='사용자 사번')
    phone = models.CharField(max_length=30, blank=True, null=True, verbose_name='사용자 연락처')
    address = models.CharField(max_length=100, blank=True, null=True, verbose_name='사용자 주소')
    hire_type = models.CharField(max_length=30, blank=True, null=True, verbose_name='사용자 고용형태')  # 근무형태
    join_date = models.DateField(blank=True, null=True, verbose_name='사용자 입사일')
    retire_date = models.DateField(blank=True, null=True, verbose_name='사용자 퇴사일')
    work_type = models.CharField(max_length=30, blank=True, null=True, verbose_name='직군')  # 직군 : 관리직, 제조/정규, 단기
    team = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='user_userteam', verbose_name='사용자 부서')  # 이름우측 아래 - 부서, 사업부로 활용
    job_title = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='user_userjobtitle', verbose_name='사용자 직책')  # 공정/직무로 활용
    job_level = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='user_userjoblevel', verbose_name='사용자 직급')  # 이름우측 표시 - 직급
    remark = models.CharField(max_length=100, blank=True, null=True, verbose_name='사용자 비고')
    permissions = models.CharField(max_length=100, default='0', verbose_name='사용자 권한')
    seq_order = models.IntegerField(null=True, verbose_name='부서내 순서')
    is_active = models.BooleanField(default=True)  # 접속불가 0,
    is_delete = models.BooleanField(default=False)  # 삭제상태 0, fk남겨두는 목적
    is_staff = models.BooleanField(default=False)  # 재작자는 1, 퇴사자는 0
    is_master = models.BooleanField(default=False, verbose_name='회사마스터 권한')  # 회사 관리자계정이며 is_superuser 계정은 토스트 운영자만 사용
    is_ceo = models.BooleanField(default=False, verbose_name='대표자 권한')  # 한울의 대표자 권한 (투입현황 접근권한)
    is_observer = models.BooleanField(default=False)  # 관찰자는 1, 일반유저는 0
    is_admin = models.BooleanField(default=False, verbose_name='최고관리자 권한')  # 한울 최고관리자만 볼 수 있는 통계 등 권한 부여
    profile_image = models.ImageField(upload_to=path_and_rename('profile_image/'), null=True, blank=True, default='profile_image/profile_default.png', verbose_name="프로필이미지")
    profile_doc = models.FileField(upload_to=path_and_rename('profile_doc/'), null=True, blank=True, verbose_name="이력서")

    gender = models.CharField(max_length=100, blank=True, null=True, verbose_name='성별')  # 남자, 여자
    rrn = models.CharField(max_length=100, blank=True, null=True, verbose_name='주민등록번호')
    nation = models.CharField(max_length=100, blank=True, null=True, verbose_name='국적')  # 내국인, 외국인, F4 등
    insurance = models.CharField(max_length=100, blank=True, null=True, verbose_name='4대보험 취득정보')
    bank = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='user_bank', verbose_name='은행')
    account_code = models.CharField(max_length=100, blank=True, null=True, verbose_name='계좌번호')
    account_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='예금주')
    company_card = models.ForeignKey('CompanyCard', models.SET_NULL, null=True, blank=True, related_name='user_company_card', verbose_name='법인카드')
    customer = models.ForeignKey('FactoryCustomer', models.SET_NULL, null=True, blank=True, related_name='working_customer')  # 현재파견지
    subsidiary = models.ForeignKey('FactoryCustomer', models.SET_NULL, null=True, blank=True, related_name='user_subsidiary')  #

    leave_manage_access = models.BooleanField(default=False)  # 연차관리 접근권한
    salary_manage_access = models.BooleanField(default=False)  # 급여정산/급여대장 접근권한
    company_card_access = models.BooleanField(default=False)  # 법인카드/경비 접근권한
    menu_access = models.TextField(blank=True, null=True, verbose_name='메뉴권한')

    created_by = models.ForeignKey('UserMaster', models.SET_NULL, null=True, related_name='user_createdby', verbose_name='작성자')
    updated_by = models.ForeignKey('UserMaster', models.SET_NULL, null=True, related_name='user_updatedby', verbose_name='편집자')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='작성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='편집일')
    company = models.ForeignKey('CompanyMaster', models.CASCADE, null=True, related_name='user_company', verbose_name='사용자 회사')


class CodeGroup(models.TextChoices):
    TEAM = 'team', '팀'
    JOB_TITLE = 'job_title', '직책'
    JOB_LEVEL = 'job_level', '직급'
    BOARD_CATEGORY = 'board_category', '게시판 카테고리'
    EVENT_CATEGORY = 'event_category', '이벤트 카테고리'
    PROJECT_CATEGORY = 'project_category', '프로젝트 카테고리'
    ASSET_CATEGORY = 'asset_category', '자산 종류'
    IP_ADDRESS = 'ip_address', 'IP 주소'
    BANK = 'bank', '은행'
    CUSTOMER_CLASS = 'customer_class', '대분류'
    CARD_ACCOUNT = 'card_account', '카드 계정과목'
    COST_ACCOUNT = 'cost_account', '비용 계정과목'
    RECRUIT_SITE = 'recruit_site', '공고 사이트'
    DAILY_WAGE = 'daily_wage', '일급 종류'
    DAILY_WORKTIME = 'daily_worktime', '근무 시간'
    SUBSIDIARY = 'subsidiary', '관리법인'
    MENU = 'menu', '메뉴'

    FACTORY_ITEM_UNIT = 'factory_item_unit', '단위'
    FACTORY_ITEM_CLASS = 'factory_item_class', '품목 분류'
    FACTORY_WAREHOUSE = 'factory_warehouse', '창고'
    FACTORY_PROCESS = 'factory_process', '생산 공정'
    FACTORY_WORKSHOP = 'factory_workshop', '작업장'
    FACTORY_FAULTY_CLASS = 'factory_faulty_class', '불량 분류'
    FACTORY_EVENT_CATEGORY = 'factory_event_category', '생산일정 카테고리'


# 하위 코드마스터
class CodeMaster(models.Model):
    class Meta:
        unique_together = ('company', 'group', 'name')

    group = models.CharField(max_length=100, choices=CodeGroup.choices, null=True, blank=True, verbose_name="그룹코드")
    name = models.CharField(max_length=100, verbose_name='항목명')
    desc1 = models.CharField(max_length=100, null=True, blank=True, verbose_name='항목설명1')
    desc2 = models.CharField(max_length=100, null=True, blank=True, verbose_name='항목설명2')
    desc3 = models.CharField(max_length=100, null=True, blank=True, verbose_name='항목설명3')  # 이벤트는 색상
    desc4 = models.CharField(max_length=100, null=True, blank=True, verbose_name='항목설명4')
    desc5 = models.CharField(max_length=100, null=True, blank=True, verbose_name='항목설명5')
    is_default = models.BooleanField(default=False, null=True)  # default는 등록/수정/삭제 불가
    price = models.FloatField(default=0, null=True, blank=True)  # 일급 가격

    created_by = models.ForeignKey('UserMaster', models.SET_NULL, null=True, related_name='codemaster_createdby', verbose_name='작성자')
    updated_by = models.ForeignKey('UserMaster', models.SET_NULL, null=True, related_name='codemaster_updatedby', verbose_name='편집자')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='작성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='편집일')
    company = models.ForeignKey('CompanyMaster', models.CASCADE, related_name='codemaster_company', verbose_name='코드마스터 컴퍼니')
    order = models.IntegerField(null=True, blank=True, verbose_name='정렬순서')
 

# request.user.company.company_info.first.check_in 방식으로 호출
class CompanyInfo(models.Model):
    company = models.ForeignKey('CompanyMaster', models.CASCADE, null=True, related_name='company_info')
    company_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='회사 이름')
    ceo = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='company_info_ceo')
    found_date = models.DateField(null=True, blank=True, verbose_name='회사설립일')
    license = models.CharField(max_length=255, null=True, blank=True, verbose_name='사업자등록번호')
    logo = models.ImageField(upload_to=path_and_rename('company_logo/'), null=True, blank=True, verbose_name="회사로고")
    stamp = models.ImageField(upload_to=path_and_rename('company_stamp/'), null=True, blank=True, verbose_name="회사도장")
    hourly_rate = models.FloatField(default=0, null=True, blank=True)  # 표준 시급
    annual_leave_payment = models.CharField(max_length=255, null=True, blank=True, default='join_date', verbose_name='연차부여 방식')  # 입사일(join_date) or 회계일(first_jan)
    approval_email = models.BooleanField(default=False)  # True: 결재메일 발송 / False: 발송안함
    apv_memo_1 = models.TextField(null=True, blank=True)  # 휴가신청서 참고사항
    apv_memo_2 = models.TextField(null=True, blank=True)  # 출장신청서 참고사항
    apv_memo_3 = models.TextField(null=True, blank=True)  # 지출결의서 참고사항
    apv_memo_4 = models.TextField(null=True, blank=True)  # 비용청구서 참고사항
    apv_memo_5 = models.TextField(null=True, blank=True)  # 일반신청서 참고사항
    check_in = models.TimeField(null=True, default=time(9, 0))  # 기준출근시간 (09:00)
    check_out = models.TimeField(null=True, default=time(18, 0))  # 기준퇴근시간 (18:00)
    etc_p1t = models.CharField(max_length=255, null=True, blank=True, default="지급액1")  # 급여정산 : 기타 지급액1 명칭 (etc_plus_title)
    etc_p2t = models.CharField(max_length=255, null=True, blank=True, default="지급액2")
    etc_p3t = models.CharField(max_length=255, null=True, blank=True, default="지급액3")
    etc_p4t = models.CharField(max_length=255, null=True, blank=True, default="지급액4")
    etc_p5t = models.CharField(max_length=255, null=True, blank=True, default="지급액5")
    etc_m1t = models.CharField(max_length=255, null=True, blank=True, default="공제액1")  # 급여정산 : 기타 공제액1 명칭 (etc_minus_title)
    etc_m2t = models.CharField(max_length=255, null=True, blank=True, default="공제액2")
    etc_m3t = models.CharField(max_length=255, null=True, blank=True, default="공제액3")
    etc_m4t = models.CharField(max_length=255, null=True, blank=True, default="공제액4")
    etc_m5t = models.CharField(max_length=255, null=True, blank=True, default="공제액5")
    etc_m6t = models.CharField(max_length=255, null=True, blank=True, default="공제액6")
    updating_user = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='company_updating_user')  #투입현황 현재수정중인 사용자


# request.user.company.company_access.first.factory 방식으로 호출
class CompanyAccess(models.Model):
    company = models.ForeignKey('CompanyMaster', models.CASCADE, null=True, related_name='company_access')
    factory = models.BooleanField(default=True)  # True: 팩토리 메뉴 노출 / False: 숨김


class BoardMaster(models.Model):
    title = models.CharField(max_length=255, null=True, blank=True)
    content = models.TextField(null=True, blank=True)
    board_type = models.CharField(max_length=255, null=True, blank=True)  # 게시판 대분류 (업체공지-notice/토스트공지-tost/추후추가예정)
    category = models.ForeignKey(CodeMaster, models.SET_NULL, null=True, related_name='board_category')  # 게시판 내부 카테고리
    views_count = models.PositiveIntegerField(default=0)
    top_fixed_flag = models.BooleanField(default=False, null=True)  # true:상단공지 / False:없음
    upload_file = models.FileField(upload_to=path_and_rename('upload_file/'), default=None, null=True, verbose_name='첨부파일')
    is_blog = models.BooleanField(default=False)  # true: 블로그 노출 / False: 비노출
    subject = models.CharField(max_length=255, null=True, blank=True)  # 블로그 목록에서 보여줄 요약 내용
    title_image = models.ImageField(upload_to=path_and_rename('blog_image/'), null=True, blank=True, verbose_name="프로필이미지")  # 블로그 목록에서 보여줄 대표 이미지

    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='board_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='board_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    company = models.ForeignKey('CompanyMaster', models.CASCADE, null=True, related_name='board_company')


class ApvMaster(models.Model):
    CATEGORY_CHOICES = [
        (1, '휴가신청서'),
        (2, '출장신청서'),
        (3, '지출결의서'),
        (4, '비용청구서'),
        (5, '일반신청서')
    ]
    STATUS_CHOICES = [
        ('임시', '임시'),
        ('진행', '진행'),
        ('완료', '완료'),
        ('반려', '반려')
    ]
    LEAVE_CHOICES = [
        ('연차', '연차'),
        ('결혼', '결혼'),
        ('사망', '사망'),
        ('출산', '출산'),
        ('예비군/민방위', '예비군/민방위'),
        ('보건휴가', '보건휴가'),
        ('무급휴가', '무급휴가'),
        ('기타휴가', '기타휴가')
    ]
    apv_no = models.CharField(max_length=255, unique=True, blank=True)  # 결재문서 코드
    title = models.CharField(max_length=255, null=True, blank=True)  # 결재 제목
    category = models.IntegerField(choices=CATEGORY_CHOICES, null=True, blank=True)  # 결재 종류
    status = models.CharField(max_length=255, choices=STATUS_CHOICES, default='임시')  # 결재 상태
    leave_reason = models.CharField(max_length=255, choices=LEAVE_CHOICES, null=True, blank=True)  # 휴가 사유
    detail = models.TextField(null=True, blank=True)  # 상세 설명
    deadline = models.DateField(null=True, blank=True)  # 업무마감 기한
    purpose = models.CharField(max_length=255, null=True, blank=True)  # 주요 목적 / 프로젝트명
    payment_method = models.CharField(max_length=255, null=True, blank=True)  # 지불방법 / 계좌정보
    trip_with = models.CharField(max_length=255, null=True, blank=True)  # 출장 동행(여러명)
    start_datetime = models.DateTimeField(null=True, blank=True)  # 시작일
    end_datetime = models.DateTimeField(null=True, blank=True)  # 종료일
    start_half = models.CharField(max_length=255, null=True, blank=True)  # 오전/오후 반차
    end_half = models.CharField(max_length=255, null=True, blank=True)  # 오후/오후 반차
    leave_days = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)  # 총 휴가일
    apv_attach = models.FileField(upload_to=path_and_rename('apv_attach/'), null=True, blank=True)  # 첨부파일
    request_date = models.DateTimeField(null=True, blank=True)  # 결재요청일

    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='apv_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='apv_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    company = models.ForeignKey('CompanyMaster', models.CASCADE, null=True, related_name='apv_company')


class ApvSubItem(models.Model):
    approval = models.ForeignKey(ApvMaster, on_delete=models.CASCADE, related_name='apv_sub')
    item_no = models.IntegerField()
    desc1 = models.CharField(max_length=255, null=True, blank=True)
    desc2 = models.CharField(max_length=255, null=True, blank=True)
    desc3 = models.DateField(null=True, blank=True)
    price = models.BigIntegerField(null=True, blank=True)
    qty = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)
    company = models.ForeignKey('CompanyMaster', models.CASCADE, null=True, related_name='apv_sub_company')


class ApvApprover(models.Model):
    APPROVER_STATUS_CHOICES = [
        ('대기', '대기'),
        ('승인', '승인'),
        ('반려', '반려'),
    ]
    approval = models.ForeignKey(ApvMaster, on_delete=models.CASCADE, related_name='apv_approver')
    approver1 = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, related_name='approver1', null=True, blank=True)
    approver1_status = models.CharField(max_length=10, choices=APPROVER_STATUS_CHOICES, null=True, blank=True)
    approver1_date = models.DateField(null=True, blank=True)
    approver2 = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, related_name='approver2', null=True, blank=True)
    approver2_status = models.CharField(max_length=10, choices=APPROVER_STATUS_CHOICES, null=True, blank=True)
    approver2_date = models.DateField(null=True, blank=True)
    approver3 = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, related_name='approver3', null=True, blank=True)
    approver3_status = models.CharField(max_length=10, choices=APPROVER_STATUS_CHOICES, null=True, blank=True)
    approver3_date = models.DateField(null=True, blank=True)
    approver4 = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, related_name='approver4', null=True, blank=True)
    approver4_status = models.CharField(max_length=10, choices=APPROVER_STATUS_CHOICES, null=True, blank=True)
    approver4_date = models.DateField(null=True, blank=True)


class ApvCC(models.Model):
    approval = models.ForeignKey(ApvMaster, on_delete=models.CASCADE, related_name='apv_cc')
    user = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, related_name='cc_users', null=True, blank=True)


class ReadStatus(models.Model):
    board = models.ForeignKey(BoardMaster, on_delete=models.CASCADE, null=True, blank=True, related_name='readstatus_board')
    approval = models.ForeignKey(ApvMaster, on_delete=models.CASCADE, null=True, blank=True, related_name='readstatus_apv')
    user = models.ForeignKey(UserMaster, on_delete=models.CASCADE, related_name='readstatus_user')
    is_read = models.BooleanField(default=False)  # False:안읽음  /  true:읽음
    is_like = models.BooleanField(default=False)  # False:취소  /  true:좋아요
    created_at = models.DateTimeField(auto_now_add=True)
    company = models.ForeignKey('CompanyMaster', models.CASCADE, null=True, related_name='readstatus_company')


class EventMaster(models.Model):
    title = models.CharField(max_length=255, null=True, blank=True, verbose_name='제목')
    desc = models.TextField(blank=True, null=True)
    start_date = models.DateTimeField(auto_now_add=False, null=True, blank=True, verbose_name='시작일')
    end_date = models.DateTimeField(auto_now_add=False, null=True, blank=True, verbose_name='종료일')
    approval = models.ForeignKey(ApvMaster, on_delete=models.CASCADE, null=True, blank=True, related_name='event_apv')
    category = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, blank=True, related_name='event_category')
    annual_leave_days = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)  # 연차 증감일 수
    change_type = models.CharField(max_length=255, null=True, blank=True, verbose_name='조정 유형')  # 연차추가/삭감, 휴가종류, 출장목적
    change_reason = models.CharField(max_length=255, null=True, blank=True, verbose_name='조정 사유')  # 조정사유 설명
    trip_with = models.CharField(max_length=255, null=True, blank=True)  # 이벤트 동행(여러명)

    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='event_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='event_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    company = models.ForeignKey('CompanyMaster', models.CASCADE, null=True, related_name='event_company')


class WorktimeMaster(models.Model):
    work_date = models.DateField(null=True, blank=True)  # 근태등록일
    check_in = models.TimeField(null=True)  # 실제출근시간
    check_out = models.TimeField(null=True)  # 실제퇴근시간
    work_time = models.TimeField(null=True)  # 근무시간
    late_time = models.TimeField(null=True)  # 지각시간
    over_time = models.TimeField(null=True)  # 초과근무시간
    early_time = models.TimeField(null=True)  # 조기퇴근시간
    check_in_ip = models.CharField(max_length=100, null=True, blank=True)  # 출근 IP주소
    check_out_ip = models.CharField(max_length=100, null=True, blank=True)  # 퇴근 IP주소
    is_checkout = models.BooleanField(default=False)  # 퇴근처리 여부 (false=퇴근미등록, true=퇴근등록)

    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='work_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='work_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    company = models.ForeignKey('CompanyMaster', models.CASCADE, null=True, related_name='work_company')


class CompanyAsset(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'code'], name='unique_asset_code')
        ]

    name = models.CharField(max_length=255, null=True, blank=True)
    code = models.CharField(max_length=255, null=True, blank=True)
    model = models.CharField(max_length=255, null=True, blank=True)
    asset_type = models.CharField(max_length=255, null=True, blank=True)  # public 공용장비 / private 개인장비
    location = models.CharField(max_length=255, null=True, blank=True)  # 필요없어서 제거해도 됨
    info = models.TextField(blank=True, null=True)
    desc1 = models.CharField(max_length=255, null=True, blank=True)
    desc2 = models.CharField(max_length=255, null=True, blank=True)
    desc3 = models.CharField(max_length=255, null=True, blank=True)
    acq_date = models.DateField(null=True, blank=True)
    price = models.IntegerField(null=True, blank=True)
    supplier = models.CharField(max_length=255, null=True, blank=True)
    is_valid = models.BooleanField(default=True)  # True 사용, False 미사용
    image = models.ImageField(upload_to=path_and_rename('company_asset_image/'), blank=True, null=True)
    asset_category = models.ForeignKey(CodeMaster, models.SET_NULL, null=True, related_name='asset_category')  # 전자제품, 생산장비 등

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='asset_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='asset_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='asset_company')


class AssetHistory(models.Model):
    asset = models.ForeignKey(CompanyAsset, on_delete=models.CASCADE, related_name='asset_history')
    owner = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='asset_owner')
    date = models.DateField(null=True, blank=True)
    change_type = models.CharField(max_length=255, null=True, blank=True)  # 지급, 반납, 정비, 인증
    desc1 = models.CharField(max_length=255, null=True, blank=True)
    desc2 = models.CharField(max_length=255, null=True, blank=True)
    desc3 = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='asset_history_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='asset_history_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='asset_history_company')


class CompanyItem(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'code'], name='unique_asset_item_code')
        ]

    code = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    desc1 = models.CharField(max_length=255, null=True, blank=True)
    desc2 = models.CharField(max_length=255, null=True, blank=True)
    desc3 = models.CharField(max_length=255, null=True, blank=True)
    price = models.IntegerField(null=True, blank=True)
    supplier = models.CharField(max_length=255, null=True, blank=True)
    is_valid = models.BooleanField(default=True)  # True 사용, False 미사용
    safety_stock = models.FloatField(default=0, null=True, blank=True)
    asset_category = models.ForeignKey(CodeMaster, models.SET_NULL, null=True, related_name='item_category')  # 소모품, 전자제품, 생산장비 등

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='item_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='item_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='item_company')


class ItemHistory(models.Model):
    item = models.ForeignKey(CompanyItem, on_delete=models.CASCADE, related_name='item_history')
    date = models.DateField(null=True, blank=True)
    qty = models.FloatField(default=0, null=True, blank=True)
    change_type = models.CharField(max_length=255, null=True, blank=True)  # 입고, 출고
    desc1 = models.CharField(max_length=255, null=True, blank=True)
    desc2 = models.CharField(max_length=255, null=True, blank=True)
    desc3 = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='item_history_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='item_history_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='item_history_company')


class Notification(models.Model):
    user = models.ForeignKey(UserMaster, on_delete=models.CASCADE, related_name='notifications')  # 알림 수신자
    noti_type = models.CharField(max_length=255, null=True, blank=True)  # 알림 출처(공지사항, 전자결재, 캘린더 등)
    message = models.TextField(null=True, blank=True, verbose_name='알림 내용')
    content = models.TextField(null=True, blank=True, verbose_name='전달받은 내용')
    url = models.URLField(null=True, blank=True, verbose_name='알림 링크')
    is_read = models.BooleanField(default=False, verbose_name='읽음 여부')
    created_at = models.DateTimeField(auto_now_add=True)


class SalaryMaster(models.Model):
    class Meta:
        unique_together = ('year', 'month', 'company')

    year = models.PositiveIntegerField(null=True, blank=True)
    month = models.PositiveIntegerField(null=True, blank=True)
    desc1 = models.CharField(max_length=255, null=True, blank=True)
    desc2 = models.CharField(max_length=255, null=True, blank=True)
    desc3 = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='monthly_salary_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='monthly_salary_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='monthly_salary_company')


class SalaryItem(models.Model):
    class Meta:
        unique_together = ('salary', 'user', 'company')

    salary = models.ForeignKey(SalaryMaster, on_delete=models.CASCADE, related_name='items')
    user = models.ForeignKey(UserMaster, on_delete=models.CASCADE)

    base_salary = models.IntegerField(null=True, blank=True)  # 기본급 (과세 대상 포함)
    extend_salary = models.IntegerField(null=True, blank=True)  # 연장근로수당
    night_salary = models.IntegerField(null=True, blank=True)  # 야간근로수당
    holiday_salary = models.IntegerField(null=True, blank=True)  # 휴일근로수당
    meal_salary = models.IntegerField(null=True, blank=True)  # 식대 (비과세)
    drive_salary = models.IntegerField(null=True, blank=True)  # 자가운전보조수당 (비과세)
    bonus = models.IntegerField(null=True, blank=True)  # 상여금
    incentive = models.IntegerField(null=True, blank=True)  # 성과급
    etc_p1v = models.IntegerField(null=True, blank=True)  # 기타 지급액1 금액 (etc_plus_value)
    etc_p2v = models.IntegerField(null=True, blank=True)
    etc_p3v = models.IntegerField(null=True, blank=True)
    etc_p4v = models.IntegerField(null=True, blank=True)
    etc_p5v = models.IntegerField(null=True, blank=True)

    pension = models.IntegerField(null=True, blank=True)  # 국민연금 (4.5%)
    health = models.IntegerField(null=True, blank=True)  # 건강보험 (3.545%)
    care = models.IntegerField(null=True, blank=True)  # 장기요양보험 (건강보험료의 12.95%)
    unemployment = models.IntegerField(null=True, blank=True)  # 고용보험 (0.9%)
    income_tax = models.IntegerField(null=True, blank=True)  # 소득세 (간이세액표 기준)
    local_tax = models.IntegerField(null=True, blank=True)  # 주민세 (소득세의 10%)
    etc_m1v = models.IntegerField(null=True, blank=True)  # 기타 공제액1 금액 (etc_minus_value)
    etc_m2v = models.IntegerField(null=True, blank=True)
    etc_m3v = models.IntegerField(null=True, blank=True)
    etc_m4v = models.IntegerField(null=True, blank=True)
    etc_m5v = models.IntegerField(null=True, blank=True)
    etc_m6v = models.IntegerField(null=True, blank=True)

    total_salary = models.IntegerField(null=True, blank=True)  # 총 지급액 (기본급 + 각종수당 + 기타지급)
    total_deduction = models.IntegerField(null=True, blank=True)  # 총 공제액 (4대보험 + 소득세 + 주민세)
    real_salary = models.IntegerField(null=True, blank=True)  # 실수령액 (기본급 - 총공제액)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='user_salary_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='user_salary_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='user_salary_company')


class UserBaseSalary(models.Model):
    user = models.ForeignKey(UserMaster, on_delete=models.CASCADE, related_name='base_salary')
    annual_salary = models.IntegerField(null=True, blank=True)  # 계약 연봉
    base_salary = models.IntegerField(null=True, blank=True)  # 기본급 (과세 대상 포함)
    extend_salary = models.IntegerField(null=True, blank=True)  # 연장근로수당
    night_salary = models.IntegerField(null=True, blank=True)  # 야간근로수당
    holiday_salary = models.IntegerField(null=True, blank=True)  # 휴일근로수당
    meal_salary = models.IntegerField(null=True, blank=True)  # 식대 (비과세)
    drive_salary = models.IntegerField(null=True, blank=True)  # 자가운전보조수당 (비과세)
    bonus = models.IntegerField(null=True, blank=True)  # 상여금
    incentive = models.IntegerField(null=True, blank=True)  # 성과급
    etc_p1v = models.IntegerField(null=True, blank=True)  # 기타 지급액1 금액 (etc_plus_value)
    etc_p2v = models.IntegerField(null=True, blank=True)
    etc_p3v = models.IntegerField(null=True, blank=True)
    etc_p4v = models.IntegerField(null=True, blank=True)
    etc_p5v = models.IntegerField(null=True, blank=True)

    pension = models.IntegerField(null=True, blank=True)  # 국민연금 (4.5%)
    health = models.IntegerField(null=True, blank=True)  # 건강보험 (3.545%)
    care = models.IntegerField(null=True, blank=True)  # 장기요양보험 (건강보험료의 12.95%)
    unemployment = models.IntegerField(null=True, blank=True)  # 고용보험 (0.9%)
    income_tax = models.IntegerField(null=True, blank=True)  # 소득세 (간이세액표 기준)
    local_tax = models.IntegerField(null=True, blank=True)  # 주민세 (소득세의 10%)
    etc_m1v = models.IntegerField(null=True, blank=True)  # 기타 공제액1 금액 (etc_minus_value)
    etc_m2v = models.IntegerField(null=True, blank=True)
    etc_m3v = models.IntegerField(null=True, blank=True)
    etc_m4v = models.IntegerField(null=True, blank=True)
    etc_m5v = models.IntegerField(null=True, blank=True)
    etc_m6v = models.IntegerField(null=True, blank=True)

    total_salary = models.IntegerField(null=True, blank=True)  # 총 지급액 (기본급 + 각종수당 + 기타지급)
    total_deduction = models.IntegerField(null=True, blank=True)  # 총 공제액 (4대보험 + 소득세 + 주민세 + 기타공제)
    real_salary = models.IntegerField(null=True, blank=True)  # 실수령액 (기본급 - 총공제액)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='base_salary_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='base_salary_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='base_salary_company')


class ProjectManage(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'code'], name='unique_prj_code')
        ]

    code = models.CharField(max_length=255, null=True, blank=True)  # 프로젝트 코드(고유)
    title = models.CharField(max_length=255, null=True, blank=True)  # 프로젝트명
    detail = models.TextField(blank=True, null=True)  # 세부내용
    desc1 = models.CharField(max_length=255, null=True, blank=True)  # 기타내용1
    desc2 = models.CharField(max_length=255, null=True, blank=True)  # 기타내용2
    desc3 = models.CharField(max_length=255, null=True, blank=True)  # 기타내용3
    cat1 = models.ForeignKey(CodeMaster, models.SET_NULL, null=True, related_name='prj_cat1')  # 대분류
    cat2 = models.ForeignKey(CodeMaster, models.SET_NULL, null=True, related_name='prj_cat2')  # 중분류
    cat3 = models.ForeignKey(CodeMaster, models.SET_NULL, null=True, related_name='prj_cat3')  # 소분류
    manager = models.ForeignKey(UserMaster, models.SET_NULL, null=True, related_name='prj_manager')  # 매니저
    customer = models.CharField(max_length=255, null=True, blank=True)  # 고객사

    plan_start = models.DateField(null=True, blank=True)  # 계획시작일
    plan_end = models.DateField(null=True, blank=True)  # 계획목표일
    progress = models.IntegerField(null=True, blank=True)  # 진행률 (0~100%)
    status = models.CharField(max_length=255, null=True, blank=True)  # 상태 (완료, 진행, 중단)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='prj_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='prj_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='prj_company')

    @property
    def total_days(self):
        if self.plan_start and self.plan_end:
            if isinstance(self.plan_start, str):
                self.plan_start = datetime.strptime(self.plan_start, '%Y-%m-%d').date()
            if isinstance(self.plan_end, str):
                self.plan_end = datetime.strptime(self.plan_end, '%Y-%m-%d').date()

            company_offday_category = CodeMaster.objects.filter(company=self.company, name="회사 휴무").last()
            if not company_offday_category:
                return None

            events = EventMaster.objects.filter(company=self.company, category=company_offday_category)
            holidays = set()
            for event in events:
                if event.start_date and event.end_date:
                    current = event.start_date.date()
                    end = event.end_date.date()
                    while current <= end:
                        holidays.add(current)
                        current += timedelta(days=1)

            count = 0
            current = self.plan_start
            while current <= self.plan_end:
                if current.weekday() < 5 and current not in holidays:
                    count += 1
                current += timedelta(days=1)
            return count
        return None

    @property
    def remaining_days(self):
        if self.plan_end:
            if isinstance(self.plan_end, str):
                self.plan_end = datetime.strptime(self.plan_end, '%Y-%m-%d').date()

            today = date.today()
            company_offday_category = CodeMaster.objects.filter(company=self.company, name="회사 휴무").last()
            if not company_offday_category:
                return None

            events = EventMaster.objects.filter(company=self.company, category=company_offday_category)
            holidays = set()
            for event in events:
                if event.start_date and event.end_date:
                    current = event.start_date.date()
                    end = event.end_date.date()
                    while current <= end:
                        holidays.add(current)
                        current += timedelta(days=1)

            count = 0

            if today <= self.plan_end:
                current = today + timedelta(days=1)
                while current <= self.plan_end:
                    if current.weekday() < 5 and current not in holidays:
                        count += 1
                    current += timedelta(days=1)
            else:
                current = self.plan_end + timedelta(days=1)
                while current <= today:
                    if current.weekday() < 5 and current not in holidays:
                        count -= 1
                    current += timedelta(days=1)

            return count
        return None


class TaskManage(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'code'], name='unique_task_code')
        ]

    prj = models.ForeignKey(ProjectManage, on_delete=models.CASCADE, related_name='prj', null=True, blank=True)
    code = models.CharField(max_length=255, null=True, blank=True)  # 태스크 코드(고유)
    title = models.CharField(max_length=255, null=True, blank=True)  # 태스크명
    detail = models.TextField(blank=True, null=True)  # 세부내용
    tasker_comment = models.CharField(max_length=255, null=True, blank=True)  # 담당자 의견
    planner_comment = models.CharField(max_length=255, null=True, blank=True)  # 계획자 의견
    cat1 = models.ForeignKey(CodeMaster, models.SET_NULL, null=True, related_name='task_cat1')  # 대분류
    cat2 = models.ForeignKey(CodeMaster, models.SET_NULL, null=True, related_name='task_cat2')  # 중분류
    cat3 = models.ForeignKey(CodeMaster, models.SET_NULL, null=True, related_name='task_cat3')  # 소분류
    tasker = models.ForeignKey(UserMaster, models.SET_NULL, null=True, related_name='tasker')  # 작업자
    planner = models.ForeignKey(UserMaster, models.SET_NULL, null=True, related_name='planner')  # 계획자

    plan_start = models.DateField(null=True, blank=True)  # 계획시작일
    plan_end = models.DateField(null=True, blank=True)  # 계획목표일
    real_start = models.DateField(null=True, blank=True)  # 계획시작일
    real_end = models.DateField(null=True, blank=True)  # 계획목표일
    plan_time = models.FloatField(null=True, blank=True)  # 계획 총 소요시간
    real_time = models.FloatField(null=True, blank=True)  # 실제 총 소요시간
    progress = models.IntegerField(null=True, blank=True)  # 진행률 (0~100%)
    status = models.CharField(max_length=255, null=True, blank=True)  # 상태 (완료, 진행, 중단)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='task_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='task_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='task_company')

    @property
    def total_days(self):
        if self.plan_start and self.plan_end:
            if isinstance(self.plan_start, str):
                self.plan_start = datetime.strptime(self.plan_start, '%Y-%m-%d').date()
            if isinstance(self.plan_end, str):
                self.plan_end = datetime.strptime(self.plan_end, '%Y-%m-%d').date()

            company_offday_category = CodeMaster.objects.filter(company=self.company, name="회사 휴무").last()
            if not company_offday_category:
                return None

            events = EventMaster.objects.filter(company=self.company, category=company_offday_category)
            holidays = set()
            for event in events:
                if event.start_date and event.end_date:
                    current = event.start_date.date()
                    end = event.end_date.date()
                    while current <= end:
                        holidays.add(current)
                        current += timedelta(days=1)

            count = 0
            current = self.plan_start
            while current <= self.plan_end:
                if current.weekday() < 5 and current not in holidays:
                    count += 1
                current += timedelta(days=1)
            return count
        return None

    @property
    def remaining_days(self):
        if self.plan_end:
            if isinstance(self.plan_end, str):
                self.plan_end = datetime.strptime(self.plan_end, '%Y-%m-%d').date()

            today = date.today()
            company_offday_category = CodeMaster.objects.filter(company=self.company, name="회사 휴무").last()
            if not company_offday_category:
                return None

            events = EventMaster.objects.filter(company=self.company, category=company_offday_category)
            holidays = set()
            for event in events:
                if event.start_date and event.end_date:
                    current = event.start_date.date()
                    end = event.end_date.date()
                    while current <= end:
                        holidays.add(current)
                        current += timedelta(days=1)

            count = 0

            if today <= self.plan_end:
                current = today + timedelta(days=1)
                while current <= self.plan_end:
                    if current.weekday() < 5 and current not in holidays:
                        count += 1
                    current += timedelta(days=1)
            else:
                current = self.plan_end + timedelta(days=1)
                while current <= today:
                    if current.weekday() < 5 and current not in holidays:
                        count -= 1
                    current += timedelta(days=1)

            return count
        return None


class CommentMaster(models.Model):
    board = models.ForeignKey(BoardMaster, on_delete=models.CASCADE, null=True, blank=True, related_name='comment_board')
    approval = models.ForeignKey(ApvMaster, on_delete=models.CASCADE, null=True, blank=True, related_name='comment_apv')
    project = models.ForeignKey(ProjectManage, on_delete=models.CASCADE, null=True, blank=True, related_name='comment_prj')
    content = models.TextField()
    is_private = models.BooleanField(default=False)  # False:공개  /  true:비공개

    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='comment_created_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    company = models.ForeignKey('CompanyMaster', models.CASCADE, null=True, related_name='comment_company')






# 토스트 팩토리 영역 ------------------------------------------------------------------------------------------------------
class FactoryItem(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'code'], name='unique_factory_item_code')
        ]

    code = models.CharField(max_length=255, null=True, blank=True)  # 품번
    name = models.CharField(max_length=255, null=True, blank=True)  # 품명
    desc1 = models.CharField(max_length=255, null=True, blank=True)  # 제품정보1
    desc2 = models.CharField(max_length=255, null=True, blank=True)  # 제품정보2
    desc3 = models.CharField(max_length=255, null=True, blank=True)  # 제품정보3
    qr_code = models.CharField(max_length=255, null=True, blank=True)  # QR코드
    buy_price = models.FloatField(default=0, null=True, blank=True)  # 표준 매입가
    sell_price = models.FloatField(default=0, null=True, blank=True)  # 표준 판매가
    std_cost = models.FloatField(default=0, null=True, blank=True)  # 표준 원가
    moq = models.FloatField(default=0, null=True, blank=True)  # 최소구매수량
    safety_stock = models.FloatField(default=0, null=True, blank=True)  # 안전재고
    img = models.ImageField(upload_to=path_and_rename('item_img/'), null=True, blank=True)  # 관련 이미지
    doc = models.FileField(upload_to=path_and_rename('item_doc/'), null=True, blank=True)  # 관련 문서
    is_valid = models.BooleanField(default=True)  # True 사용, False 미사용

    unit = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='factory_item_unit', verbose_name='품목 단위')
    item_class = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='factory_item_class', verbose_name='품목 분류')
    warehouse = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='factory_item_warehouse', verbose_name='기본 창고')
    supplier = models.ForeignKey('FactoryCustomer', models.SET_NULL, null=True, related_name='factory_item_supplier', verbose_name='주 공급처')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_item_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_item_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='factory_item_company')


class FactoryCustomer(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'code'], name='unique_factory_customer_code')
        ]

    code = models.CharField(max_length=255, null=True, blank=True)  # 협력업체 코드(고유)
    name = models.CharField(max_length=255, null=True, blank=True)  # 업체명
    license = models.CharField(max_length=255, null=True, blank=True)  # 사업자등록번호
    owner_name = models.CharField(max_length=255, null=True, blank=True)  # 대표자 이름
    address = models.CharField(max_length=255, null=True, blank=True)  # 사업장 소재지
    type = models.CharField(max_length=255, null=True, blank=True)  # 업태
    item = models.CharField(max_length=255, null=True, blank=True)  # 종목
    tel = models.CharField(max_length=255, null=True, blank=True)  # 대표 전화
    fax = models.CharField(max_length=255, null=True, blank=True)  # 대표 팩스
    email = models.CharField(max_length=255, null=True, blank=True)  # 대표 메일
    charge_name = models.CharField(max_length=255, null=True, blank=True)  # 담당자 이름
    mobile = models.CharField(max_length=255, null=True, blank=True)  # 담당자 연락처
    customer_type = models.CharField(max_length=255, null=True, blank=True)  # 협력사 유형(고객사, 공급사, 공급&고객사)
    desc1 = models.CharField(max_length=255, null=True, blank=True)  # 비고
    desc2 = models.CharField(max_length=255, null=True, blank=True)  # 근무시간
    desc3 = models.CharField(max_length=255, null=True, blank=True)  # 업무내용
    desc4 = models.CharField(max_length=255, null=True, blank=True)  # 휴게시간

    manager = models.ForeignKey('UserMaster', models.SET_NULL, null=True, related_name='customer_manager', verbose_name='센터 매니저')
    customer_class = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='customer_class', verbose_name='거래처 대분류')
    default_wage = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='default_wage', verbose_name='표준 일급')
    image = models.ImageField(upload_to=path_and_rename('customer_stamp/'), null=True, blank=True, verbose_name="첨부 이미지")
    daily_field = models.JSONField(default=list, blank=True)  # 단기직 급여항목에서 보여줄 필드
    general_work_type = models.CharField(max_length=255, null=True, blank=True)  # 정규파견직 직무 (기본 제조직, 옵션 물류직)
    is_valid = models.BooleanField(default=True)  # 투입현황에서 True 사용, False 미사용
    subsidiary_code = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, blank=True, related_name='customer_subsidiary')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='customer_company')
    order = models.IntegerField(null=True, blank=True)

class FactoryBomStructure(models.Model):
    parent_item = models.ForeignKey('FactoryItem', models.CASCADE, null=True, related_name='parent_item', verbose_name='상위 품목')
    child_item = models.ForeignKey('FactoryItem', models.SET_NULL, null=True, related_name='child_item', verbose_name='하위 품목')
    part_no = models.CharField(max_length=255, null=True, blank=True)  # BOM 순서넘버
    child_qty = models.FloatField(default=0, null=True, blank=True)  # 필요수량

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='bom_structure_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='bom_structure_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='bom_structure_company')


class FactoryProStructure(models.Model):
    item = models.ForeignKey('FactoryItem', models.CASCADE, null=True, related_name='item', verbose_name='생산품목')
    process = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='process', verbose_name='생산공정')
    workshop = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='workshop', verbose_name='작업장')
    responsible = models.ForeignKey('UserMaster', models.SET_NULL, null=True, related_name='responsible', verbose_name='작업담당자')
    seq_no = models.IntegerField(null=True, blank=True)  # 공정 순서
    desc1 = models.CharField(max_length=255, null=True, blank=True)  # 기타내용1

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='process_structure_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='process_structure_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='process_structure_company')


class FactoryEvent(models.Model):
    title = models.CharField(max_length=255, null=True, blank=True, verbose_name='제목')
    desc = models.TextField(blank=True, null=True)
    start_date = models.DateTimeField(auto_now_add=False, null=True, blank=True, verbose_name='시작일')
    end_date = models.DateTimeField(auto_now_add=False, null=True, blank=True, verbose_name='종료일')
    category = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, blank=True, related_name='factory_event_category')
    event_url = models.URLField(null=True, blank=True, verbose_name='관련 링크')
    purchase = models.ForeignKey('FactoryPurchase', models.CASCADE, null=True, related_name='purchase_event')  # 발주서
    production = models.ForeignKey('FactoryProduction', models.CASCADE, null=True, related_name='production_event')  # 생산계획서
    customer_order = models.ForeignKey('FactoryCustomerOrder', models.CASCADE, null=True, related_name='customer_order_event')  # 주문서

    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_event_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_event_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    company = models.ForeignKey('CompanyMaster', models.CASCADE, null=True, related_name='factory_event_company')


class FactoryItemIn(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'code'], name='unique_factory_itemin_code')
        ]

    code = models.CharField(max_length=255, null=True, blank=True)  # 입고번호
    item = models.ForeignKey('FactoryItem', models.SET_NULL, null=True, related_name='itemin')  # 입고품목
    warehouse = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='factory_itemin_warehouse')  # 입고창고
    customer = models.ForeignKey('FactoryCustomer', models.SET_NULL, null=True, related_name='factory_itemin_supplier', verbose_name='공급사')
    date = models.DateField(auto_now_add=False, null=True, blank=True)  # 입고일
    price = models.FloatField(default=0, null=True, blank=True)  # 입고단가
    total_amount = models.FloatField(default=0, null=True, blank=True)  # 입하수량
    faulty_amount = models.FloatField(default=0, null=True, blank=True)  # 입하불량수량
    result_amount = models.FloatField(default=0, null=True, blank=True)  # 최종입고수량
    warehouse_transfer = models.BooleanField(default=False)  # 창고이동여부
    desc1 = models.CharField(max_length=255, null=True, blank=True)  # 입고정보1
    desc2 = models.CharField(max_length=255, null=True, blank=True)  # 입고정보2
    desc3 = models.CharField(max_length=255, null=True, blank=True)  # 입고정보3
    purchase = models.ForeignKey('FactoryPurchase', models.CASCADE, null=True, related_name='itemin_purchase')  # 발주서 - 구매품 입고
    production = models.ForeignKey('FactoryProduction', models.CASCADE, null=True, related_name='itemin_production')  # 생산계획서 - 생산품 입고

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_itemin_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_itemin_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='factory_itemin_company')


class FactoryItemOut(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'code'], name='unique_factory_itemout_code')
        ]

    code = models.CharField(max_length=255, null=True, blank=True)  # 출고번호
    item = models.ForeignKey('FactoryItem', models.SET_NULL, null=True, related_name='itemout')  # 출고품목
    warehouse = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='factory_itemout_warehouse')  # 출고창고
    customer = models.ForeignKey('FactoryCustomer', models.SET_NULL, null=True, related_name='factory_itemout_supplier', verbose_name='고객사')
    faulty_class = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='factory_itemout_faulty_class')  # 불량사유
    date = models.DateField(auto_now_add=False, null=True, blank=True)  # 출고일
    price = models.FloatField(default=0, null=True, blank=True)  # 출고단가
    total_amount = models.FloatField(default=0, null=True, blank=True)  # 출하수량
    faulty_amount = models.FloatField(default=0, null=True, blank=True)  # 출하불량수량
    result_amount = models.FloatField(default=0, null=True, blank=True)  # 최종출고수량
    warehouse_transfer = models.BooleanField(default=False)  # 창고이동여부
    desc1 = models.CharField(max_length=255, null=True, blank=True)  # 출고정보1
    desc2 = models.CharField(max_length=255, null=True, blank=True)  # 출고정보2
    desc3 = models.CharField(max_length=255, null=True, blank=True)  # 출고정보3
    production = models.ForeignKey('FactoryProduction', models.CASCADE, null=True, related_name='itemout_production')  # 생산계획서 - 원재료 출고
    customer_order = models.ForeignKey('FactoryCustomerOrder', models.CASCADE, null=True, related_name='itemout_customer_order')  # 주문서 - 출하품 출고
    customer_order_item = models.ForeignKey('FactoryCustomerOrderItem', models.CASCADE, null=True, related_name='itemout_customer_order_item')  # 주문서품목 - 출하품 출고

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_itemout_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_itemout_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='factory_itemout_company')


class FactoryPurchase(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'code'], name='unique_factory_purchase_code')
        ]

    code = models.CharField(max_length=255, null=True, blank=True)  # 발주서 코드(고유)
    customer = models.ForeignKey('FactoryCustomer', models.SET_NULL, null=True, related_name='factory_purchase_supplier', verbose_name='발주처')
    approver = models.ForeignKey('UserMaster', models.SET_NULL, null=True, related_name='factory_purchase_approver', verbose_name='승인자')
    is_approved = models.BooleanField(default=False)  # False:미승인  /  true:승인완료
    is_vat = models.BooleanField(default=True)  # False:vat미포함  /  true:vat포함
    price = models.FloatField(default=0, null=True, blank=True)  # 전체발주금액
    order_date = models.DateField(auto_now_add=False, null=True, blank=True)  # 발주일
    request_date = models.DateField(auto_now_add=False, null=True, blank=True)  # 납품요청일
    desc1 = models.CharField(max_length=255, null=True, blank=True)  # 기타내용1 - 참고사항
    desc2 = models.CharField(max_length=255, null=True, blank=True)  # 기타내용2 - 요청사항
    desc3 = models.CharField(max_length=255, null=True, blank=True)  # 기타내용3

    # 발주입고 관련내용
    status = models.CharField(max_length=255, null=True, blank=True)  # 발주입고현황
    receive_date = models.DateField(auto_now_add=False, null=True, blank=True)  # 실제입고일
    receive_total_price = models.FloatField(default=0, null=True, blank=True)  # 입고 공급가액

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_purchase_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_purchase_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='factory_purchase_company')


class FactoryPurchaseItem(models.Model):
    purchase = models.ForeignKey('FactoryPurchase', models.CASCADE, null=True, related_name='purchase_order')  # 발주서
    item = models.ForeignKey('FactoryItem', models.SET_NULL, null=True, related_name='purchase_order_item')  # 발주품목
    unit_price = models.FloatField(default=0, null=True, blank=True)  # 발주품목 단가
    total_price = models.FloatField(default=0, null=True, blank=True)  # 발주품목 공급가
    total_qty = models.FloatField(default=0, null=True, blank=True)  # 발주 수량
    desc1 = models.CharField(max_length=255, null=True, blank=True)  # 기타정보1
    desc2 = models.CharField(max_length=255, null=True, blank=True)  # 기타정보2

    # 발주입고 관련내용
    status = models.CharField(max_length=255, null=True, blank=True)  # 발주입고 현황
    receive_date = models.DateField(auto_now_add=False, null=True, blank=True)  # 입하일
    receive_qty = models.FloatField(default=0, null=True, blank=True)  # 입하 수량
    faulty_qty = models.FloatField(default=0, null=True, blank=True)  # 입하 불량수량
    result_qty = models.FloatField(default=0, null=True, blank=True)  # 최종 입고수량
    receive_price = models.FloatField(default=0, null=True, blank=True)  # 입고 단가
    receive_total_price = models.FloatField(default=0, null=True, blank=True)  # 입고 공급가액
    warehouse = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='factory_purchase_item_warehouse')  # 입고창고

    # 발주 당시의 품목정보를 보존
    item_code = models.CharField(max_length=255, null=True, blank=True)
    item_name = models.CharField(max_length=255, null=True, blank=True)
    item_desc1 = models.CharField(max_length=255, null=True, blank=True)
    item_desc2 = models.CharField(max_length=255, null=True, blank=True)
    item_desc3 = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_purchase_item_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_purchase_item_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='factory_purchase_item_company')


class FactoryProduction(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'code'], name='unique_factory_production_code')
        ]

    code = models.CharField(max_length=255, null=True, blank=True)  # 생산계획서 코드(고유)
    approver = models.ForeignKey('UserMaster', models.SET_NULL, null=True, related_name='factory_production_approver')  # 승인자
    item = models.ForeignKey('FactoryItem', models.SET_NULL, null=True, related_name='factory_production_item')  # 생산품목
    is_approved = models.BooleanField(default=False)  # False:미승인  /  true:승인완료
    start_date = models.DateField(auto_now_add=False, null=True, blank=True)  # 생산 시작일
    end_date = models.DateField(auto_now_add=False, null=True, blank=True)  # 생산 종료일
    total_qty = models.FloatField(default=0, null=True, blank=True)  # 계획 수량
    receive_qty = models.FloatField(default=0, null=True, blank=True)  # 총 생산량
    faulty_qty = models.FloatField(default=0, null=True, blank=True)  # 생산 불량수량
    result_qty = models.FloatField(default=0, null=True, blank=True)  # 최종 입고수량
    desc1 = models.CharField(max_length=255, null=True, blank=True)  # 기타내용1
    desc2 = models.CharField(max_length=255, null=True, blank=True)  # 기타내용2
    desc3 = models.CharField(max_length=255, null=True, blank=True)  # 기타내용3
    status = models.CharField(max_length=255, null=True, blank=True)  # 생산 현황(대기, 진행, 완료)
    warehouse = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='factory_production_warehouse')  # 생산후 입고창고

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_production_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_production_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='factory_production_company')


class FactoryProductionItem(models.Model):
    # 생산공정 관련내용
    production = models.ForeignKey('FactoryProduction', models.CASCADE, null=True, related_name='production_order')  # 생산계획서
    item = models.ForeignKey('FactoryItem', models.SET_NULL, null=True, related_name='production_order_item')  # 공정 생산품목
    total_qty = models.FloatField(default=0, null=True, blank=True)  # 공정계획 수량
    start_date = models.DateField(auto_now_add=False, null=True, blank=True)  # 공정 시작일
    end_date = models.DateField(auto_now_add=False, null=True, blank=True)  # 공정 종료일
    seq_no = models.IntegerField(null=True, blank=True)  # 공정 순서
    process = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='production_order_process', verbose_name='생산공정')
    workshop = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='production_order_workshop', verbose_name='작업장')
    responsible = models.ForeignKey('UserMaster', models.SET_NULL, null=True, related_name='production_order_responsible', verbose_name='작업담당자')
    desc1 = models.CharField(max_length=255, null=True, blank=True)  # 공정 기타정보1
    desc2 = models.CharField(max_length=255, null=True, blank=True)  # 공정 기타정보2

    # 생산입고 관련내용
    status = models.CharField(max_length=255, null=True, blank=True)  # 공정 현황(대기, 진행, 완료)
    receive_date = models.DateField(auto_now_add=False, null=True, blank=True)  # 공정 완료일
    receive_qty = models.FloatField(default=0, null=True, blank=True)  # 공정 완료수량
    faulty_qty = models.FloatField(default=0, null=True, blank=True)  # 공정 불량수량
    result_qty = models.FloatField(default=0, null=True, blank=True)  # 공정 최종수량
    faulty_class = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='production_faluty_class', verbose_name='불량사유')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_production_item_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_production_item_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='factory_production_item_company')


class FactoryQuotation(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'code'], name='unique_factory_quotation_code')
        ]

    code = models.CharField(max_length=255, null=True, blank=True)  # 발주서 코드
    approver = models.ForeignKey('UserMaster', models.SET_NULL, null=True, related_name='factory_quotation_approver')  # 견적담당자
    customer = models.ForeignKey('FactoryCustomer', models.SET_NULL, null=True, related_name='factory_quotation_customer', verbose_name='고객사')
    is_vat = models.BooleanField(default=True)  # False:vat미포함  /  true:vat포함
    price = models.FloatField(default=0, null=True, blank=True)  # 전체 견적금액
    quotation_date = models.DateField(auto_now_add=False, null=True, blank=True)  # 견적일
    request_date = models.DateField(auto_now_add=False, null=True, blank=True)  # 납기일
    desc1 = models.CharField(max_length=255, null=True, blank=True)  # 기타내용1 - 참고사항
    desc2 = models.CharField(max_length=255, null=True, blank=True)  # 기타내용2 - 요청사항
    desc3 = models.CharField(max_length=255, null=True, blank=True)  # 기타내용3 - 견적유효기간
    status = models.CharField(max_length=255, null=True, blank=True)  # 견적 진행상태(대기, 수주, 만료)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_quotation_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_quotation_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='factory_quotation_company')


class FactoryQuotationItem(models.Model):
    quotation = models.ForeignKey('FactoryQuotation', models.CASCADE, null=True, related_name='customer_quotation')  # 견적서
    item = models.ForeignKey('FactoryItem', models.SET_NULL, null=True, related_name='customer_quotation_item')  # 견적품목
    total_qty = models.FloatField(default=0, null=True, blank=True)  # 견적 수량
    unit_price = models.FloatField(default=0, null=True, blank=True)  # 견적품목 단가
    total_price = models.FloatField(default=0, null=True, blank=True)  # 견적품목 공급가
    desc1 = models.CharField(max_length=255, null=True, blank=True)  # 기타정보1
    desc2 = models.CharField(max_length=255, null=True, blank=True)  # 기타정보2

    # 견적 당시의 품목정보를 보존
    item_code = models.CharField(max_length=255, null=True, blank=True)
    item_name = models.CharField(max_length=255, null=True, blank=True)
    item_desc1 = models.CharField(max_length=255, null=True, blank=True)
    item_desc2 = models.CharField(max_length=255, null=True, blank=True)
    item_desc3 = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_quotation_item_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_quotation_item_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='factory_quotation_item_company')


class FactoryCustomerOrder(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'code'], name='unique_factory_customer_order_code')
        ]

    code = models.CharField(max_length=255, null=True, blank=True)  # 주문서 코드(고유)
    approver = models.ForeignKey('UserMaster', models.SET_NULL, null=True, related_name='factory_customer_order_approver')  # 주문담당자
    delivery_user =models.ForeignKey('UserMaster', models.SET_NULL, null=True, related_name='factory_customer_order_delivery_user')  # 출하담당자
    customer = models.ForeignKey('FactoryCustomer', models.SET_NULL, null=True, related_name='factory_customer_order_supplier', verbose_name='고객사')
    is_vat = models.BooleanField(default=True)  # False:vat미포함  /  true:vat포함
    price = models.FloatField(default=0, null=True, blank=True)  # 전체주문금액
    order_date = models.DateField(auto_now_add=False, null=True, blank=True)  # 주문일
    request_date = models.DateField(auto_now_add=False, null=True, blank=True)  # 납기일
    desc1 = models.CharField(max_length=255, null=True, blank=True)  # 기타내용1 - 참고사항
    desc2 = models.CharField(max_length=255, null=True, blank=True)  # 기타내용2 - 요청사항
    desc3 = models.CharField(max_length=255, null=True, blank=True)  # 기타내용3
    status = models.CharField(max_length=255, null=True, blank=True)  # 주문출하현황 (대기, 진행, 완료, 보류)
    delivery_date = models.DateField(auto_now_add=False, null=True, blank=True)  # 출하완료일

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_customer_order_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_customer_order_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='factory_customer_order_company')


class FactoryCustomerOrderItem(models.Model):
    customer_order = models.ForeignKey('FactoryCustomerOrder', models.CASCADE, null=True, related_name='customer_order')  # 주문서
    item = models.ForeignKey('FactoryItem', models.SET_NULL, null=True, related_name='customer_order_item')  # 주문품목
    total_qty = models.FloatField(default=0, null=True, blank=True)  # 주문 수량
    unit_price = models.FloatField(default=0, null=True, blank=True)  # 주문품목 단가
    total_price = models.FloatField(default=0, null=True, blank=True)  # 주문품목 공급가
    desc1 = models.CharField(max_length=255, null=True, blank=True)  # 기타정보1
    desc2 = models.CharField(max_length=255, null=True, blank=True)  # 기타정보2

    # 주문출하 관련내용
    delivery_date = models.DateField(auto_now_add=False, null=True, blank=True)  # 출하일
    delivery_qty = models.FloatField(default=0, null=True, blank=True)  # 출하수량
    warehouse = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='factory_customer_order_item_warehouse')  # 출하창고

    # 견적 당시의 품목정보를 보존
    item_code = models.CharField(max_length=255, null=True, blank=True)
    item_name = models.CharField(max_length=255, null=True, blank=True)
    item_desc1 = models.CharField(max_length=255, null=True, blank=True)
    item_desc2 = models.CharField(max_length=255, null=True, blank=True)
    item_desc3 = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_customer_order_item_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='factory_customer_order_item_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='factory_customer_order_item_company')


# 한울 영역 -------------------------------------------------------------------------------------------------------------
class DailyWorkOrder(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'code'], name='unique_daily_work_order_code')
        ]

    code = models.CharField(max_length=255, null=True, blank=True)  # 문서번호
    date = models.DateField(null=True, blank=True)  # 근무일
    manager = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='daily_manager')  # 담당관리자
    customer = models.ForeignKey('FactoryCustomer', models.SET_NULL, null=True, related_name='customer')  # 거래처
    subsidiary = models.ForeignKey('FactoryCustomer', models.SET_NULL, null=True, related_name='subsidiary')  # 관리법인
    request_price = models.FloatField(default=0, null=True, blank=True)  # 청구금액 총계
    pre_result_price = models.FloatField(default=0, null=True, blank=True)  # 지급합계 총계
    tax = models.FloatField(default=0, null=True, blank=True)  # 공제금 합계 3.3%
    result_price = models.FloatField(default=0, null=True, blank=True)  # 근무자 지급금액 총계
    profit = models.FloatField(default=0, null=True, blank=True)  # 예상 수익금
    status = models.CharField(max_length=255, null=True, blank=True)  # 상태 (진행, 완료)
    desc1 = models.CharField(max_length=255, null=True, blank=True)  # 비고

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='daily_work_order_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='daily_work_order_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='daily_work_order_company')


class DailyWorker(models.Model):
    work_order = models.ForeignKey('DailyWorkOrder', models.CASCADE, null=True, related_name='work_order')  # 근무지시서
    user = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='daily_worker')  # 근무자
    sign_status = models.CharField(max_length=255, null=True, blank=True)  # 서명 상태 (진행, 완료)
    image = models.ImageField(upload_to=path_and_rename('daily_worker_sign/'), null=True, blank=True)  # 전자서명 싸인
    pdf = models.FileField(upload_to=path_and_rename('daily_worker_pdf/'), null=True, blank=True)  # 계약서 pdf 파일
    date = models.DateTimeField(auto_now_add=False, null=True, blank=True)  # 전자서명 일자
    wage = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='daily_worker_wage')  # 일급 종류
    worktime = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='daily_worker_worktime')  # 근무시간 종류
    salary_date = models.DateField(null=True, blank=True)  # 입금 일자
    desc1 = models.CharField(max_length=255, null=True, blank=True)  # 비고

    base_salary = models.FloatField(null=True, blank=True)  # 기본급
    extend_salary = models.FloatField(null=True, blank=True)  # 잔업수당 (미사용)
    hanwool = models.FloatField(null=True, blank=True)  # 자체수당 (센터에 청구하지는 않지만 한울에서 근로자에게 지급하는 추가수당)
    tax = models.FloatField(null=True, blank=True)  # 공제금 3.3%
    pre_result_price = models.FloatField(null=True, blank=True)  # 지급합계 = 청구금액 - 수수료
    result_price = models.FloatField(null=True, blank=True)  # 지급금액 = 지급합계 - 공제금

    late = models.FloatField(null=True, blank=True)  # 지각금
    ot = models.FloatField(null=True, blank=True)  # 초과근무
    night = models.FloatField(null=True, blank=True)  # 야간근무
    late_ot_night = models.FloatField(null=True, blank=True)  # 지각+초과+야간
    wk = models.FloatField(null=True, blank=True)  # 주휴수당
    meal = models.FloatField(null=True, blank=True)  # 식대
    tran = models.FloatField(null=True, blank=True)  # 교통비
    early = models.FloatField(null=True, blank=True)  # 조출수당
    full = models.FloatField(null=True, blank=True)  # 만근수당
    title = models.FloatField(null=True, blank=True)  # 직책수당
    cdc = models.FloatField(null=True, blank=True)  # CDC
    extra = models.FloatField(null=True, blank=True)  # 추가지급액
    special = models.FloatField(null=True, blank=True)  # 특별수당
    promo = models.FloatField(null=True, blank=True)  # 프로모션
    work = models.FloatField(null=True, blank=True)  # 업무수당
    total = models.FloatField(null=True, blank=True)  # 청구금액

    pension = models.FloatField(null=True, blank=True)  # 국민연금
    health = models.FloatField(null=True, blank=True)  # 건강보험
    emp = models.FloatField(null=True, blank=True)  # 고용보험
    acc = models.FloatField(null=True, blank=True)  # 산재보험
    fee = models.FloatField(null=True, blank=True)  # 수수료

    start_time = models.TimeField(null=True, blank=True)  # 출근시간
    end_time = models.TimeField(null=True, blank=True)  # 퇴근시간
    basic_start_time = models.TimeField(null=True, blank=True)  # 기준출근시간
    basic_end_time = models.TimeField(null=True, blank=True)  # 기준퇴근시간
    work_dur = models.DurationField(null=True, blank=True)  # 근무시간
    basic_work_dur = models.DurationField(null=True, blank=True)  # 기준근무시간
    ext_dur = models.DurationField(null=True, blank=True)  # 연장근무시간
    night_dur = models.DurationField(null=True, blank=True)  # 야간근무시간
    late_dur = models.DurationField(null=True, blank=True)  # 지각시간
    early_dur = models.DurationField(null=True, blank=True)  # 조출시간
    total_dur = models.DurationField(null=True, blank=True)  # 총근무시간

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='daily_worker_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='daily_worker_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='daily_worker_company')

class GeneralWorkOrder(models.Model):
    manager = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='general_manager')  # 담당관리자
    customer = models.ForeignKey('FactoryCustomer', models.SET_NULL, null=True, related_name='general_customer')  # 거래처
    subsidiary = models.ForeignKey('FactoryCustomer', models.SET_NULL, null=True, related_name='general_subsidiary')  # 관리법인
    status = models.CharField(max_length=255, null=True, blank=True)  # 상태 (진행, 완료)
    desc1 = models.CharField(max_length=255, null=True, blank=True)  # 비고

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='general_work_order_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='general_work_order_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='general_work_order_company')
    
class GeneralWorker(models.Model):
    work_order = models.ForeignKey('GeneralWorkOrder', models.SET_NULL, null=True, related_name='general_work_order')  # 파견근무지시서
    user = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='general_worker')  # 파견근무자
    customer = models.ForeignKey('FactoryCustomer', models.SET_NULL, null=True, related_name='general_worker_customer')  # 거래처(workorder에서 근무자제외를 대비한 백업데이터)
    start_date = models.DateField(auto_now_add=False, null=True, blank=True)  # 파견근무 시작일
    end_date = models.DateField(auto_now_add=False, null=True, blank=True)  # 파견근무 종료일
    sign_status = models.CharField(max_length=255, null=True, blank=True)  # 서명 상태 (진행, 완료)
    image = models.ImageField(upload_to=path_and_rename('general_worker_sign/'), null=True, blank=True)  # 전자서명 싸인
    date = models.DateTimeField(auto_now_add=False, null=True, blank=True)  # 전자서명 일자
    desc1 = models.CharField(max_length=255, null=True, blank=True)  # 비고
    last_work_order = models.IntegerField(null=True, blank=True)  # 파견근무지시서 백업용
    doc = models.FileField(upload_to=path_and_rename('generalworker_doc/'), null=True, blank=True)  # 입사지원서
    pdf = models.FileField(upload_to=path_and_rename('general_worker_pdf/'), null=True, blank=True)  # 계약서 pdf 파일
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='general_worker_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='general_worker_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='general_worker_company')

class GeneralWorkerSalary(models.Model):
    work_order = models.ForeignKey('GeneralWorkOrder', models.SET_NULL, null=True, related_name='general_worker_salary_order')  # 파견근무지시서
    worker = models.ForeignKey('GeneralWorker', models.SET_NULL, null=True, related_name='general_worker_salary')  # 정규근무자 항목
    user = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='general_worker_salary_user')  # 정규근무자 사람
    date = models.DateField(null=True, blank=True)  # 급여정산 연/월
    hourly_rate = models.FloatField(default=0, null=True, blank=True)  # 기준 시급
    extra_price = models.FloatField(default=0, null=True, blank=True)  # 기타 금액 (직접인건비 정산 단계) # 기타 직접비1
    extra_price2 = models.FloatField(default=0, null=True, blank=True)  # 기타 금액 (직접인건비 정산 단계)  # 기타 직접비2
    extra_indirect_price = models.FloatField(default=0, null=True, blank=True)  # 기타 간접비1
    extra_indirect_price2 = models.FloatField(default=0, null=True, blank=True)  # 기타 간접비2
    etc_price = models.FloatField(default=0, null=True, blank=True)  # 기타 금액 (간접비 합산 단계)
    work_data = models.JSONField(default=list, blank=True)  # 근무시간
    ot_data = models.JSONField(default=list, blank=True)  # 연장
    night_data = models.JSONField(default=list, blank=True)  # 심야
    sat_data = models.JSONField(default=list, blank=True)  # 특근
    sat_ot_data = models.JSONField(default=list, blank=True)  # 특근잔업
    weekly_data = models.JSONField(default=list, blank=True)  # 주차 (주휴수당)
    etc_data = models.JSONField(default=list, blank=True)  # 기타수당
    annual_data = models.JSONField(default=list, blank=True)  # 연월차 - 텍스트
    insurance_data = models.JSONField(default=list, blank=True)  # 관리비 및 보험 요율% - 텍스트

    sum_price = models.FloatField(default=0, null=True, blank=True)  # 소계
    final_price = models.FloatField(default=0, null=True, blank=True)  # 총 청구액
    profit = models.FloatField(default=0, null=True, blank=True)  # 예상 수익금

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='general_worker_salary_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='general_worker_salary_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='general_worker_salary_company')

class MonthlySales(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['year', 'month', 'customer', 'company'], name='unique_monthly_sales')
        ]

    year = models.PositiveIntegerField(null=True, blank=True)
    month = models.PositiveIntegerField(null=True, blank=True)
    subsidiary = models.ForeignKey('FactoryCustomer', models.SET_NULL, null=True, related_name='monthly_sales_subsidiary')
    customer = models.ForeignKey('FactoryCustomer', models.SET_NULL, null=True, related_name='monthly_sales_customer')
    is_daily = models.BooleanField(default=True)  # True 사용, False 미사용
    is_general = models.BooleanField(default=True)  # True 사용, False 미사용

    daily_price = models.FloatField(null=True, blank=True)  # 단기청구액
    general_price = models.FloatField(null=True, blank=True)  # 파견청구액
    vat = models.FloatField(null=True, blank=True)  # 부가세
    total_price = models.FloatField(null=True, blank=True)  # 총 청구액
    daily_salary = models.FloatField(null=True, blank=True)  # 단기 지급액
    general_salary = models.FloatField(null=True, blank=True)  # 파견 지급액
    total_salary = models.FloatField(null=True, blank=True)  # 총 지급액
    daily_profit = models.FloatField(null=True, blank=True)  # 단기청구 이익금
    general_profit = models.FloatField(null=True, blank=True)  # 파견청구 이익금

    desc1 = models.CharField(max_length=255, null=True, blank=True)  # 예비항목1
    desc2 = models.CharField(max_length=255, null=True, blank=True)  # 예비항목2
    desc3 = models.CharField(max_length=255, null=True, blank=True)  # 예비항목3
    desc4 = models.CharField(max_length=255, null=True, blank=True)  # 예비항목4
    desc1_price = models.FloatField(null=True, blank=True)  # 예비항목1 금액
    desc2_price = models.FloatField(null=True, blank=True)  # 예비항목2 금액
    desc3_price = models.FloatField(null=True, blank=True)  # 예비항목3 금액
    desc4_price = models.FloatField(null=True, blank=True)  # 예비항목4 금액

    is_send = models.BooleanField(default=False)  # True 청구, False 미청구
    is_done = models.BooleanField(default=False)  # True 결제완료, False 결제미완료
    paid_price = models.FloatField(null=True, blank=True)  # 거래처 실지급액
    paid_date = models.DateField(null=True, blank=True)  # 결제일

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='monthly_sales_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='monthly_sales_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='monthly_sales_company')

class CompanyCard(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'code'], name='unique_company_card_code')
        ]

    code = models.CharField(max_length=255, null=True, blank=True)  # 카드번호 4자리
    name = models.CharField(max_length=255, null=True, blank=True)  # 카드별칭
    owner = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='card_owner')  # 카드소유자
    card_supplier = models.CharField(max_length=255, null=True, blank=True)  # 카드사 (농협, 기업 등)
    validation_date = models.DateField(null=True, blank=True)  # 카드만료일
    is_valid = models.BooleanField(default=True)  # True 사용, False 미사용

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='card_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='card_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='card_company')

class CompanyCardHistory(models.Model):
    card = models.ForeignKey(CompanyCard, on_delete=models.SET_NULL, null=True, blank=True, related_name='card')  # 법인카드
    user = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='user')  # 카드사용자
    card_account = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='card_account')  # 계정과목
    date = models.DateField(null=True, blank=True)  # 카드사용일
    price = models.FloatField(default=0, null=True, blank=True)  # 사용금액
    desc1 = models.CharField(max_length=255, null=True, blank=True)  # 내용
    desc2 = models.CharField(max_length=255, null=True, blank=True)  # 비고
    desc3 = models.CharField(max_length=255, null=True, blank=True)  # 예비
    image = models.ImageField(upload_to=path_and_rename('company_card_image/'), null=True, blank=True, verbose_name="첨부 이미지")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='card_history_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='card_history_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='card_history_company')

class Recruit(models.Model):
    user = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='recruit_user')  # 관리자
    subsidiary = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='recruit_subsidiary')
    recruit_site = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='recruit_site')  # 공고사이트
    customer = models.ForeignKey(FactoryCustomer, on_delete=models.SET_NULL, null=True, blank=True, related_name='recruit_customer')  # 공고센터
    start_date = models.DateField(null=True, blank=True)  # 게재일
    end_date = models.DateField(null=True, blank=True)  # 마감일
    work_type = models.CharField(max_length=255, null=True, blank=True)  # 직군
    desc1 = models.CharField(max_length=255, null=True, blank=True)  # 공고내용
    price = models.FloatField(default=0, null=True, blank=True)  # 공고금액
    desc2 = models.CharField(max_length=255, null=True, blank=True)  # 비고

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='recruit_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='recruit_updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='recruit_company')
    
class GeneralCost(models.Model):
    subsidiary = models.ForeignKey('FactoryCustomer', models.SET_NULL, null=True, related_name='general_cost_subsidiary')  # 관리법인
    customer = models.ForeignKey('FactoryCustomer', models.SET_NULL, null=True, related_name='general_cost_customer')
    cost_type = models.CharField(max_length=255, null=True, blank=True)  # 비용종류(고정비, 변동비)
    cost_account = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='cost_account')  # 비용종류(고정비, 변동비)
    date = models.DateField(null=True, blank=True)  # 비용발생일
    price = models.FloatField(default=0, null=True, blank=True)  # 금액
    desc1 = models.CharField(max_length=255, null=True, blank=True)  # 비용설명1
    desc2 = models.CharField(max_length=255, null=True, blank=True)  # 비용설명2

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='general_cost_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='general_cost_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='general_cost_company')

class PrePayment(models.Model):
    customer = models.ForeignKey('FactoryCustomer', models.SET_NULL, null=True, related_name='prepayment_customer')
    date = models.DateField(null=True, blank=True)  # 가불금 발생일
    user = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='prepayment_user')  # 가불금 신청자
    bank = models.ForeignKey('CodeMaster', models.SET_NULL, null=True, related_name='prepayment_user_bank', verbose_name='은행')
    account_code = models.CharField(max_length=100, blank=True, null=True, verbose_name='계좌번호')
    account_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='예금주')
    price = models.FloatField(default=0, null=True, blank=True)  # 가불금액
    price_result = models.CharField(max_length=255, null=True, blank=True)  # 처리유무
    deduct = models.FloatField(default=0, null=True, blank=True)  # 정산금액
    deduct_result = models.CharField(max_length=255, null=True, blank=True)  # 정산확인

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='prepayment_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='prepayment_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='prepayment_company')

class DailyReport(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'date'], name='unique_dailyreport')
        ]

    date = models.DateField(null=True, blank=True)  # 현황기준일
    data = models.JSONField(default=dict)  # 예: {"정규": [12, 10, 2], "일반": [10, 10, 0], "파트": [10, 10, 2]}
    manager = models.JSONField(default=dict)  # 예: {"홍길동": "출근입니다", "박문수": "휴가입니다", "김영희": "출근입니다"}
    version = models.PositiveIntegerField(default=1)  # 매니저 충동 방지용

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='dailyreport_created_by')
    updated_by = models.ForeignKey(UserMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name='dailyreport_updated_by')
    company = models.ForeignKey(CompanyMaster, models.CASCADE, null=True, related_name='dailyreport_company')