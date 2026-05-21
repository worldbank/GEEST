# -*- coding: utf-8 -*-
"""Client for querying the public Space2Stats API."""

import json
import random
import time
from typing import Any, Dict, List, Optional

from qgis.core import QgsNetworkAccessManager
from qgis.PyQt.QtCore import QObject, QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest


class S2SClient(QObject):
    """Client wrapper for Space2Stats endpoints used by GeoE3.

    This client provides thin request/response helpers for the public API.
    It intentionally keeps scope small for phase 1 integration.
    """

    VALID_JOIN_METHODS = {"touches", "centroid", "within"}
    VALID_GEOMETRIES = {"point", "polygon"}
    RETRYABLE_STATUS_CODES = {502, 503, 504}

    def __init__(
        self,
        base_url: Optional[str] = None,
        max_attempts: int = 4,
        backoff_base_seconds: float = 0.5,
        backoff_jitter_seconds: float = 0.2,
    ):
        """Initialize the S2S client.

        Args:
            base_url: API base URL. Defaults to public Space2Stats host.
            max_attempts: Maximum number of attempts for transient failures.
            backoff_base_seconds: Base exponential backoff delay.
            backoff_jitter_seconds: Random jitter added to each backoff delay.
        """
        super().__init__()
        self.base_url = (base_url or "https://space2stats.ds.io").rstrip("/")
        self.network_manager = QgsNetworkAccessManager.instance()
        self.max_attempts = max(1, int(max_attempts))
        self.backoff_base_seconds = max(0.0, float(backoff_base_seconds))
        self.backoff_jitter_seconds = max(0.0, float(backoff_jitter_seconds))

    def health(self) -> Dict[str, Any]:
        """Check API health endpoint.

        Returns:
            Parsed JSON object from the health endpoint.
        """
        result = self._request("GET", "/health")
        if not isinstance(result, dict):
            raise RuntimeError("Unexpected /health response format.")
        return result

    def fields(self) -> List[str]:
        """Fetch available summary fields from S2S.

        Returns:
            List of field names.
        """
        result = self._request("GET", "/fields")
        if isinstance(result, list):
            return [str(value) for value in result]

        if isinstance(result, dict):
            for key in ("fields", "data"):
                value = result.get(key)
                if isinstance(value, list):
                    return [str(item) for item in value]
            keys = ", ".join(sorted(result.keys())[:8])
            raise RuntimeError(f"Unexpected /fields response format: object keys [{keys}]")

        raise RuntimeError(f"Unexpected /fields response format: {type(result).__name__}")

    def summary(
        self,
        aoi: Dict[str, Any],
        fields: List[str],
        spatial_join_method: str = "centroid",
        geometry: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query per-hex summary records for an AOI.

        Args:
            aoi: GeoJSON feature (Polygon/MultiPolygon).
            fields: S2S field names to fetch.
            spatial_join_method: One of touches/centroid/within.
            geometry: Optional geometry type (point or polygon).

        Returns:
            List of summary rows, typically including ``hex_id`` and selected fields.
        """
        if not isinstance(aoi, dict) or not aoi:
            raise ValueError("'aoi' must be a non-empty GeoJSON feature dictionary.")

        if not isinstance(fields, list) or not fields:
            raise ValueError("'fields' must be a non-empty list of field names.")

        if spatial_join_method not in self.VALID_JOIN_METHODS:
            raise ValueError(
                f"Invalid spatial_join_method '{spatial_join_method}'. "
                f"Use one of: {sorted(self.VALID_JOIN_METHODS)}"
            )

        if geometry is not None and geometry not in self.VALID_GEOMETRIES:
            raise ValueError(f"Invalid geometry '{geometry}'. Use one of: {sorted(self.VALID_GEOMETRIES)}")

        payload: Dict[str, Any] = {
            "aoi": aoi,
            "spatial_join_method": spatial_join_method,
            "fields": fields,
        }
        if geometry is not None:
            payload["geometry"] = geometry

        result = self._request("POST", "/summary", payload)
        if not isinstance(result, list):
            raise RuntimeError("Unexpected /summary response format.")
        return result

    def summary_by_hexids(
        self,
        hex_ids: List[str],
        fields: List[str],
        geometry: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query per-hex summary records for explicit H3 hex IDs.

        Args:
            hex_ids: List of H3 hex IDs.
            fields: S2S field names to fetch.
            geometry: Optional geometry type (point or polygon).

        Returns:
            List of summary rows, typically including ``hex_id`` and selected fields.
        """
        if not isinstance(hex_ids, list) or not hex_ids:
            raise ValueError("'hex_ids' must be a non-empty list of H3 IDs.")

        normalized_hex_ids = [str(value).strip() for value in hex_ids if str(value).strip()]
        if not normalized_hex_ids:
            raise ValueError("'hex_ids' must contain at least one non-empty H3 ID.")

        if not isinstance(fields, list) or not fields:
            raise ValueError("'fields' must be a non-empty list of field names.")

        if geometry is not None and geometry not in self.VALID_GEOMETRIES:
            raise ValueError(f"Invalid geometry '{geometry}'. Use one of: {sorted(self.VALID_GEOMETRIES)}")

        payload: Dict[str, Any] = {
            "hex_ids": normalized_hex_ids,
            "fields": fields,
        }
        if geometry is not None:
            payload["geometry"] = geometry

        result = self._request("POST", "/summary_by_hexids", payload)
        if not isinstance(result, list):
            raise RuntimeError("Unexpected /summary_by_hexids response format.")
        return result

    def _request(self, method: str, endpoint: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a blocking JSON request to S2S.

        Args:
            method: HTTP method (GET or POST).
            endpoint: API endpoint path.
            payload: Optional JSON payload for POST requests.

        Returns:
            Parsed JSON response payload.
        """
        if method not in {"GET", "POST"}:
            raise ValueError(f"Unsupported method: {method}")

        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_attempts + 1):
            url = QUrl(f"{self.base_url}{endpoint}")
            request = QNetworkRequest(url)
            request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")

            try:
                if method == "GET":
                    reply = self.network_manager.blockingGet(request)
                else:
                    data = json.dumps(payload or {}).encode("utf-8")
                    reply = self.network_manager.blockingPost(request, data)

                status_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
                response_text = self._extract_text(reply.content())

                if status_code is None:
                    raise RuntimeError("No HTTP status code received from S2S API.")

                if status_code == 422:
                    raise ValueError(f"S2S request validation failed (422): {response_text}")
                if status_code == 429:
                    raise RuntimeError("S2S API rate limit exceeded (429). Please retry later.")
                if status_code >= 500:
                    if status_code in self.RETRYABLE_STATUS_CODES and attempt < self.max_attempts:
                        self._sleep_before_retry(attempt)
                        continue

                    if status_code in self.RETRYABLE_STATUS_CODES:
                        raise RuntimeError(
                            f"S2S service temporarily unavailable ({status_code}) after {attempt} attempts."
                        )

                    raise RuntimeError(f"S2S server error ({status_code}).")
                if status_code >= 400:
                    raise RuntimeError(f"S2S request failed ({status_code}): {response_text}")

                try:
                    return self._parse_json_response(response_text)
                except json.JSONDecodeError as error:
                    raise RuntimeError(f"Failed to parse S2S JSON response: {error}") from error

            except Exception as error:
                if not self._is_retryable_error(error):
                    raise

                last_error = error
                if attempt >= self.max_attempts:
                    raise RuntimeError(
                        f"S2S service temporarily unavailable after {attempt} attempts: {error}"
                    ) from error

                self._sleep_before_retry(attempt)

        raise RuntimeError(f"S2S request failed after retries: {last_error}")

    def _sleep_before_retry(self, attempt: int) -> None:
        """Sleep with exponential backoff before retrying."""
        delay = self.backoff_base_seconds * (2 ** max(0, attempt - 1))
        if self.backoff_jitter_seconds > 0:
            delay += random.uniform(0.0, self.backoff_jitter_seconds)
        if delay > 0:
            time.sleep(delay)

    @staticmethod
    def _is_retryable_error(error: Exception) -> bool:
        """Return True when an error is considered transient and retryable."""
        message = str(error).lower()
        return (
            "no http status code received" in message
            or "service temporarily unavailable" in message
            or "connection" in message
            or "timed out" in message
            or "timeout" in message
            or "failed to parse s2s json response" in message
            or "extra data" in message
        )

    @staticmethod
    def _parse_json_response(response_text: str) -> Any:
        """Parse JSON responses, tolerating trailing junk after valid JSON.

        Some upstream responses intermittently append extra bytes after valid JSON.
        We parse the first valid JSON document to keep requests resilient.
        """
        normalized = response_text.lstrip("\ufeff\x00 \t\r\n")
        if not normalized:
            raise json.JSONDecodeError("Expecting value", response_text, 0)

        try:
            return json.loads(normalized)
        except json.JSONDecodeError:
            decoder = json.JSONDecoder()
            value, end = decoder.raw_decode(normalized)
            remainder = normalized[end:].lstrip("\x00 \t\r\n")
            if not remainder:
                return value

            if remainder[0] in '{["-0123456789tfn':
                raise json.JSONDecodeError("Extra data", normalized, end)

            return value

    @staticmethod
    def _extract_text(content: Any) -> str:
        """Convert network reply content to UTF-8 text."""
        if isinstance(content, (bytes, bytearray)):
            return bytes(content).decode("utf-8")

        if hasattr(content, "data"):
            return bytes(content).decode("utf-8")

        return str(content)
