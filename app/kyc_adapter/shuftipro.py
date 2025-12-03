import base64
import hashlib
import json
import logging
import os
from random import randint
from typing import Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)


class ShuftiProAdapter:
    def __init__(
        self,
        client_id: str,
        secret_key: str,
        api_url: str = "https://api.shuftipro.com/",
        callback_url: Optional[str] = None,
    ):
        self.client_id = client_id
        self.secret_key = secret_key
        self.api_url = api_url.rstrip("/") + "/"
        self.callback_url = callback_url or os.getenv("SHUFTIPRO_CALLBACK_URL")

    def _auth_header(self) -> Dict[str, str]:
        token = base64.b64encode(
            f"{self.client_id}:{self.secret_key}".encode()
        ).decode()
        return {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }

    def _build_payload(self, body: Dict[str, Any]) -> Dict[str, Any]:
        reference = f"ref-{body['user_id']}-{randint(1000, 9999)}"

        payload: Dict[str, Any] = {
            "reference": reference,
            "journey_id": body.get("journey_id", ""),
            "email": body["email"],
            "enhanced_originality_checks": "0",
        }

        if self.callback_url:
            payload["callback_url"] = self.callback_url

        return payload

    def _verify_signature(self, response: httpx.Response) -> bool:
        sp_signature = response.headers.get("Signature", "")
        secret_hash = hashlib.sha256(self.secret_key.encode()).hexdigest()
        calc_sig = hashlib.sha256(
            f"{response.text}{secret_hash}".encode()
        ).hexdigest()
        return sp_signature == calc_sig

    async def start_verification(self, body: Dict[str, Any]) -> Dict[str, Any]:
        payload = self._build_payload(body)

        logger.info(f"Calling ShuftiPro API at {self.api_url}")
        logger.debug(f"Payload: {json.dumps(payload, indent=2)}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    self.api_url,
                    headers=self._auth_header(),
                    content=json.dumps(payload),
                )

            logger.info(f"ShuftiPro status: {resp.status_code}")

            try:
                data = resp.json()
            except Exception as e:
                data = {"error": "Invalid JSON response", "raw_text": resp.text}

            if resp.status_code != 200:
                error_msg = (
                    data.get("message")
                    or data.get("error")
                    or "API request failed"
                )
                return {
                    "reference": payload["reference"],
                    "provider": "shuftipro",
                    "verification_url": None,
                    "error": error_msg,
                    "status_code": resp.status_code,
                    "raw": data,
                }

            verification_url = (
                data.get("verification_url")
                or data.get("redirect_url")
                or data.get("url")
                or data.get("verification_link")
            )

            return {
                "reference": payload["reference"],
                "provider": "shuftipro",
                "verification_url": verification_url,
                "raw": data,
            }

        except Exception as e:
            return {
                "reference": payload["reference"],
                "provider": "shuftipro",
                "verification_url": None,
                "error": str(e),
                "raw": {"error": str(e)},
            }
