"""Replaceable free-prototype geocoding and road-routing provider."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Optional, Tuple
from urllib.parse import quote

import requests


# Override these with environment variables when switching to a hosted provider.
NOMINATIM_URL = os.getenv("GEOCODER_BASE_URL", "https://nominatim.openstreetmap.org")
OSRM_URL = os.getenv("ROUTER_BASE_URL", "https://router.project-osrm.org")
USER_AGENT = os.getenv(
    "ROUTING_USER_AGENT", "kaigo-app/1.0 (+https://github.com/USA1130/kaigo-app)"
)
REQUEST_TIMEOUT_SECONDS = float(os.getenv("ROUTING_TIMEOUT_SECONDS", "15"))


class RoutingError(Exception):
    """A user-displayable lookup or route failure."""


@dataclass(frozen=True)
class RouteEstimate:
    distance_km: float
    standard_minutes: int
    origin_label: str
    destination_label: str


def geocode_address(address: str, *, session: Any = requests) -> Tuple[float, float, str]:
    """Return latitude, longitude and display label using Nominatim."""
    query = address.strip()
    if not query:
        raise RoutingError("住所が空です。出発地・目的地を入力してください。")

    try:
        response = session.get(
            f"{NOMINATIM_URL.rstrip('/')}/search",
            params={"q": query, "format": "jsonv2", "limit": 1, "countrycodes": "jp"},
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        results = response.json()
    except requests.RequestException as exc:
        raise RoutingError(f"住所検索サービスに接続できませんでした: {exc}") from exc
    except (ValueError, TypeError) as exc:
        raise RoutingError("住所検索サービスから正しい応答を受け取れませんでした。") from exc

    if not results:
        raise RoutingError(f"住所が見つかりません:「{query}」。住所を詳しくするか、手入力してください。")
    try:
        item = results[0]
        return float(item["lat"]), float(item["lon"]), item.get("display_name", query)
    except (KeyError, TypeError, ValueError) as exc:
        raise RoutingError("住所検索結果の座標を読み取れませんでした。") from exc


def fetch_route(origin: Tuple[float, float], destination: Tuple[float, float], *, session: Any = requests) -> Tuple[float, int]:
    """Return road distance in km and rounded-up standard driving minutes."""
    # OSRM expects longitude,latitude pairs.
    coordinates = f"{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
    try:
        response = session.get(
            f"{OSRM_URL.rstrip('/')}/route/v1/driving/{quote(coordinates, safe=',;')}",
            params={"overview": "false", "alternatives": "false", "steps": "false"},
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise RoutingError(f"道路ルートサービスに接続できませんでした: {exc}") from exc
    except (ValueError, TypeError) as exc:
        raise RoutingError("道路ルートサービスから正しい応答を受け取れませんでした。") from exc

    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise RoutingError("この2地点間の車ルートが見つかりません。住所を確認するか、距離・時間を手入力してください。")
    try:
        route = payload["routes"][0]
        distance_km = float(route["distance"]) / 1000
        standard_minutes = max(1, int((float(route["duration"]) + 59) // 60))
        if distance_km <= 0:
            raise ValueError("route distance must be positive")
        return distance_km, standard_minutes
    except (KeyError, TypeError, ValueError) as exc:
        raise RoutingError("道路ルートの距離・所要時間を読み取れませんでした。") from exc


def estimate_route(origin_address: str, destination_address: str, *, session: Any = requests,
                   pause: Optional[Any] = time.sleep) -> RouteEstimate:
    """Geocode both addresses and request an OSRM road-route estimate."""
    origin = geocode_address(origin_address, session=session)
    # Public Nominatim requires clients to stay at or below one request/second.
    pause(1.0)
    destination = geocode_address(destination_address, session=session)
    distance_km, standard_minutes = fetch_route(origin[:2], destination[:2], session=session)
    return RouteEstimate(distance_km, standard_minutes, origin[2], destination[2])
