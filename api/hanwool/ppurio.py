import os
import django
import base64
import requests
import json
import uuid
import re
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.models import DailyWorker, GeneralWorker, CodeMaster


# 뿌리고 API 경로
PPURIO_TOKEN_URL = "https://message.ppurio.com/v1/token"
PPURIO_API_URL = "https://message.ppurio.com/v1/kakao"

# 한울
PPURIO_AUTH_KEY_HW = "b5c8e723577039f8691465c3722fdfd6dc9636af98ac85e05dbedddb33e9e023"
PPURIO_ACCOUNT_HW = "leejun4885"
PPURIO_SENDER_PROFILE_HW = "@한울로지텍"
PPURIO_TEMPLATE_CODE_HW = "ppur_2025110715253423342713421"
TOKEN_FILE_HW = "ppurio_token_hw.json"

# 제이앤케이
PPURIO_AUTH_KEY_JNK = "d05ecf1eaeee33815ee36626efe1a802cb9eef5b26f2d22c4e9241d589d37aa5"
PPURIO_ACCOUNT_JNK = "leejun4886"
PPURIO_SENDER_PROFILE_JNK = "@주식회사제이앤케이"
PPURIO_TEMPLATE_CODE_JNK = "ppur_2025111016293723622780667"
TOKEN_FILE_JNK = "ppurio_token_jnk.json"


def get_access_token(account, auth_key, token_file):
    """해당 계정별 토큰 발급 및 캐싱"""
    if os.path.exists(token_file):
        with open(token_file, "r", encoding="utf-8") as f:
            token_data = json.load(f)
            token = token_data.get("token")
            expires_at = datetime.fromisoformat(token_data.get("expires_at"))
            if datetime.now() < expires_at:
                return token

    print(f"[{account}] 토큰 만료 또는 없음. 재발급 중...")
    auth_str = f"{account}:{auth_key}"
    encoded_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

    headers = {"Authorization": f"Basic {encoded_auth}"}
    response = requests.post(PPURIO_TOKEN_URL, headers=headers)
    response.raise_for_status()

    res_data = response.json()
    token = res_data.get("token")
    expired = res_data.get("expired")
    expire_time = datetime.strptime(str(expired), "%Y%m%d%H%M%S")

    with open(token_file, "w", encoding="utf-8") as f:
        json.dump({"token": token, "expires_at": expire_time.isoformat()}, f, ensure_ascii=False, indent=2)

    print(f"[{account}] 새 토큰 발급 완료.")
    return token


class PpurioClient:
    """회사(한울/제이앤케이)에 따라 설정 분기"""
    def __init__(self, company_type="HW"):
        if company_type == "JNK":
            self.auth_key = PPURIO_AUTH_KEY_JNK
            self.account = PPURIO_ACCOUNT_JNK
            self.sender_profile = PPURIO_SENDER_PROFILE_JNK
            self.template_code = PPURIO_TEMPLATE_CODE_JNK
            self.token_file = TOKEN_FILE_JNK
        else:
            self.auth_key = PPURIO_AUTH_KEY_HW
            self.account = PPURIO_ACCOUNT_HW
            self.sender_profile = PPURIO_SENDER_PROFILE_HW
            self.template_code = PPURIO_TEMPLATE_CODE_HW
            self.token_file = TOKEN_FILE_HW

        self.token = get_access_token(self.account, self.auth_key, self.token_file)
        self.url = PPURIO_API_URL
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }

    def send_kakao(self, to_number, name, vars_dict, ref_key):
        body = {
            "account": self.account,
            "messageType": "ALT",
            "senderProfile": self.sender_profile,
            "templateCode": self.template_code,
            "duplicateFlag": "N",
            "isResend": "N",
            "targetCount": 1,
            "targets": [{"to": to_number, "name": name, "changeWord": vars_dict}],
            "refKey": ref_key,
        }

        response = requests.post(self.url, headers=self.headers, data=json.dumps(body))
        print("Response:", response.text)
        response.raise_for_status()
        return response.json()

    def send_kakao2(self, targets, ref_key):
        body = {
            "account": self.account,
            "messageType": "ALT",
            "senderProfile": self.sender_profile,
            "templateCode": self.template_code,
            "duplicateFlag": "N",
            "isResend": "N",
            "targetCount": len(targets),
            "targets": targets,
            "refKey": ref_key,
        }

        response = requests.post(self.url, headers=self.headers, data=json.dumps(body))
        print("Response:", response.text)
        response.raise_for_status()
        return response.json()


