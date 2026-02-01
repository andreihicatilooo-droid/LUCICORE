"""Merchant API SDK - Webhook Handler"""

import hmac
import hashlib
import json


class WebhookHandler:
    """Handler for webhook signature verification (HMAC-SHA256)."""

    def __init__(self, api_secret):
        self.api_secret = api_secret

    def generate_signature(self, payload):
        return hmac.new(self.api_secret.encode(), payload, hashlib.sha256).hexdigest()

    def verify_signature(self, payload, signature):
        if not signature: return False
        return hmac.compare_digest(self.generate_signature(payload), signature)

    def parse_payload(self, payload):
        return json.loads(payload.decode() if isinstance(payload, bytes) else payload)

    def process_webhook(self, payload, signature):
        if self.verify_signature(payload, signature):
            return self.parse_payload(payload)
        return None
