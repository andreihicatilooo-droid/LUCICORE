"""Merchant API SDK - Exceptions"""


class MerchantApiError(Exception):
    def __init__(self, message, status_code=None, response=None):
        self.message = message
        self.status_code = status_code
        self.response = response or {}
        super().__init__(self.message)


class AuthenticationError(MerchantApiError):
    pass


class RateLimitError(MerchantApiError):
    def __init__(self, message, retry_after=None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ValidationError(MerchantApiError):
    def __init__(self, message, errors=None, **kwargs):
        super().__init__(message, **kwargs)
        self.errors = errors or {}


class NotFoundError(MerchantApiError):
    pass


class ServerError(MerchantApiError):
    pass


class TorConnectionError(MerchantApiError):
    pass
