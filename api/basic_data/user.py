from django import forms
from api.models import UserMaster
from django.shortcuts import render, redirect
from django.views import View
from django.db import transaction
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework import status, serializers
from django.contrib.auth import login, logout


class UserMasterSerializer(serializers.ModelSerializer):
    code = serializers.CharField(max_length=8, required=False, read_only=True)
    password = serializers.CharField(write_only=True)
    created_by = serializers.CharField(required=False, read_only=True)  # 최종작성일
    created_at = serializers.CharField(required=False, read_only=True)  # 최초작성일
    company_name = serializers.SerializerMethodField(read_only=True, required=False)

    class Meta:
        model = UserMaster
        fields = '__all__'
        optional_fields = ['company']

    def get_company_name(self, obj):
        return obj.company.name if obj.company else None


class CustomObtainAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        # is_active 체크
        # if not user.is_active:
        #     return Response({'error': '접속이 제한된 사용자입니다.'}, status=status.HTTP_403_FORBIDDEN)

        login(request, user)

        # Token.objects.filter(user=user).delete()
        # token = Token.objects.create(user=user)
        token, created = Token.objects.get_or_create(user=user)

        return Response({'token': token.key, 'user': UserMasterSerializer(user).data}, status=status.HTTP_200_OK)


def custom_logout_fn(request):
    logout(request)  # Django 기본 로그아웃 수행
    request.session.flush()  # 세션 완전 삭제

    response = redirect("/login/")  # 로그인 페이지로 이동

    # 모든 쿠키 삭제 (로그아웃 후 남아있는 정보 제거)
    cookies_to_delete = [
        "Authorization", "user_id", "is_superuser", "is_master", "permissions",
        "csrftoken", "saveid", "user_pkid"
    ]

    for cookie in cookies_to_delete:
        response.delete_cookie(cookie, path="/")

    response.delete_cookie("csrftoken", path="/")

    return response

#
# class UserCreateForm(forms.ModelForm):
#     password = forms.CharField(widget=forms.PasswordInput)
#     confirm_password = forms.CharField(widget=forms.PasswordInput)
#
#     class Meta:
#         model = UserMaster
#         fields = ['name', 'password', 'confirm_password']
#
#     def clean(self):
#         cleaned_data = super(UserCreateForm, self).clean()
#         password = cleaned_data.get("password")
#         confirm_password = cleaned_data.get("confirm_password")
#
#         if password != confirm_password:
#             raise forms.ValidationError("Passwords must match")
#
#         return cleaned_data
#
#
# class UserCreateFunc(View):
#     def get(self, request, *args, **kwargs):
#         form = UserCreateForm()
#         return render(request, 'signup.html', {'form': form})
#
#     @transaction.atomic
#     def post(self, request, *args, **kwargs):
#         form = UserCreateForm(request.POST)
#         if form.is_valid():
#             user = form.save(commit=False)
#             user.set_password(form.cleaned_data['password'])
#             user.save()
#             return redirect('login')  # 로그인 페이지로 리디렉션
#         return render(request, 'signup.html', {'form': form})
