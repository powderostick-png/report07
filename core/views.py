import json
from json import JSONDecodeError

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import ShippingInformation


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
    account_name = request.GET.get("accountName", "").strip()
    if not account_name:
        return JsonResponse(
            {
                "status": "missing_account",
                "message": "Please enter your account name or handle.",
            },
            status=400,
        )

    account_without_at = account_name[1:] if account_name.startswith("@") else account_name
    account_with_at = account_name if account_name.startswith("@") else f"@{account_name}"
    request_record = (
        ShippingInformation.objects.filter(account_name__iexact=account_name).first()
        or ShippingInformation.objects.filter(account_name__iexact=account_with_at).first()
        or ShippingInformation.objects.filter(account_name__iexact=account_without_at).first()
    )

    if not request_record:
        return JsonResponse(
            {
                "status": "not_found",
                "message": "We could not find a sample request for this account name.",
            },
            status=404,
        )

    if not request_record.tracking_number:
        return JsonResponse(
            {
                "status": "pending",
                "message": "Your request is saved. The tracking number has not been uploaded yet.",
                "submittedAt": request_record.created_at.isoformat(),
            }
        )

    return JsonResponse(
        {
            "status": "ready",
            "message": "Tracking number found. You can open 17TRACK to view the latest logistics status.",
            "trackingNumber": request_record.tracking_number,
            "trackingUrl": request_record.tracking_url,
            "submittedAt": request_record.created_at.isoformat(),
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
