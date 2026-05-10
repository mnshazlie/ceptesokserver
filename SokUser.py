from Colored import Colored
import os

# --- 1. CRITICAL FIREWALL BYPASS ---
from curl_cffi import requests


class SokUser:
    def __init__(
        self,
        phoneNumber: str,
        name: str = None,
        surname: str = None,
        email: str = None,
        accessToken: str = None,
        refreshToken: str = None,
        balance: float = None,
    ):
        self.phoneNumber = phoneNumber
        self.name = name
        self.surname = surname
        self.email = email
        self.accessToken = accessToken
        self.refreshToken = refreshToken
        self.balance = balance

        # --- 2. CHROME IMPERSONATION ---
        self.session = requests.Session(impersonate="safari15_5")

    @property
    def userTuple(self):
        return (
            self.phoneNumber,
            self.name,
            self.surname,
            self.email,
            self.accessToken,
            self.refreshToken,
            self.balance,
        )

    def updateToken(self):
        url = "https://www.sokmarket.com.tr/hesabim/win-hesabim"
        headers = {
            "X-Platform": "WEB",
            "Cookie": f"refresh_token={self.refreshToken}",
        }

        # --- 3. FORCED SESSION USAGE ---
        response = self.session.get(url, headers=headers)

        newAccess = response.cookies.get("access_token")
        newRefresh = response.cookies.get("refresh_token")

        if (
            newAccess
            and newAccess
            != "FNlmBCX9Ep544pj9IfZztWgr0ynlG3Dc-a8t7h5rsXEtGhsJhWLUbbFTGXw0qMmS3"
        ):
            self.accessToken = newAccess
            self.refreshToken = newRefresh
            print(Colored.success("Yeni refresh_token ve access_token hazırlandı"))
            return True
        else:
            print(Colored.error("Sunucu misafir token çevirdi"))
            return False

        return (self.accessToken, self.refreshToken)

    def login(self, authCode):
        token = self._fetchToken(authCode)
        if not token:
            return

        userInfo = self.fetchAccountInfo()
        if not userInfo:
            return

        return self.userTuple

    def signup(self):
        verificationId = self._requestSignupOTP()
        if not verificationId:
            return

        # NOTE: Removed input() trap. If you need signup via API,
        # it must be split into two endpoints just like login.
        print(Colored.error("API formatında input() kullanılamaz. Endpoint'i ayırın."))
        return

    def fetchQR(self):
        url = "https://www.sokmarket.com.tr/api/v1/buyers/qr-code"
        headers = {"X-Platform": "WEB", "Cookie": f"access_token={self.accessToken}"}

        print(Colored.info("QR kodu getiriliyor..."))
        # --- FORCED SESSION USAGE ---
        response = self.session.get(url, headers=headers)

        if response.status_code == 200:
            print(Colored.success("QR kodu alındı"))
            return response.json().get("code")
        else:
            print(Colored.error("QR kodu almakta hata oluştu"))
            print(response.json())
            return response.json().get("code")

    def fetchAccountInfo(self):
        url = "https://www.sokmarket.com.tr/api/v1/buyers/personal-info"
        urlWallet = "https://www.sokmarket.com.tr/api/v1/wallets/my-wallet"
        headers = {
            "X-Platform": "WEB",
            "Cookie": f"access_token={self.accessToken}; refresh_token:{self.refreshToken}",
        }

        print(Colored.info("Kişisel bilgiler getiriliyor..."))
        # --- FORCED SESSION USAGE ---
        response = self.session.get(url, headers=headers)

        if response.status_code == 200:
            print(Colored.success(f"Kişisel bilgiler getirildi"))
            data = response.json()
        else:
            print(Colored.error("Error in fetching user information"))
            print(Colored.info(response.json()))
            return response.json()

        print(Colored.info("Cüzdan bilgileri getiriliyor..."))
        # --- FORCED SESSION USAGE ---
        response = self.session.get(urlWallet, headers=headers)

        if response.status_code == 200:
            print(Colored.success(f"Cüzdan bilgileri alındı"))
            data["balance"] = response.json()["balance"]["value"]

            self.name = data["name"]
            self.surname = data["surname"]
            self.email = data["email"]
            self.balance = data["balance"]
            return data
        else:
            print(Colored.error("Kullanıcı bilgileri almakta hata oluştu"))
            print(response.json())
            return

    def _requestSignupOTP(self):
        url = "https://giris.ec.sokmarket.com.tr/api/authentication/otp-registration/generate"
        headers = {
            "X-Platform": "WEB",
            "Origin": "https://giris.ec.sokmarket.com.tr",
            "Referer": "https://giris.ec.sokmarket.com.tr/otp-register",
            "Cookie": "Service-Type=MARKET;",
        }
        payload = {
            "clientId": "buyer-web",
            "phoneNumber": str(self.phoneNumber),
            "captchaToken": "",
            "captchaAction": "generate_register_otp",
            "reCaptchaV2": False,
        }

        print(Colored.info(f"{self.phoneNumber} Numarası için SMS kodu isteniyor..."))

        response = self.session.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            print(Colored.success(f"SMS kodu gönderildi"))
            return response.json().get("verificationId")
        else:
            print(Colored.error("SMS kodu göndermekte hata oluştu"))
            print(response.json())
            return

    def _requestLoginOTP(self):
        url = "https://giris.ec.sokmarket.com.tr/api/authentication/otp/generate"
        headers = {"X-Platform": "WEB"}

        payload = {
            "clientId": "buyer-web",
            "phoneNumber": str(self.phoneNumber),
            "captchaToken": "",
            "captchaAction": "generate_login_otp",
            "reCaptchaV2": False,
        }

        print(Colored.info(f"{self.phoneNumber} Numarası için SMS kodu isteniyor..."))

        response = self.session.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            print(Colored.success(f"SMS kodu gönderildi"))
            return response.json().get("verificationId")
        else:
            print(Colored.error("SMS kodu göndermekte hata oluştu"))
            return response.json().get("code")

    def _submitOTP(self, verificationId, otpCode):
        url = "https://giris.ec.sokmarket.com.tr/api/authentication/otp/login"
        headers = {
            "X-Platform": "WEB",
            "Origin": "https://giris.ec.sokmarket.com.tr",
            "Referer": "https://giris.ec.sokmarket.com.tr/verify-otp-login",
        }

        payload = {
            "clientId": "buyer-web",
            "redirectUri": "https://www.sokmarket.com.tr/authorized",
            "scope": "cookie",
            "phoneNumber": str(self.phoneNumber),
            "otpCode": str(otpCode),
            "verificationId": str(verificationId),
            "reCaptchaV2": False,
            "captchaToken": "",
            "captchaAction": "verify_otp",
        }

        print(Colored.info("SMS kodu kontrol ediliyor..."))

        response = self.session.post(url, headers=headers, json=payload)
        authCode = response.json().get("code")

        if response.status_code == 200:
            print(Colored.success(f"SMS kodu kontrol edildi"))
            return authCode
        else:
            print(Colored.error("SMS kodu iletmekte hata oluştu..."))
            return response.json().get("code")

    def _fetchToken(self, authCode):
        url = "https://www.sokmarket.com.tr/authorized"
        headers = {"X-Platform": "WEB"}
        payload = {"code": authCode}

        print(Colored.info("Auth kodundan token getiriliyor..."))

        response = self.session.get(url, headers=headers, params=payload)

        if response.status_code == 200:
            accessToken = self.session.cookies.get_dict().get("access_token")
            refreshToken = self.session.cookies.get_dict().get("refresh_token")
            self.accessToken = accessToken
            self.refreshToken = refreshToken

            print(Colored.success(f"Access token alındı"))
            return accessToken
        else:
            print(Colored.error("Token alınmakta hata oluştu"))
            print(response.json())
            return
