from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from django.views.generic import TemplateView
from django.contrib import sitemaps
from django.contrib.sitemaps.views import sitemap
from api.sitemaps import StaticViewSitemap
from api.basic_data.index import *
from web.views import *
from api.views import *
from api.auto_select2 import *
from api.basic_data.index import *
from api.basic_data.notice import *
from api.basic_data.user import *
from api.basic_data.calendar import *
from api.basic_data.approval import *
from api.basic_data.comment import *
from api.basic_data.leave import *
from api.basic_data.worktime import *
from api.basic_data.notification import *
from api.admin.company import *
from api.admin.companyinfo import *
from api.admin.employee import *
from api.admin.salary_user import *
from api.admin.code import *
from api.admin.tost_notice import *
from api.basic_data.board import *
from api.admin.signup import *
from api.brand.blog import *
from api.basic_data.company_asset import *
from api.basic_data.company_item import *
from api.basic_data.prj_project import *
from api.basic_data.prj_task import *
from api.factory.factory_item import *
from api.factory.factory_customer import *
from api.factory.factory_code import *
from api.factory.bom_structure import *
from api.factory.pro_structure import *
from api.factory.factory_calendar import *
from api.factory.inventory_list import *
from api.factory.inventory_in import *
from api.factory.inventory_out import *
from api.factory.factory_purchase import *
from api.factory.factory_production import *
from api.factory.factory_quotation import *
from api.factory.factory_customer_order import *
from api.factory.factory_dashboard import *
from api.hanwool.company_card import *
from api.hanwool.recruit import *
from api.hanwool.daily_work import *
from api.hanwool.general_work import *
from api.hanwool.sales import *
from api.hanwool.general_cost import *
from api.hanwool.performance import *
from api.hanwool.prepayment import *
from api.hanwool.excel_export import *
from api.hanwool.kpi import *
from api.hanwool.daily_report import *
from api.hanwool.ppurio import *


custom_obtain_auth_token = CustomObtainAuthToken.as_view()

sitemaps_dict = {
    'static': StaticViewSitemap,
}

