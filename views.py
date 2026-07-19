import csv
import io
import json
import os
import re
import uuid
from json import JSONDecodeError
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import ShippingInformation


TRACKING_SHEET_ID = "1oi6ZpuSVEwbYjYg1LbKRXeP0DZvFOpaxa6jxsm2Y7Mo"
SUBMISSIONS_WEBHOOK_URL = os.getenv("SUBMISSIONS_WEBHOOK_URL", "")
SUBMISSIONS_WEBHOOK_SECRET = os.getenv("SUBMISSIONS_WEBHOOK_SECRET", "")

TRACKING_SHEET_SOURCES = getattr(
    settings,
    "TRACKING_SHEET_SOURCES",
    [
        {
            "name": "EU",
            "gid": "503880334",
            "buyer_name_column_index": 13,
            "tracking_number_column_index": 26,
        },
        {
            "name": "US",
            "gid": "1969428090",
            "buyer_name_column_index": 2,
            "tracking_number_column_index": 17,
        },
    ],
)

FIELD_MAP = {
    "fullName": "full_name",
    "accountName": "account_name",
    "phone": "phone",
    "country": "country",
    "countryOther": "country_other",
    "stateProvince": "state_province",
    "city": "city",
    "postalCode": "postal_code",
    "streetAddress": "full_shipping_address",
    "cameraVersion": "camera_version",
    "cameraVersionOther": "camera_version_other",
    "notes": "notes",
}

REQUIRED_FIELDS = {
    "fullName": "Full name is required.",
    "accountName": "Account name is required.",
    "phone": "Phone number is required.",
    "country": "Country or region is required.",
    "city": "City is required.",
    "postalCode": "Postal code is required.",
    "streetAddress": "Full shipping address is required.",
    "cameraVersion": "Camera version is required.",
}


def _clean_text(payload, key):
    value = payload.get(key, "")
    if value is None:
        return ""
    return str(value).strip()


def _normalize_lookup_value(value):
    return " ".join(str(value or "").strip().casefold().split())


def _get_row_value(row, column_index):
    if column_index >= len(row):
        return ""
    return str(row[column_index] or "").strip()


def _split_tracking_numbers(value):
    normalized = str(value or "").replace("\r", "\n").replace(",", "\n").replace(";", "\n")
    return [part.strip() for part in normalized.splitlines() if part.strip()]


def _parse_order_date(order_number):
    match = re.search(r"(?<!\d)(\d{6})(?!\d)", str(order_number or ""))
    if not match:
        return ""

    date_code = match.group(1)
    year = int(date_code[:2])
    month = int(date_code[2:4])
    day = int(date_code[4:6])
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return ""

    return f"20{year:02d}{month:02d}{day:02d}"


def _tracking_sheet_csv_url(gid):
    return f"https://docs.google.com/spreadsheets/d/{TRACKING_SHEET_ID}/gviz/tq?tqx=out:csv&gid={gid}"


def _fetch_tracking_sheet_rows(source):
    request = Request(_tracking_sheet_csv_url(source["gid"]), headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=12) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        content = response.read().decode(charset, errors="replace")

    return list(csv.reader(io.StringIO(content)))


def _lookup_tracking_numbers_by_buyer_name(buyer_name):
    target_name = _normalize_lookup_value(buyer_name)
    found_buyer = False
    latest_match = None

    for source_index, source in enumerate(TRACKING_SHEET_SOURCES):
        buyer_name_column_index = source["buyer_name_column_index"]
        tracking_number_column_index = source["tracking_number_column_index"]

        for row_number, row in enumerate(_fetch_tracking_sheet_rows(source), start=1):
            if row_number == 1:
                continue

            row_buyer_name = _get_row_value(row, buyer_name_column_index)
            if _normalize_lookup_value(row_buyer_name) != target_name:
                continue

            found_buyer = True
            candidate = {
                "source_index": source_index,
                "row_number": row_number,
                "order_date": _parse_order_date(_get_row_value(row, 0)),
                "tracking_numbers": _split_tracking_numbers(_get_row_value(row, tracking_number_column_index)),
            }
            candidate_key = (
                candidate["order_date"],
                candidate["source_index"],
                candidate["row_number"],
            )
            if latest_match is None or candidate_key > latest_match["key"]:
                latest_match = {"key": candidate_key, "candidate": candidate}

    if latest_match is None:
        return found_buyer, []

    return found_buyer, latest_match["candidate"]["tracking_numbers"]


def _build_submission_payload(data):
    submitted_at = timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M:%S")
    return {
        "submittedAt": submitted_at,
        "fullName": data["full_name"],
        "accountName": data["account_name"],
        "phone": data["phone"],
        "country": data["country"],
        "countryOther": data["country_other"],
        "stateProvince": data["state_province"],
        "city": data["city"],
        "postalCode": data["postal_code"],
        "fullShippingAddress": data["full_shipping_address"],
        "cameraVersion": data["camera_version"],
        "cameraVersionOther": data["camera_version_other"],
        "notes": data["notes"],
        "glsConfirm": "TRUE",
        "source": "Website",
        "submissionId": uuid.uuid4().hex,
    }


