from django.shortcuts import render, redirect, get_object_or_404
from api.models import UserMaster, CompanyMaster
import random
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from datetime import datetime, timedelta
from api.lib import Pagenation, get_excep_msg
from django.db import transaction, IntegrityError
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


def signup_step1(request):
    if request.method == "POST":
        if "verify" in request.POST:
            # 인증코드 확인
            code_input = request.POST.get("code")
            expire_time_str = request.session.get("email_expire")
            if expire_time_str:
                expire_time = datetime.fromisoformat(expire_time_str)
                if datetime.now() > expire_time:
                    return render(request, "signup/signup_step1.html", {
                        "code_sent": True,
                        "error": "인증코드가 만료되었습니다. 다시 요청해주세요."
                    })

            if code_input == request.session.get("email_code"):
                request.session["email_verified"] = True
                return redirect("signup_step2")
            else:
                return render(request, "signup/signup_step1.html", {
                    "code_sent": True,
                    "error": "인증코드가 일치하지 않습니다."
                })

        # 인증코드 전송 제한 체크
        expire_time_str = request.session.get("email_expire")
        if expire_time_str:
            expire_time = datetime.fromisoformat(expire_time_str)
            if datetime.now() < expire_time:
                return render(request, "signup/signup_step1.html", {
                    "code_sent": True,
                    "error": "이미 인증코드를 보냈습니다. 잠시 후 다시 시도해주세요."
                })

        # 이메일 입력 및 reCAPTCHA 검증
        email = request.POST.get("email")
        recaptcha_response = request.POST.get("g-recaptcha-response")
        if not verify_recaptcha(recaptcha_response):
            return render(request, "signup/signup_step1.html", {
                "error": "로봇 인증에 실패했습니다. 다시 시도해주세요."
            })

        # 이메일 중복 체크
        if CompanyMaster.objects.filter(signup_email=email).exists():
            return render(request, "signup/signup_step1.html", {
                "error": "이미 가입된 이메일 주소입니다.",
            })

        code = str(random.randint(100000, 999999))

        request.session["email_code"] = code
        request.session["email"] = email
        request.session["email_expire"] = (datetime.now() + timedelta(minutes=3)).isoformat()

        send_verification_email(email, code, mail_type="signup")

        return render(request, "signup/signup_step1.html", {
            "code_sent": True,
            "message": "인증코드를 전송했습니다. 메일을 확인해주세요."
        })

    return render(request, "signup/signup_step1.html")


def signup_step2(request):
    if not request.session.get('email_verified'):
        return redirect('signup_step1')

    if request.method == "POST":
        signup_email = request.session.get("email")
        company_name = request.POST.get('company_name')
        user_id = request.POST.get('user_id')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        if password != password_confirm:
            return render(request, 'signup/signup_step2.html', {
                'error': '비밀번호가 일치하지 않습니다.',
            })

        if UserMaster.objects.filter(user_id=user_id).exists():
            return render(request, 'signup/signup_step2.html', {
                'error': f"이미 사용 중인 ID입니다: {user_id}",
            })

        try:
            with transaction.atomic():
                url = request.build_absolute_uri('/admin_company_create_fn/')
                data = {
                    'name': company_name,
                    'master_id': user_id,
                    'password': password,
                    'self_signup': True,
                    'signup_email': signup_email,
                }

                # 세션 쿠키 복사해서 인증 정보 유지
                session = requests.Session()
                cookies = request.COOKIES
                headers = {'X-CSRFToken': request.META.get('CSRF_COOKIE', '')}
                response = session.post(url, data=data, cookies=cookies, headers=headers)

                print("response.status_code:", response.status_code)
                print("response.text:", response.text)

                if response.status_code != 200:
                    try:
                        json_response = response.json()
                        error_message = json_response.get('message', '알 수 없는 오류')
                    except ValueError:
                        error_message = f'업체 생성 실패 (HTTP {response.status_code})'

                    return render(request, 'signup/signup_step2.html', {
                        'error': error_message
                    })

                # 가입 성공 후 완료 페이지 렌더링 전에 세션 플래그 제거
                request.session.pop('email_verified', None)

                return render(request, 'signup/signup_done.html', {
                    'company_name': company_name,
                    'user_id': user_id,
                })

        except Exception as e:
            msg = get_excep_msg(e)
            return render(request, 'signup/signup_step2.html', {'error': msg})

    return render(request, 'signup/signup_step2.html')


# def send_verification_email(email, code):
#     subject = "[토스트 오피스] 회원가입 인증코드 안내"
#     from_email = "tost.korea@gmail.com"
#     to = [email]
#
#     text_content = f"아래 인증번호를 입력해주세요.\n\n인증코드: {code}"
#     html_content = render_to_string("signup/verify_mail_template.html", {"code": code})
#
#     msg = EmailMultiAlternatives(subject, text_content, from_email, to)
#     msg.attach_alternative(html_content, "text/html")
#     msg.send()


