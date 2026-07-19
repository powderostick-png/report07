import csv
import io
import json
from json import JSONDecodeError
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import ShippingInformation


TRACKING_SHEET_ID = "1oi6ZpuSVEwbYjYg1LbKRXeP0DZvFOpaxa6jxsm2Y7Mo"
TRACKING_SHEET_SOURCES = getattr(
    settings,
    "TRACKING_SHEET_SOURCES",
    [
        {
            "name": "EU发货",
            "gid": "503880334",
            "buyer_name_column_index": 13,
            "tracking_number_column_index": 26,
        },
        {
            "name": "US发货",
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
    tracking_numbers = []

    for source in TRACKING_SHEET_SOURCES:
        buyer_name_column_index = source["buyer_name_column_index"]
        tracking_number_column_index = source["tracking_number_column_index"]

        for row_number, row in enumerate(_fetch_tracking_sheet_rows(source), start=1):
            if row_number == 1:
                continue

            row_buyer_name = _get_row_value(row, buyer_name_column_index)
            if _normalize_lookup_value(row_buyer_name) != target_name:
                continue

            found_buyer = True
            for tracking_number in _split_tracking_numbers(_get_row_value(row, tracking_number_column_index)):
                if tracking_number not in tracking_numbers:
                    tracking_numbers.append(tracking_number)

    return found_buyer, tracking_numbers


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
    buyer_name = (request.GET.get("buyerName") or request.GET.get("accountName") or "").strip()
    if not buyer_name:
        return JsonResponse(
            {
                "status": "missing_buyer_name",
                "message": "Please enter your buyer name.",
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
                "message": "We could not find a shipment for this buyer name.",
            },
            status=404,
        )

    if not tracking_numbers:
        return JsonResponse(
            {
                "status": "pending",
                "message": "This buyer name was found, but the tracking number has not been uploaded yet.",
            }
        )

    tracking_number = ", ".join(tracking_numbers)
    return JsonResponse(
        {
            "status": "ready",
            "message": "Tracking number found. You can open 17TRACK to view the latest logistics status.",
            "buyerName": buyer_name,
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
