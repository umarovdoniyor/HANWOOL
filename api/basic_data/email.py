import smtplib
from email.mime.text import MIMEText

B_EMAIL_HOST = 'smtp.gmail.com'
B_EMAIL_PORT = 587
B_EMAIL_USE_TLS = True
B_EMAIL_HOST_USER = 'tostoffice.com@gmail.com'
B_EMAIL_HOST_PASSWORD = 'iykv qprp asrk pdyi'

def send_approval_mail_fn(title, sub_title, recipient, url_path):
    try:
        if not recipient.email:
            # print("이메일 주소 없음")
            return

        subject = f"[토스트 오피스 - {sub_title}] {title}"
        body = f"""
        <html>
        <body>
        <p>안녕하세요, {recipient.name}님</p>
        <br>
        <p>아래와 같이 <strong>[토스트 오피스]</strong>에서 이메일 알림이 전달되었습니다.</p>
        <p>매번 수동으로 로그인한다면 '수동 로그인' 버튼을, 자동 로그인 사용중이라면 '자동 로그인' 버튼으로 결재를 확인하세요.</p>
        <br>
        <hr>
        <br>
        <p><strong>{title} - {sub_title}</strong></p>
        <br>
        <p>
        <a href="https://tostoffice.com/login/?next={url_path}" style="display:inline-block;padding:10px 20px;background-color:#6c757d;color:#fff;text-decoration:none;border-radius:5px;font-weight:bold;" target="_blank">수동 로그인 바로가기</a>
        </p>
        <br>
        <p>
        <a href="https://tostoffice.com{url_path}" style="display:inline-block;padding:10px 20px;background-color:#198754;color:#fff;text-decoration:none;border-radius:5px;font-weight:bold;" target="_blank">자동 로그인 바로가기</a>
        </p>
        <br>
        <hr>
        <br>
        <p>쉽고편한 그룹웨어, 토스트 오피스 🙂</p>
        <p>효율적인 공장관리, 토스트 팩토리 😀</p>
        <br>
        </body>
        </html>
        """
        msg = MIMEText(body, "html")
        msg['Subject'] = subject
        msg['From'] = B_EMAIL_HOST_USER
        msg['To'] = recipient.email

        # print("SMTP 연결 시도 중...")
        server = smtplib.SMTP(B_EMAIL_HOST, B_EMAIL_PORT)
        if B_EMAIL_USE_TLS:
            server.starttls()
        server.login(B_EMAIL_HOST_USER, B_EMAIL_HOST_PASSWORD)
        server.sendmail(B_EMAIL_HOST_USER, [recipient.email], msg.as_string())
        server.quit()
        # print("이메일 전송 성공")

    except Exception as e:
        print("이메일 전송 실패:", e)