def _submit_to_google_sheet(submission):
    if not SUBMISSIONS_WEBHOOK_SECRET:
        raise ValueError("SUBMISSIONS_WEBHOOK_SECRET is not configured.")

    payload = json.dumps(
        {
            "secret": SUBMISSIONS_WEBHOOK_SECRET,
            "submission": submission,
        }
    ).encode("utf-8")
    request = Request(
        SUBMISSIONS_WEBHOOK_URL,
        data=payload,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Viltrox Sample Portal",
        },
        method="POST",
    )

    with urlopen(request, timeout=15) as response:
        body = response.read().decode("utf-8", errors="replace")

    result = json.loads(body or "{}")
    if not result.get("ok"):
        raise ValueError(result.get("error") or "Google Sheet webhook rejected the submission.")

    return result


@require_POST
def create_shipping_information(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, JSONDecodeError):
        return JsonResponse(
            {
                "message": "Invalid JSON payload.",
                "errors": {"request": "Please submit valid JSON data."},
            },
            status=400,
        )

    if not isinstance(payload, dict):
        return JsonResponse(
            {
                "message": "Invalid request payload.",
                "errors": {"request": "JSON payload must be an object."},
            },
            status=400,
        )

    errors = {}
    for field, message in REQUIRED_FIELDS.items():
        if not _clean_text(payload, field):
            errors[field] = message

    country = _clean_text(payload, "country")
    camera_version = _clean_text(payload, "cameraVersion")
    camera_choices = set(ShippingInformation.CameraVersion.values)

    if country == "Other" and not _clean_text(payload, "countryOther"):
        errors["countryOther"] = "Please enter the country or region."

    if camera_version and camera_version not in camera_choices:
        errors["cameraVersion"] = "Please select a valid camera version."

    if camera_version == ShippingInformation.CameraVersion.OTHER and not _clean_text(payload, "cameraVersionOther"):
        errors["cameraVersionOther"] = "Please enter the camera version."

    if payload.get("glsConfirm") is not True:
        errors["glsConfirm"] = "Please confirm GLS delivery availability for European addresses."

    if errors:
        return JsonResponse(
            {
                "message": "Please check the highlighted fields.",
                "errors": errors,
            },
            status=400,
        )

    data = {model_field: _clean_text(payload, api_field) for api_field, model_field in FIELD_MAP.items()}
    if data["country"] != "Other":
        data["country_other"] = ""
    if data["camera_version"] != ShippingInformation.CameraVersion.OTHER:
        data["camera_version_other"] = ""

    shipping_information = ShippingInformation(**data, gls_confirm=True)

    try:
        shipping_information.full_clean()
    except ValidationError as exc:
        return JsonResponse(
            {
                "message": "Please check the highlighted fields.",
                "errors": exc.message_dict,
            },
            status=400,
        )

    if SUBMISSIONS_WEBHOOK_URL:
        submission = _build_submission_payload(data)
        try:
            _submit_to_google_sheet(submission)
        except (HTTPError, TimeoutError, URLError, UnicodeDecodeError, JSONDecodeError, ValueError):
            return JsonResponse(
                {
                    "message": "Could not save shipping information right now. Please try again later.",
                    "errors": {"googleSheet": "Google Sheet submission failed."},
                },
                status=502,
            )

        return JsonResponse(
            {
                "id": submission["submissionId"],
                "message": "Shipping information saved.",
                "trackingUrl": "",
            },
            status=201,
        )

    shipping_information.save()

    return JsonResponse(
        {
            "id": shipping_information.id,
            "message": "Shipping information saved.",
            "trackingUrl": shipping_information.tracking_url,
        },
        status=201,
    )


@require_GET
def lookup_tracking_status(request):
    buyer_name = (request.GET.get("fullName") or request.GET.get("buyerName") or request.GET.get("accountName") or "").strip()
    if not buyer_name:
        return JsonResponse(
            {
                "status": "missing_buyer_name",
                "message": "Please enter your full name.",
            },
            status=400,
        )

    try:
        found_buyer, tracking_numbers = _lookup_tracking_numbers_by_buyer_name(buyer_name)
    except (HTTPError, TimeoutError, URLError, UnicodeDecodeError, csv.Error):
        return JsonResponse(
            {
                "status": "sheet_unavailable",
                "message": "Unable to check the tracking sheet right now. Please try again later.",
            },
            status=502,
        )

    if not found_buyer:
        return JsonResponse(
            {
                "status": "not_found",
                "message": "We could not find a shipment for this full name.",
            },
            status=404,
        )

    if not tracking_numbers:
        return JsonResponse(
            {
                "status": "pending",
                "message": "This full name was found, but the tracking number has not been uploaded yet.",
            }
        )

    tracking_number = ", ".join(tracking_numbers)
    return JsonResponse(
        {
            "status": "ready",
            "message": "Tracking number found. You can open 17TRACK to view the latest logistics status.",
            "fullName": buyer_name,
            "trackingNumber": tracking_number,
            "trackingNumbers": tracking_numbers,
            "trackingUrl": f"https://t.17track.net/en#nums={tracking_number}",
        }
    )


@ensure_csrf_cookie
def vue_frontend(request):
    index_path = settings.BASE_DIR / "static" / "frontend" / "index.html"
    try:
        html = index_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return HttpResponse(
            "Vue frontend has not been built yet. Please run: cd frontend && pnpm build",
            status=503,
            content_type="text/plain; charset=utf-8",
        )

    return HttpResponse(html)