class SendKakaoDaily(APIView):
    def post(self, request):
        ids = request.data.get("ids", [])
        if not ids:
            return Response({"detail": "선택된 대상이 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        results = []
        targets = []
        errors = []
        try:
            for worker_id in ids:
                worker = DailyWorker.objects.select_related("user", "work_order__subsidiary").get(id=worker_id)
                subsidiary_name = worker.work_order.subsidiary.name if worker.work_order.subsidiary else ""

                # 하이픈 제거
                raw_number = worker.user.phone or ""
                to_number = re.sub(r"[^0-9]", "", raw_number)
                if len(to_number) < 10:
                    results.append({"name": worker.user.name, "error": f"잘못된 전화번호: {raw_number}"})
                    continue

                # 어떤 회사 계정으로 발송할지 결정
                if "JNK" in subsidiary_name or "제이앤케이" in subsidiary_name:
                    company_type = "JNK"
                else:
                    company_type = "HW"

                client = PpurioClient(company_type)
                user_name = worker.user.name
                ref_key = str(uuid.uuid4())[:16]

                vars_dict = {
                    "var1": user_name,
                    "var2": f"http://www.hwltotal.co.kr/daily/con/{worker.work_order_id}/{worker.id}/?s=y",
                }
                targets.append({"to": to_number, "name": user_name, "changeWord": vars_dict})

                results.append({
                    "worker_id": worker.id,
                    "name": user_name,
                    "subsidiary": subsidiary_name,
                    "status": "",
                    "messageKey": ""
                })

            result = client.send_kakao2(targets, ref_key)
            for idx, item in enumerate(results):
                item["status"] = result.get("description", "ok")
                item["messageKey"] = result.get("messageKey", None)

        except Exception as e:
            errors.append({"name": getattr(worker.user, "name", ""), "error": str(e)})

        return Response({"results": results, "errors": errors}, status=status.HTTP_200_OK)


class SendKakaoGeneral(APIView):
    def post(self, request):
        ids = request.data.get("ids", [])
        worktime_id = request.GET.get('worktime_id', '')
        worktime = request.GET.get('worktime', '')
        wage_id = request.GET.get('wage_id', '')
        wage = request.GET.get('wage', '')
        wage_desc = request.GET.get('wage_desc', '')
        if not ids:
            return Response({"detail": "선택된 대상이 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        results = []
        targets = []
        errors = []
        try:
            for worker_id in ids:
                worker = GeneralWorker.objects.select_related("user", "work_order__subsidiary").get(id=worker_id)
                subsidiary_name = worker.work_order.subsidiary.name if worker.work_order.subsidiary else ""

                # 하이픈 제거
                raw_number = worker.user.phone or ""
                to_number = re.sub(r"[^0-9]", "", raw_number)
                if len(to_number) < 10:
                    results.append({"name": worker.user.name, "error": f"잘못된 전화번호: {raw_number}"})
                    continue

                # 어떤 회사 계정으로 발송할지 결정
                if "JNK" in subsidiary_name or "제이앤케이" in subsidiary_name:
                    company_type = "JNK"
                else:
                    company_type = "HW"

                client = PpurioClient(company_type)
                user_name = worker.user.name
                ref_key = str(uuid.uuid4())[:16]

                vars_dict = {
                    "var1": user_name,
                    "var2": f"http://www.hwltotal.co.kr/general/con/{worker.work_order_id}/{worker.id}",
                }

                targets.append({"to": to_number, "name": user_name, "changeWord": vars_dict})

                results.append({
                    "worker_id": worker.id,
                    "name": user_name,
                    "subsidiary": subsidiary_name,
                    "status": "",
                    "messageKey": ""
                })

            result = client.send_kakao2(targets, ref_key)
            for idx, item in enumerate(results):
                item["status"] = result.get("description", "ok")
                item["messageKey"] = result.get("messageKey", None)
                
        except Exception as e:
            errors.append({"name": getattr(worker.user, "name", ""), "error": str(e)})

        return Response({"results": results, "errors": errors}, status=status.HTTP_200_OK)