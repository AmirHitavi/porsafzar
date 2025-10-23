import hashlib
import hmac
import random

from django.conf import settings
from django.core.cache import cache


class OTPHandler:
    """OTP Handler for phone number verification"""

    PHONE_SECRET_KEY = settings.PHONE_SECRET_KEY
    OTP_TIMEOUT = 120
    MAX_ATTEMPTS = 3

    @staticmethod
    def _get_hashed_phone(phone_number):
        return hmac.new(
            OTPHandler.PHONE_SECRET_KEY.encode(), phone_number.encode(), hashlib.sha256
        ).hexdigest()

    @staticmethod
    def generate_otp(phone_number):
        hashed_phone = OTPHandler._get_hashed_phone(phone_number)
        cache_key = f"otp_{hashed_phone}"

        if cache.get(cache_key):
            return {
                "status": "error",
                "message": "OTP already sent. Please wait.",
                "code": "OTP_ALREADY_SENT",
            }

        otp_code = str(random.randint(100000, 999999))

        cache.set(cache_key, otp_code, timeout=OTPHandler.OTP_TIMEOUT)

        # TODO: Integrate with SMS service in production
        print(f"OTP for {phone_number}: {otp_code}")

        return {
            "status": "success",
            "message": "OTP sent successfully",
        }

    @staticmethod
    def verify_otp(phone_number, otp_code):
        hashed_phone = OTPHandler._get_hashed_phone(phone_number)
        otp_cache_key = f"otp_{hashed_phone}"
        stored_otp = cache.get(otp_cache_key)

        # attempts
        attempts_cache_key = f"otp_attempts_{hashed_phone}"
        cache.add(attempts_cache_key, 0, timeout=OTPHandler.OTP_TIMEOUT)
        attempts = cache.incr(attempts_cache_key)

        if attempts > OTPHandler.MAX_ATTEMPTS:
            cache.delete(otp_cache_key)
            return {
                "status": "error",
                "message": "Too many attempts. Please request a new OTP.",
                "code": "TOO_MANY_ATTEMPTS",
            }

        if stored_otp and stored_otp == otp_code:
            cache.delete_many([otp_cache_key, attempts_cache_key])
            return {
                "status": "success",
                "message": "OTP verified successfully.",
                "code": "VERIFICATION_SUCCESS",
            }

        return {
            "status": "error",
            "message": "OTP expired or not found.",
            "code": "OTP_EXPIRED",
        }