urlpatterns = [
    # 로그인 / 로그아웃
    path('', index_page, name='index_page'),
    path('index/', index_page, name='index_page'),
    path('index2/', index2_page, name='index2_page'),
    path('login/', login_page, name='login_page'),
    path('logout/', custom_logout_fn, name='logout_fn'),
    path('get_user_token/', custom_obtain_auth_token, name='custom_obtain_auth_token'),
    path('myinfo/', myinfo_page, name='myinfo_page'),
    path('myinfo_update_fn/', Myinfo_Update.as_view(), name='myinfo_update_fn'),
    path('master_password_reset_fn/', Master_Password_Reset.as_view(), name='master_password_reset_fn'),
    path('my_salary/', my_salary_page, name='my_salary_page'),
    path('my_salary_check_fn/', my_salary_check_fn, name='my_salary_check_fn'),
    path('error/', error_page, name='error_page'),
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps_dict}, name='django.contrib.sitemaps.views.sitemap'),

    # 브랜드 페이지
    path('brand/', brand_page, name='brand_page'),
    path('blog/list/', blog_list_page, name='blog_list_page'),
    path('blog/read/<int:id>/', blog_read_page, name='blog_read_page'),

    # 회원가입
    path('signup/step1/', signup_step1, name='signup_step1'),
    path('signup/step2/', signup_step2, name='signup_step2'),
    path('check-user-id/', check_user_id, name='check_user_id'),
    path('password_reset/step1/', password_reset_step1, name='password_reset_step1'),
    path('password_reset/step2/', password_reset_step2, name='password_reset_step2'),
    path('company_exit_fn/', Company_Exit.as_view(), name='company_exit_fn'),

    # 대시보드
    path('dashboard/', dashboard_page, name='dashboard_page'),
    path('company_ip_list_fn/', company_ip_list_fn, name='company_ip_list_fn'),

    # 공지사항
    path('notice/list/', notice_list_page, name='notice_list_page'),
    path('notice/read/<int:id>/', notice_read_page, name='notice_read_page'),
    path('notice/create/', notice_create_page, name='notice_create_page'),
    path('notice/create/<int:id>/', notice_create_page, name='notice_update_page'),
    path('notice_list_fn/', Notice_List.as_view(), name='notice_list_fn'),
    path('notice_create_fn/', Notice_Create.as_view(), name='notice_create_fn'),
    path('notice_update_fn/', Notice_Update.as_view(), name='notice_update_fn'),
    path('notice_delete_fn/', Notice_Delete.as_view(), name='notice_delete_fn'),
    path('notice_topfix_fn/<int:board_id>/', Notice_Topfix_Toggle.as_view(), name='notice_topfix_fn'),

    # 토스트 공지
    path('tost_notice/list/', tost_notice_list_page, name='tost_notice_list_page'),
    path('tost_notice/read/<int:id>/', tost_notice_read_page, name='tost_notice_read_page'),
    path('tost_notice/create/', tost_notice_create_page, name='tost_notice_create_page'),
    path('tost_notice/create/<int:id>/', tost_notice_create_page, name='tost_notice_update_page'),
    path('tost_notice_list_fn/', TostNotice_List.as_view(), name='tost_notice_list_fn'),
    path('tost_notice_create_fn/', TostNotice_Create.as_view(), name='tost_notice_create_fn'),
    path('tost_notice_update_fn/', TostNotice_Update.as_view(), name='tost_notice_update_fn'),
    path('tost_notice_delete_fn/', TostNotice_Delete.as_view(), name='tost_notice_delete_fn'),

    # 댓글
    path('comment_board_read_fn/<int:board_id>/', Comment_Read.as_view(), name='comment_board_read_fn'),
    path('comment_apv_read_fn/<int:approval_id>/', Comment_Read.as_view(), name='comment_apv_read_fn'),
    path('comment_project_read_fn/<int:project_id>/', Comment_Read.as_view(), name='comment_project_read_fn'),
    path('comment_board_create_fn/<int:board_id>/', Comment_Create.as_view(), name='comment_board_create_fn'),
    path('comment_apv_create_fn/<int:approval_id>/', Comment_Create.as_view(), name='comment_apv_create_fn'),
    path('comment_project_create_fn/<int:project_id>/', Comment_Create.as_view(), name='comment_project_create_fn'),
    path('comment_update_fn/<int:comment_id>/', Comment_Update.as_view(), name='comment_update_fn'),
    path('comment_delete_fn/<int:comment_id>/', Comment_Delete.as_view(), name='comment_delete_fn'),

    # 알림기능
    path('noti/list/', noti_list_page, name='noti_list_page'),
    path('noti_list_fn/', Noti_List.as_view(), name='noti_list_fn'),
    path('noti_read_update_fn/', Noti_Read_Update.as_view(), name='noti_read_update_fn'),
    path('noti_read_mass_update_fn/', Noti_Read_Mass_Update.as_view(), name='noti_read_mass_update_fn'),
    path('noti_mass_delete_fn/', Noti_Mass_Delete.as_view(), name='noti_mass_delete_fn'),

    # 게시판
    path('board/list/', board_list_page, name='board_list_page'),
    path('board/list/<int:board_id>/', board_list_page, name='board_list_page'),
    path('board/read/<int:board_id>/', board_read_page, name='board_read_page'),
    path('board/create/', board_create_page, name='board_create_page'),
    path('board/create/<int:board_id>/', board_create_page, name='board_update_page'),
    path('board_list_fn/', Board_List.as_view(), name='board_list_fn'),
    path('board_create_fn/', Board_Create.as_view(), name='board_create_fn'),
    path('board_update_fn/', Board_Update.as_view(), name='board_update_fn'),
    path('board_delete_fn/', Board_Delete.as_view(), name='board_delete_fn'),

    # 일정관리
    path('calendar/', calendar_page, name='calendar_page'),
    path('event_read_fn/', Event_Read.as_view(), name='event_read_fn'),
    path('event_create_fn/', Event_Create.as_view(), name='event_create_fn'),
    path('event_update_fn/', Event_Update.as_view(), name='event_update_fn'),
    path('event_delete_fn/', Event_Delete.as_view(), name='event_delete_fn'),

    # 전자결재
    path('approval/list/', approval_list_page, name='approval_list_page'),
    path('approval/create/<str:category_id>/', approval_create_page, name='approval_create_page'),
    path('approval/create/<str:category_id>/<str:apv_id>/', approval_create_page, name='approval_update_page'),
    path('approval/progress/<str:category_id>/<str:apv_id>/', approval_progress_page, name='approval_progress_page'),
    path('approval_list_fn/', Approval_List.as_view(), name='approval_list_fn'),
    path('approval_read_fn/', Approval_Read.as_view(), name='approval_read_fn'),
    path('approval_create_fn/', Approval_Create.as_view(), name='approval_create_fn'),
    path('approval_update_fn/', Approval_Update.as_view(), name='approval_update_fn'),
    path('approval_delete_fn/', Approval_Delete.as_view(), name='approval_delete_fn'),
    path('approval/cost/', approval_cost_page, name='approval_cost_page'),
    path('approval_cost_fn/', Approval_Cost.as_view(), name='approval_cost_fn'),

    # 근태관리
    path('worktime/list/', worktime_list_page, name='worktime_list_page'),
    path('worktime/status/', worktime_status_page, name='worktime_status_page'),
    path('worktime/report/', worktime_report_page, name='worktime_report_page'),
    path('worktime_list_fn/', Worktime_List.as_view(), name="worktime_list_fn"),
    path('worktime_delete_fn/', Worktime_Delete.as_view(), name="worktime_delete_fn"),
    path('worktime_checkin_fn/', Worktime_Create.as_view(), name="worktime_checkin_fn"),
    path('worktime_checkout_fn/', Worktime_Update.as_view(), name="worktime_checkout_fn"),
    path('worktime_checkout_admin_fn/', Worktime_Admin.as_view(), name="worktime_checkout_admin_fn"),
    path('worktime_daily_report_fn/', Worktime_daily_report.as_view(), name="worktime_daily_report_fn"),
    path('worktime_report_fn/', WorktimeReport_List.as_view(), name="worktime_report_fn"),

    # 휴가관리
    path('leave/manage/', leave_manage_page, name='leave_manage_page'),
    path('leave/report/', leave_report_page, name='leave_report_page'),
    path('leave_manage_list_fn/', LeaveManage_List.as_view(), name="leave_manage_list_fn"),
    path('leave_manage_create_fn/', LeaveManage_Create.as_view(), name="leave_manage_create_fn"),
    path('leave_manage_update_fn/', LeaveManage_Update.as_view(), name="leave_manage_update_fn"),
    path('leave_manage_delete_fn/', LeaveManage_Delete.as_view(), name="leave_manage_delete_fn"),
    path('leave_report_list_fn/', LeaveReport_List.as_view(), name="leave_report_list_fn"),

    # 프로젝트
    path('prj/prj_gantt/', prj_gantt_page, name='prj_gantt_page'),
    path('prj/prj_viewer/<int:id>/', prj_viewer_page, name='prj_viewer_page'),
    path('prj/task_gantt/', task_gantt_page, name='task_gantt_page'),
    path('prj/user_gantt/', user_gantt_page, name='user_gantt_page'),

    path('project_read_fn/', Project_Read.as_view(), name='project_read_fn'),
    path('project_create_fn/', Project_Create.as_view(), name='project_create_fn'),
    path('project_update_fn/', Project_Update.as_view(), name='project_update_fn'),
    path('project_delete_fn/', Project_Delete.as_view(), name='project_delete_fn'),
    path('task_read_fn/', Task_Read.as_view(), name='task_read_fn'),
    path('task_create_fn/', Task_Create.as_view(), name='task_create_fn'),
    path('task_update_fn/', Task_Update.as_view(), name='task_update_fn'),
    path('task_delete_fn/', Task_Delete.as_view(), name='task_delete_fn'),
    path('task_date_update_fn/', Task_Date_Update.as_view(), name='task_date_update_fn'),
    path('user_gantt_read_fn/', User_Gantt_Read.as_view(), name='user_gantt_read_fn'),
    path('company_offday_read_fn/', Company_Offday_Read.as_view(), name="company_offday_read_fn"),

    # 자산관리
    path('asset/public/', asset_public_page, name='asset_public_page'),
    path('asset/private/', asset_private_page, name='asset_private_page'),
    path('asset_manage_list_fn/', AssetManage_Read.as_view(), name='asset_manage_list_fn'),
    path('asset_manage_create_fn/', AssetManage_Create.as_view(), name='asset_manage_create_fn'),
    path('asset_manage_update_fn/', AssetManage_Update.as_view(), name='asset_manage_update_fn'),
    path('asset_manage_delete_fn/', AssetManage_Delete.as_view(), name='asset_manage_delete_fn'),
    path('asset_history_list_fn/', AssetHistory_Read.as_view(), name='asset_history_list_fn'),
    path('asset_history_create_fn/', AssetHistory_Create.as_view(), name='asset_history_create_fn'),
    path('asset_history_update_fn/', AssetHistory_Update.as_view(), name='asset_history_update_fn'),
    path('asset_history_delete_fn/', AssetHistory_Delete.as_view(), name='asset_history_delete_fn'),

    path('asset/item/', asset_item_page, name='asset_item_page'),
    path('item_manage_list_fn/', ItemManage_Read.as_view(), name='item_manage_list_fn'),
    path('item_manage_create_fn/', ItemManage_Create.as_view(), name='item_manage_create_fn'),
    path('item_manage_update_fn/', ItemManage_Update.as_view(), name='item_manage_update_fn'),
    path('item_manage_delete_fn/', ItemManage_Delete.as_view(), name='item_manage_delete_fn'),
    path('item_history_list_fn/', ItemHistory_Read.as_view(), name='item_history_list_fn'),
    path('item_history_create_fn/', ItemHistory_Create.as_view(), name='item_history_create_fn'),
    path('item_history_update_fn/', ItemHistory_Update.as_view(), name='item_history_update_fn'),
    path('item_history_delete_fn/', ItemHistory_Delete.as_view(), name='item_history_delete_fn'),

    # 조직관리
    path('employee/list/', employee_list_page, name='employee_list_page'),
    path('employee/org_chart/', org_chart_page, name='org_chart_page'),

    # 인사관리 : 직원관리 페이지
    path('admin/employee/list/', admin_employee_list_page, name='admin_employee_list_page'),
    path('admin_employee_list_fn/', Employee_Read.as_view(), name='admin_employee_list_fn'),
    path('admin_employee_create_fn/', Employee_Create.as_view(), name='admin_employee_create_fn'),
    path('admin_employee_update_fn/', Employee_Update.as_view(), name='admin_employee_update_fn'),
    path('admin_employee_delete_fn/', Employee_Delete.as_view(), name='admin_employee_delete_fn'),
    path('admin/employee/cert/<str:u>/', admin_employee_cert_page, name='admin_employee_cert_page'),

    # 인사관리 : 급여정산 페이지
    path('admin/salary/list/', salary_base_list_page, name='salary_base_list_page'),
    path('user_salary_list_fn/', UserSalary_List.as_view(), name='user_salary_list_fn'),
    path('user_salary_update_fn/', UserSalary_Update.as_view(), name='user_salary_update_fn'),
    path('monthly_salary_list_fn/', MonthlySalary_List.as_view(), name='monthly_salary_list_fn'),
    path('salary_label_update_fn/', SalaryLabel_Update.as_view(), name='salary_label_update_fn'),
    path('user_salary_excel_export/', UserSalary_ExcelExport.as_view(), name='user_salary_excel_export'),
    path('user_salary_excel_import/', UserSalary_ExcelImport.as_view(), name='user_salary_excel_import'),

    # 인사관리 : 급여대장 페이지
    path('admin/salary/history/', salary_history_page, name='salary_history_page'),
    path('salary_master_list_fn/', SalaryMaster_List.as_view(), name='salary_master_list_fn'),
    path('salary_master_create_fn/', SalaryMaster_Create.as_view(), name='salary_master_create_fn'),
    path('salary_master_update_fn/', SalaryMaster_Update.as_view(), name='salary_master_update_fn'),
    path('salary_master_delete_fn/', SalaryMaster_Delete.as_view(), name='salary_master_delete_fn'),
    path('my_salary_list_fn/', MySalary_List.as_view(), name='my_salary_list_fn'),

    # 업체관리자 : 코드관리 페이지
    path('admin/code/', admin_code_page, name='admin_code_page'),
    path('admin_code_list_fn/', Codemaster_Read.as_view(), name='admin_code_list_fn'),
    path('admin_code_create_fn/', Codemaster_Create.as_view(), name='admin_code_create_fn'),
    path('admin_code_update_fn/', Codemaster_Update.as_view(), name='admin_code_update_fn'),
    path('admin_code_delete_fn/', Codemaster_Delete.as_view(), name='admin_code_delete_fn'),

    # 업체관리자 : 환경설정 페이지
    path('admin/setting/', admin_setting_page, name='admin_setting_page'),
    path('admin_setting_read_fn/', CompanyInfo_Read.as_view(), name='admin_setting_read_fn'),
    path('admin_setting_update_fn/', CompanyInfo_Update.as_view(), name='admin_setting_update_fn'),
    path('approval_memo_update_fn/', ApprovalInfo_Update.as_view(), name='approval_memo_update_fn'),  # 전자결재 메모 수정
    path('company_menu_update_fn/', CompanyAccess_Update.as_view(), name='company_menu_update_fn'),  # 업체 메뉴 수정

    # 토스트관리자 : 회사관리 페이지
    path('admin/company/list/', admin_company_list_page, name='admin_company_list_page'),
    path('admin_company_list_fn/', Company_Read.as_view(), name='admin_company_list_fn'),
    path('admin_company_create_fn/', Company_Create.as_view(), name='admin_company_create_fn'),
    path('admin_company_update_fn/', Company_Update.as_view(), name='admin_company_update_fn'),
    path('admin_company_delete_fn/', Company_Delete.as_view(), name='admin_company_delete_fn'),


    # 토스트 팩토리 ------------------------------------------------------------------------------------------------------
    path('factory/', factory_index_page, name='factory_index_page'),
    path('factory/dashboard/', factory_dashboard_page, name='factory_dashboard_page'),
    path('factory/guide/', factory_guide_page, name='factory_guide_page'),
    path('factory/init_setup/', factory_init_setup_page, name='factory_init_setup_page'),
    path('factory_init_setup_fn/', FactoryCode_Init_Setup.as_view(), name='factory_init_setup_fn'),

    path('factory/code/', factory_code_page, name='factory_code_page'),
    path('factory_code_list_fn/', FactoryCode_Read.as_view(), name='factory_code_list_fn'),
    path('factory_code_create_fn/', FactoryCode_Create.as_view(), name='factory_code_create_fn'),
    path('factory_code_update_fn/', FactoryCode_Update.as_view(), name='factory_code_update_fn'),
    path('factory_code_delete_fn/', FactoryCode_Delete.as_view(), name='factory_code_delete_fn'),

    path('factory/item/list/', factory_item_list_page, name='factory_item_list_page'),
    path('factory_item_list_fn/', FactoryItem_Read.as_view(), name='factory_item_list_fn'),
    path('factory_item_create_fn/', FactoryItem_Create.as_view(), name='factory_item_create_fn'),
    path('factory_item_update_fn/', FactoryItem_Update.as_view(), name='factory_item_update_fn'),
    path('factory_item_delete_fn/', FactoryItem_Delete.as_view(), name='factory_item_delete_fn'),

    path('factory_bom_structure_list_fn/', BomStructure_Read.as_view(), name='factory_bom_structure_list_fn'),
    path('factory_bom_structure_create_fn/', BomStructure_Create.as_view(), name='factory_bom_structure_create_fn'),
    path('factory_bom_structure_update_fn/', BomStructure_Update.as_view(), name='factory_bom_structure_update_fn'),
    path('factory_bom_structure_delete_fn/', BomStructure_Delete.as_view(), name='factory_bom_structure_delete_fn'),

    path('factory_pro_structure_list_fn/', ProStructure_Read.as_view(), name='factory_pro_structure_list_fn'),
    path('factory_pro_structure_create_fn/', ProStructure_Create.as_view(), name='factory_pro_structure_create_fn'),
    path('factory_pro_structure_update_fn/', ProStructure_Update.as_view(), name='factory_pro_structure_update_fn'),
    path('factory_pro_structure_delete_fn/', ProStructure_Delete.as_view(), name='factory_pro_structure_delete_fn'),

    path('factory/customer/list/', factory_customer_list_page, name='factory_customer_list_page'),
    path('factory_customer_list_fn/', FactoryCustomer_Read.as_view(), name='factory_customer_list_fn'),
    path('factory_customer_create_fn/', FactoryCustomer_Create.as_view(), name='factory_customer_create_fn'),
    path('factory_customer_update_fn/', FactoryCustomer_Update.as_view(), name='factory_customer_update_fn'),
    path('factory_customer_delete_fn/', FactoryCustomer_Delete.as_view(), name='factory_customer_delete_fn'),

    path('factory/calendar/', factory_calendar_page, name='factory_calendar_page'),
    path('factory_event_read_fn/', FactoryEvent_Read.as_view(), name='factory_event_read_fn'),
    path('factory_event_create_fn/', FactoryEvent_Create.as_view(), name='factory_event_create_fn'),
    path('factory_event_update_fn/', FactoryEvent_Update.as_view(), name='factory_event_update_fn'),
    path('factory_event_delete_fn/', FactoryEvent_Delete.as_view(), name='factory_event_delete_fn'),

    path('factory/inventory/list/', factory_inventory_list_page, name='factory_inventory_list_page'),
    path('factory_inventory_list_read_fn/', InventoryList_Read.as_view(), name='factory_inventory_list_read_fn'),
    path('factory_inventory_transfer_create_fn/', InventoryTransfer_Create.as_view(), name='factory_inventory_transfer_create_fn'),
    path('factory_warehouse_list_read_fn/', WarehouseList_Read.as_view(), name='factory_warehouse_list_read_fn'),

    path('factory/inventory_in/list/', factory_inventory_in_list_page, name='factory_inventory_in_list_page'),
    path('factory_inventory_in_read_fn/', InventoryIn_Read.as_view(), name='factory_inventory_in_read_fn'),
    path('factory_inventory_in_create_fn/', InventoryIn_Create.as_view(), name='factory_inventory_in_create_fn'),
    path('factory_inventory_in_update_fn/', InventoryIn_Update.as_view(), name='factory_inventory_in_update_fn'),
    path('factory_inventory_in_delete_fn/', InventoryIn_Delete.as_view(), name='factory_inventory_in_delete_fn'),

    path('factory/inventory_out/list/', factory_inventory_out_list_page, name='factory_inventory_out_list_page'),
    path('factory_inventory_out_read_fn/', InventoryOut_Read.as_view(), name='factory_inventory_out_read_fn'),
    path('factory_inventory_out_create_fn/', InventoryOut_Create.as_view(), name='factory_inventory_out_create_fn'),
    path('factory_inventory_out_update_fn/', InventoryOut_Update.as_view(), name='factory_inventory_out_update_fn'),
    path('factory_inventory_out_delete_fn/', InventoryOut_Delete.as_view(), name='factory_inventory_out_delete_fn'),

    path('factory/purchase/list/', factory_po_list_page, name='factory_po_list_page'),
    path('factory_purchase_list_fn/', FactoryPurchase_Read.as_view(), name='factory_purchase_list_fn'),
    path('factory_purchase_create_fn/', FactoryPurchase_Create.as_view(), name='factory_purchase_create_fn'),
    path('factory_purchase_update_fn/', FactoryPurchase_Update.as_view(), name='factory_purchase_update_fn'),
    path('factory_purchase_delete_fn/', FactoryPurchase_Delete.as_view(), name='factory_purchase_delete_fn'),
    path('factory_purchase_approve_fn/', FactoryPurchase_Approve.as_view(), name='factory_purchase_approve_fn'),
    path('factory_purchase_item_list_fn/', FactoryPurchaseItem_Read.as_view(), name='factory_purchase_item_list_fn'),

    path('factory/purchase/input/', factory_po_input_page, name='factory_po_input_page'),
    path('factory_purchase_item_update_fn/', FactoryPurchaseItem_Update.as_view(), name='factory_purchase_item_update_fn'),

    path('factory/production/list/', factory_production_list_page, name='factory_production_list_page'),
    path('factory_production_list_fn/', FactoryProduction_Read.as_view(), name='factory_production_list_fn'),
    path('factory_production_create_fn/', FactoryProduction_Create.as_view(), name='factory_production_create_fn'),
    path('factory_production_update_fn/', FactoryProduction_Update.as_view(), name='factory_production_update_fn'),
    path('factory_production_delete_fn/', FactoryProduction_Delete.as_view(), name='factory_production_delete_fn'),
    path('factory_production_approve_fn/', FactoryProduction_Approve.as_view(), name='factory_production_approve_fn'),
    path('factory_production_item_list_fn/', FactoryProductionItem_Read.as_view(), name='factory_production_item_list_fn'),

    path('factory/production/status/', factory_production_status_page, name='factory_production_status_page'),
    path('factory_production_item_update_fn/', FactoryProductionItem_Update.as_view(), name='factory_production_item_update_fn'),

    path('factory/sales/quotation_list/', factory_sales_quotation_list_page, name='factory_sales_quotation_list_page'),
    path('factory_quotation_list_fn/', FactoryQuotation_Read.as_view(), name='factory_quotation_list_fn'),
    path('factory_quotation_create_fn/', FactoryQuotation_Create.as_view(), name='factory_quotation_create_fn'),
    path('factory_quotation_update_fn/', FactoryQuotation_Update.as_view(), name='factory_quotation_update_fn'),
    path('factory_quotation_delete_fn/', FactoryQuotation_Delete.as_view(), name='factory_quotation_delete_fn'),
    path('factory_quotation_approve_fn/', FactoryQuotation_Approve.as_view(), name='factory_quotation_approve_fn'),
    path('factory_quotation_item_list_fn/', FactoryQuotationItem_Read.as_view(), name='factory_quotation_item_list_fn'),

    path('factory/sales/co_list/', factory_sales_co_list_page, name='factory_sales_co_list_page'),
    path('factory_customer_order_list_fn/', FactoryCustomerOrder_Read.as_view(), name='factory_customer_order_list_fn'),
    path('factory_customer_order_create_fn/', FactoryCustomerOrder_Create.as_view(), name='factory_customer_order_create_fn'),
    path('factory_customer_order_update_fn/', FactoryCustomerOrder_Update.as_view(), name='factory_customer_order_update_fn'),
    path('factory_customer_order_delete_fn/', FactoryCustomerOrder_Delete.as_view(), name='factory_customer_order_delete_fn'),
    path('factory_customer_order_item_list_fn/', FactoryCustomerOrderItem_Read.as_view(), name='factory_customer_order_item_list_fn'),

    path('factory/sales/delivery_list/', factory_sales_delivery_list_page, name='factory_sales_delivery_list_page'),
    path('factory_customer_order_item_update_fn/', FactoryCustomerOrderItem_Update.as_view(), name='factory_customer_order_item_update_fn'),

    path('factory_dashboard_production_status_fn/', FactoryDashboard_Production_Status.as_view(), name='factory_dashboard_production_status_fn'),
    path('factory_dashboard_quotation_order_status_fn/', FactoryDashboard_Quotation_Order_Status.as_view(), name='factory_dashboard_quotation_order_status_fn'),
    path('factory_dashboard_inventory_status_fn/', FactoryDashboard_Inventory_Status.as_view(), name='factory_dashboard_inventory_status_fn'),
    path('factory_dashboard_purchase_sales_status_fn/', FactoryDashboard_Purchase_Sales_Status.as_view(), name='factory_dashboard_purchase_sales_status_fn'),
    path('factory_dashboard_production_faulty_rate_fn/', FactoryDashboard_Production_Faulty_Rate.as_view(), name='factory_dashboard_production_faulty_rate_fn'),
    path('factory_dashboard_production_delivery_status_fn/', FactoryDashboard_Production_Delivery_Status.as_view(), name='factory_dashboard_production_delivery_status_fn'),


    # 품질관리는 추후 개발예정
    path('factory/quality/document/', factory_quality_document_page, name='factory_quality_document_page'),
    path('factory/quality/claim/', factory_quality_claim_page, name='factory_quality_claim_page'),


    # 한울 --------------------------------------------------------------------------------------------------------------

    # 거래처/현장관리 : 일일근무관리
    path('daily/work_order/', daily_work_order_page, name='daily_work_order_page'),
    path('daily_work_order_list_fn/', DailyWorkOrder_Read.as_view(), name='daily_work_order_list_fn'),
    path('daily_work_order_create_fn/', DailyWorkOrder_Create.as_view(), name='daily_work_order_create_fn'),
    path('daily_work_order_update_fn/', DailyWorkOrder_Update.as_view(), name='daily_work_order_update_fn'),
    path('daily_work_order_delete_fn/', DailyWorkOrder_Delete.as_view(), name='daily_work_order_delete_fn'),

    path('factory/customer/salary/', factory_customer_salary_page, name='factory_customer_salary_page'),
    path('factory_customer_salary_update_fn/', FactoryCustomerSalary_Update.as_view(), name='factory_customer_salary_update_fn'),

    path('daily/worker_list/<int:work_order_id>/', daily_worker_list_page, name='daily_worker_list_page'),
    path('daily_worker_list_fn/', DailyWorker_Read.as_view(), name='daily_worker_list_fn'),
    path('daily/con/<int:work_order_id>/<int:worker_id>/', daily_work_contract_page, name='daily_work_contract_page'),
    path('daily_worker_save_wage_fn/', DailyWorker_Wage.as_view(), name='daily_worker_save_wage_fn'),
    path('daily_worker_save_completed_fn/', DailyWorker_Completed.as_view(), name='daily_worker_save_completed_fn'),
    path('daily_worker_save_salary_fn/', DailyWorker_Salary.as_view(), name='daily_worker_save_salary_fn'),
    path('daily_worker_sign_fn/', DailyWorker_Sign.as_view(), name='daily_worker_sign_fn'),
    path('daily/work_invoice/<int:work_order_id>/', daily_work_invoice_page, name='daily_work_invoice_page'),

    # 거래처/현장관리 : 정규파견관리
    path('general/work_order/', general_work_order_page, name='general_work_order_page'),
    path('general/work_order2/', general_work_order_page2, name='general_work_order_page2'),
    path('general_work_order_list_fn/', GeneralWorkOrder_Read.as_view(), name='general_work_order_list_fn'),
    path('general_work_order_create_fn/', GeneralWorkOrder_Create.as_view(), name='general_work_order_create_fn'),
    path('general_work_order_update_fn/', GeneralWorkOrder_Update.as_view(), name='general_work_order_update_fn'),
    path('general_work_order_delete_fn/', GeneralWorkOrder_Delete.as_view(), name='general_work_order_delete_fn'),

    path('general/worker_list/<int:work_order_id>/', general_worker_list_page, name='general_worker_list_page'),
    path('general_worker_list_fn/', GeneralWorker_Read.as_view(), name='general_worker_list_fn'),
    path('general/con/<int:work_order_id>/<int:worker_id>/', general_work_contract_page, name='general_work_contract_page'),
    path('general_worker_save_contract_fn/', GeneralWorker_Contract.as_view(), name='general_worker_save_contract_fn'),
    path('general_worker_salary_read_fn/', GeneralWorkerSalary_Read.as_view(), name='general_worker_salary_read_fn'),
    path('general_worker_salary_update_fn/', GeneralWorkerSalary_Update.as_view(), name='general_worker_salary_update_fn'),
    path('general_worker_sign_fn/', GeneralWorker_Sign.as_view(), name='general_worker_sign_fn'),
    path('general/work_invoice/<int:work_order_id>/', general_work_invoice_page, name='general_work_invoice_page'),

    # 거래처/현장관리 : 실적관리
    path('customer/performance/', performance_page, name='performance_page'),
    path('customer_performance_data_fn/', Performance_Data.as_view(), name='customer_performance_data_fn'),
    path('customer/human_performance/', human_performance_page, name='human_performance_page'),
    path('customer_human_performance_data_fn/', HumanPerformance_Data.as_view(), name='customer_human_performance_data_fn'),
    path('customer/team_performance/', team_performance_page, name='team_performance_page'),
    path('customer_team_performance_data_fn/', TeamPerformance_Data.as_view(), name='customer_team_performance_data_fn'),
    
    # 매출/지출관리 : 매출관리
    path('sales/monthly_list/', sales_monthly_list_page, name='sales_monthly_list_page'),
    path('sales_monthly_list_fn/', MonthlySales_Read.as_view(), name='sales_monthly_list_fn'),
    path('sales_monthly_create_fn/', MonthlySales_Create.as_view(), name='sales_monthly_create_fn'),
    path('sales_monthly_update_fn/', MonthlySales_Update.as_view(), name='sales_monthly_update_fn'),
    path('sales_monthly_delete_fn/', MonthlySales_Delete.as_view(), name='sales_monthly_delete_fn'),

    path('sales/monthly/claim/<int:monthly_sales_id>/', sales_monthly_claim_page, name='sales_monthly_claim_page'),
    path('sales/monthly/daily/price/<int:year>/<int:month>/<int:customer_id>/<int:monthly_sales_id>/', sales_monthly_daily_price_page, name='sales_monthly_daily_price_page'),
    path('sales_monthly_daily_price_fn/', MonthlySales_DailyPrice.as_view(), name='sales_monthly_daily_price_fn'),
    path('sales/monthly/general/price/<int:year>/<int:month>/<int:customer_id>/<int:monthly_sales_id>/', sales_monthly_general_price_page, name='sales_monthly_general_price_page'),
    path('sales_monthly_general_price_fn/', MonthlySales_GeneralPrice.as_view(), name='sales_monthly_general_price_fn'),

    # 매출/지출관리 : 결제/미수관리
    path('sales/monthly_result/', sales_monthly_result_page, name='sales_monthly_result_page'),
    path('sales_monthly_result_fn/', MonthlySales_Result.as_view(), name='sales_monthly_result_fn'),
    path('sales/monthly_result/data/', sales_monthly_result_data_page, name='sales_monthly_result_data_page'),
    path('sales_monthly_result_data_fn/', MonthlySales_Data.as_view(), name='sales_monthly_result_data_fn'),

    # 매출/지출관리 : 고정/변동비
    path('cost/general/cost_list/', general_cost_list_page, name='general_cost_list_page'),
    path('cost_general_cost_list_fn/', GeneralCost_Read.as_view(), name='cost_general_cost_list_fn'),
    path('cost_general_cost_create_fn/', GeneralCost_Create.as_view(), name='cost_general_cost_create_fn'),
    path('cost_general_cost_update_fn/', GeneralCost_Update.as_view(), name='cost_general_cost_update_fn'),
    path('cost_general_cost_delete_fn/', GeneralCost_Delete.as_view(), name='cost_general_cost_delete_fn'),
    path('cost/general/data/', general_cost_data_page, name='general_cost_data_page'),
    path('cost_general_cost_data_fn/', GeneralCost_Data.as_view(), name='cost_general_cost_data_fn'),

    # 근태/급여관리 : 소득신고자료
    path('salary/monthly_cliam/', salary_monthly_claim_page, name='salary_monthly_claim_page'),
    path('daily_worker_salary_date/', DailyWorker_SalaryDate.as_view(), name='daily_worker_salary_date'),
    path('monthly_claim_report_excel_export/', MonthlyClaimReport_ExcelExport.as_view(), name='monthly_claim_report_excel_export'),
    path('monthly_claim_bank_excel_export/', MonthlyClaimBank_ExcelExport.as_view(), name='monthly_claim_bank_excel_export'),
    path('monthly_total_report_excel_export/', MonthlyTotalReport_ExcelExport.as_view(), name='monthly_total_report_excel_export'),
    
    # 근태/급여관리 : 가불금관리
    path('salary/prepayment/', salary_prepayment_page, name='salary_prepayment_page'),
    path('salary_prepayment_list_fn/', PrePayment_Read.as_view(), name='salary_prepayment_list_fn'),
    path('salary_prepayment_create_fn/', PrePayment_Create.as_view(), name='salary_prepayment_create_fn'),
    path('salary_prepayment_update_fn/', PrePayment_Update.as_view(), name='salary_prepayment_update_fn'),
    path('salary_prepayment_delete_fn/', PrePayment_Delete.as_view(), name='salary_prepayment_delete_fn'),
    path('salary/prepayment/data/', salary_prepayment_data_page, name='salary_prepayment_data_page'),
    path('salary_prepayment_data_fn/', PrePayment_Data.as_view(), name='salary_prepayment_data_fn'),

    # 법인카드/경비 : 법인카드관리
    path('cost/company_card/', cost_company_card_page, name='cost_company_card_page'),
    path('cost_company_card_list_fn/', CompanyCard_Read.as_view(), name='cost_company_card_list_fn'),
    path('cost_company_card_create_fn/', CompanyCard_Create.as_view(), name='cost_company_card_create_fn'),
    path('cost_company_card_update_fn/', CompanyCard_Update.as_view(), name='cost_company_card_update_fn'),
    path('cost_company_card_delete_fn/', CompanyCard_Delete.as_view(), name='cost_company_card_delete_fn'),
    path('cost_company_card_history_list_fn/', CompanyCardHistory_Read.as_view(), name='cost_company_card_history_list_fn'),
    path('cost_company_card_history_create_fn/', CompanyCardHistory_Create.as_view(), name='cost_company_card_history_create_fn'),
    path('cost_company_card_history_update_fn/', CompanyCardHistory_Update.as_view(), name='cost_company_card_history_update_fn'),
    path('cost_company_card_history_delete_fn/', CompanyCardHistory_Delete.as_view(), name='cost_company_card_history_delete_fn'),
    path('cost/company_card/data/', company_card_data_page, name='company_card_data_page'),
    path('cost_company_card_data_fn/', CompanyCard_Data.as_view(), name='cost_company_card_data_fn'),

    # 법인카드/경비 : 광고/경비관리
    path('cost/recruit/', cost_recruit_page, name='cost_recruit_page'),
    path('cost_recruit_list_fn/', Recruit_Read.as_view(), name='cost_recruit_list_fn'),
    path('cost_recruit_create_fn/', Recruit_Create.as_view(), name='cost_recruit_create_fn'),
    path('cost_recruit_update_fn/', Recruit_Update.as_view(), name='cost_recruit_update_fn'),
    path('cost_recruit_delete_fn/', Recruit_Delete.as_view(), name='cost_recruit_delete_fn'),
    path('cost/recruit/data/manager', recruit_data_manager_page, name='recruit_data_manager_page'),
    path('cost_recruit_data_manager_fn/', RecruitManager_Data.as_view(), name='cost_recruit_data_manager_fn'),
    path('cost/recruit/data/', recruit_data_page, name='recruit_data_page'),
    path('cost_recruit_data_fn/', Recruit_Data.as_view(), name='cost_recruit_data_fn'),

    # 손익관리
    path('kpi/customer', kpi_customer_page, name='kpi_customer_page'),
    path('kpi_customer_data_fn/', KpiCustomer_Data.as_view(), name='kpi_customer_data_fn'),
    path('kpi/subsidiary', kpi_subsidiary_page, name='kpi_subsidiary_page'),
    path('kpi_subsidiary_data_fn/', KpiSubsidiary_Data.as_view(), name='kpi_customer_data_fn'),
    path('kpi/center', kpi_center_page, name='kpi_center_page'),
    path('kpi_center_data_fn/', KpiCenter_Data.as_view(), name='kpi_center_data_fn'),
    path('kpi_customer_summary_fn/', KpiCustomer_Summary.as_view(), name='kpi_customer_summary_fn'),
    path('kpi_subsidiary_summary_fn/', KpiSubsidiary_Summary.as_view(), name='kpi_subsidiary_summary_fn'),
    path('kpi_center_summary_fn/', KpiCenter_Summary.as_view(), name='kpi_center_summary_fn'),
    
    # 투입현황
    path('daily/report', daily_report_page, name='daily_report_page'),
    path('daily_report_list_fn/', DailyReport_Read.as_view(), name='daily_report_list_fn'),
    path('daily_report_update_fn/', DailyReport_Update.as_view(), name='daily_report_update_fn'),

    # 시스템관리 : 전자계약/서명관리
    path('admin/daily_contract_manage/', daily_contract_manage, name='daily_contract_manage'),
    path('admin/general_contract_manage/', general_contract_manage, name='general_contract_manage'),
    path('daily_contract_delete_fn/', DailyWorker_Delete.as_view(), name='daily_contract_delete_fn'),
    path('general_contract_delete_fn/', GeneralWorker_Delete.as_view(), name='general_contract_delete_fn'),

    # 알림톡 발송
    path('send_kakao_daily/', SendKakaoDaily.as_view(), name="send_kakao_daily"),
    path('send_kakao_general/', SendKakaoGeneral.as_view(), name="send_kakao_general"),

    path('view_daily_contract_document/', view_daily_contract_document, name="view_daily_contract_document"),
    path('view_general_contract_document/', view_general_contract_document, name="view_general_contract_document"),
    
    # auto_select2 urls ------------------------------------------------------------------------------------------------
    path("sel2_user/", sel2_user),
    path("sel2_user_manager/", sel2_user_manager),  # 관리직 전용
    path("sel2_my_salary/", sel2_my_salary),
    path("sel2_code_group/", sel2_code_group),
    path("sel2_code_event_category/", sel2_code_event_category),
    path("sel2_code_board_category/", sel2_code_board_category),
    path("sel2_code_asset_category/", sel2_code_asset_category),
    path("sel2_code_team/", sel2_code_team),
    path("sel2_code_job_title/", sel2_code_job_title),
    path("sel2_code_job_level/", sel2_code_job_level),
    path("sel2_code_company/", sel2_code_company),
    path("sel2_code_prj_cat1/", sel2_code_prj_cat1),
    path("sel2_code_prj_cat2/", sel2_code_prj_cat2),
    path("sel2_code_prj_cat3/", sel2_code_prj_cat3),
    path("sel2_project/", sel2_project),
    path("sel2_code_bank/", sel2_code_bank),
    path("sel2_code_card_account/", sel2_code_card_account),
    path("sel2_code_cost_account/", sel2_code_cost_account),
    path("sel2_company_card/", sel2_company_card),
    path("sel2_factory_item/", sel2_factory_item),
    path("sel2_factory_all_customer/", sel2_factory_all_customer),
    path("sel2_factory_customer/", sel2_factory_customer),
    path("sel2_factory_supplier/", sel2_factory_supplier),
    path("sel2_hanwool_subsidiary/", sel2_hanwool_subsidiary),
    path("sel2_hanwool_customer/", sel2_hanwool_customer),
    path("sel2_code_item_class/", sel2_code_item_class),
    path("sel2_code_warehouse/", sel2_code_warehouse),
    path("sel2_code_unit/", sel2_code_unit),
    path("sel2_code_process/", sel2_code_process),
    path("sel2_code_workshop/", sel2_code_workshop),
    path("sel2_code_faulty_class/", sel2_code_faulty_class),
    path("sel2_code_factory_event_category/", sel2_code_factory_event_category),
    path("sel2_code_customer_class/", sel2_code_customer_class),
    path("sel2_code_recruit_site/", sel2_code_recruit_site),
    path("sel2_code_daily_wage/", sel2_code_daily_wage),
    path("sel2_code_daily_worktime/", sel2_code_daily_worktime),
    path("sel2_code_subsidiary/", sel2_code_subsidiary),
    path("sel2_code_menu/", sel2_code_menu),

    path('daily/con_test/<int:work_order_id>/<int:worker_id>/', daily_work_contract_test_page, name='daily_work_contract_test_page'),
    
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)