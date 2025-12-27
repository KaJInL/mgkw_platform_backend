from fastapi.routing import APIRouter

from application.apis.account.schema.request import LoginByPwdReq, WxCode2SessionReq, WxGetPhoneNumberReq
from application.apis.account.schema.response import LoginRes, WxMiniprogramLoginByCodeRes
from application.common.helper import ResponseHelper
from application.common.schema import BaseResponse, LoginUserInfo
from application.common.utils import WxMiniProgramUtils
from application.service.account_service import account_service

api = APIRouter()


@api.post(
    "/account/login-by-pwd",
    summary="用户密码登录",
    response_model=BaseResponse[LoginRes],
)
async def login_by_pwd(req: LoginByPwdReq):
    """
    用户密码登录
    """
    res = await account_service.login_by_pwd(req.phone_number, req.password)
    return ResponseHelper.success(res)


@api.get("/account/get-user-info", summary="获取用户信息", response_model=BaseResponse[LoginUserInfo])
async def get_user_info():
    login_user_info = await account_service.get_login_user_info()
    user_dict = login_user_info.model_dump(exclude={'auths'})
    return ResponseHelper.success(user_dict)


@api.post("/account/miniprogram/wx-login-by-code", summary="微信小程序获取session",
          response_model=BaseResponse[WxMiniprogramLoginByCodeRes])
async def wx_miniprogram_login_by_code(req: WxCode2SessionReq):
    """
    小程序登录
    """
    res = await WxMiniProgramUtils.login_by_js_code(req.code)
    openid = res.get('openid')
    token = await account_service.login_by_wx_miniprogram_openid(openid)
    if token:
        res['token'] = token
    return ResponseHelper.success(res)


@api.post("/account/miniprogram/register-by-phone-number", summary="微信小程序使用手机号进行注册")
async def wx_miniprogram_register_by_phone_number(req: WxGetPhoneNumberReq):
    """
    微信小程序使用手机号进行注册
    """
    res = await WxMiniProgramUtils.decrypt_data(req.encrypted_data, req.session_key, req.iv)
    pure_phone_number = res.get("purePhoneNumber")
    token = await account_service.wx_miniprogram_register(pure_phone_number, req.openid)
    return ResponseHelper.success({"token": token})