def send_verification_email(email, code, mail_type="signup"):
    if mail_type == "signup":
        subject = "[토스트 오피스] 회원가입 인증코드 안내"
    elif mail_type == "password":
        subject = "[토스트 오피스] 비밀번호 초기화 인증코드 안내"
    else:
        subject = "[토스트 오피스] 인증코드 안내"

    from_email = "tost.korea@gmail.com"
    to = [email]

    text_content = f"아래 인증번호를 입력해주세요.\n\n인증코드: {code}"
    html_content = render_to_string("signup/verify_mail_template.html", {"code": code})

    msg = EmailMultiAlternatives(subject, text_content, from_email, to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()


@csrf_exempt
def check_user_id(request):
    user_id = request.GET.get('user_id', '')
    exists = UserMaster.objects.filter(user_id=user_id).exists()
    return JsonResponse({'exists': exists})



def password_reset_step1(request):
    if request.method == "POST":

        # 이메일 존재 여부 먼저 체크
        email = request.POST.get("email")
        if not CompanyMaster.objects.filter(signup_email=email).exists():
            return render(request, "signup/password_reset_step1.html", {
                "error": "해당 이메일로 가입한 내역이 없습니다. 다시 확인해주세요.",
            })

        if "verify" in request.POST:
            # 인증코드 확인
            code_input = request.POST.get("code")
            expire_time_str = request.session.get("email_expire")
            if expire_time_str:
                expire_time = datetime.fromisoformat(expire_time_str)
                if datetime.now() > expire_time:
                    return render(request, "signup/password_reset_step1.html", {
                        "code_sent": True,
                        "error": "인증코드가 만료되었습니다. 다시 요청해주세요."
                    })

            if code_input == request.session.get("email_code"):
                request.session["email_verified"] = True
                return redirect("password_reset_step2")
            else:
                return render(request, "signup/password_reset_step1.html", {
                    "code_sent": True,
                    "error": "인증코드가 일치하지 않습니다."
                })

        # 인증코드 전송 제한 체크
        expire_time_str = request.session.get("email_expire")
        if expire_time_str:
            expire_time = datetime.fromisoformat(expire_time_str)
            if datetime.now() < expire_time:
                return render(request, "signup/password_reset_step1.html", {
                    "code_sent": True,
                    "error": "이미 인증코드를 보냈습니다. 잠시 후 다시 시도해주세요."
                })

        recaptcha_response = request.POST.get("g-recaptcha-response")
        if not verify_recaptcha(recaptcha_response):
            return render(request, "signup/password_reset_step1.html", {
                "error": "로봇 인증에 실패했습니다. 다시 시도해주세요.",
            })

        # 인증코드 발급 및 전송
        code = str(random.randint(100000, 999999))
        request.session["email_code"] = code
        request.session["email"] = email
        request.session["email_expire"] = (datetime.now() + timedelta(minutes=3)).isoformat()

        send_verification_email(email, code, mail_type="password")

        return render(request, "signup/password_reset_step1.html", {
            "code_sent": True,
            "message": "인증코드를 전송했습니다. 메일을 확인해주세요."
        })

    return render(request, "signup/password_reset_step1.html")


def password_reset_step2(request):
    if not request.session.get('email_verified'):
        return redirect('password_reset_step1')

    email = request.session.get("email")

    # 이메일로 사용자 및 회사 정보 찾기
    company = CompanyMaster.objects.filter(signup_email=email).first()
    user = UserMaster.objects.filter(company=company, is_master=True).first() if company else None

    if not company or not user:
        return render(request, 'signup/password_reset_step2.html', {
            'error': '계정 정보를 찾을 수 없습니다.',
        })

    company_name = company.name
    user_id = user.user_id

    if request.method == "POST":
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        if password != password_confirm:
            return render(request, 'signup/password_reset_step2.html', {
                'company_name': company_name,
                'user_id': user_id,
                'error': '비밀번호가 일치하지 않습니다.',
            })

        try:
            with transaction.atomic():
                url = request.build_absolute_uri('/master_password_reset_fn/')
                data = {
                    'email': email,
                    'user_id': user_id,
                    'password': password,
                }

                # 세션 쿠키 복사해서 인증 정보 유지
                session = requests.Session()
                cookies = request.COOKIES
                headers = {'X-CSRFToken': request.META.get('CSRF_COOKIE', '')}
                response = session.post(url, data=data, cookies=cookies, headers=headers)

                print("response.status_code:", response.status_code)
                print("response.text:", response.text)

                if response.status_code != 200:
                    try:
                        json_response = response.json()
                        error_message = json_response.get('message', '알 수 없는 오류')
                    except ValueError:
                        error_message = f'비밀번호 변경 실패 (HTTP {response.status_code})'

                    return render(request, 'signup/password_reset_step2.html', {
                        'company_name': company_name,
                        'user_id': user_id,
                        'error': error_message,
                    })

                # 자바스크립트 alert + 리다이렉트 처리
                return render(request, 'signup/password_reset_step2.html', {
                    'success': True,
                })

        except Exception as e:
            msg = get_excep_msg(e)
            return render(request, 'signup/password_reset_step2.html', {
                'company_name': company_name,
                'user_id': user_id,
                'error': msg,
            })

    return render(request, 'signup/password_reset_step2.html', {
        'company_name': company_name,
        'user_id': user_id,
    })


def verify_recaptcha(recaptcha_response):
    try:
        secret_key = "6Lf2jYErAAAAAIPFSwHuJPAzT3rKCKsaOPzvqxkM"
        resp = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={
                'secret': secret_key,
                'response': recaptcha_response
            }
        )
        result = resp.json()
        return result.get('success', False)
    except Exception:
        return False