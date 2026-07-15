from django.contrib import admin
from django.utils.html import format_html

from .models import ShippingInformation


admin.site.site_header = "Viltrox 红人样品后台"
admin.site.site_title = "Viltrox 后台"
admin.site.index_title = "信息管理"


@admin.register(ShippingInformation)
class ShippingInformationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "full_name",
        "account_name",
        "phone",
        "country",
        "city",
        "postal_code",
        "shipping_address_display",
        "camera_version_display",
        "tracking_number",
        "created_at",
    )
    list_display_links = ("id", "full_name")
    list_editable = ("tracking_number",)
    list_filter = ("country", "camera_version", "gls_confirm", "created_at")
    search_fields = (
        "full_name",
        "account_name",
        "phone",
        "country",
        "city",
        "postal_code",
        "full_shipping_address",
        "tracking_number",
    )
    readonly_fields = ("tracking_link", "created_at", "updated_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 30
    empty_value_display = "-"

    fieldsets = (
        (
            "红人信息",
            {
                "fields": (
                    "full_name",
                    "account_name",
                    "phone",
                )
            },
        ),
        (
            "收货地址",
            {
                "fields": (
                    "country",
                    "country_other",
                    "state_province",
                    "city",
                    "postal_code",
                    "full_shipping_address",
                    "gls_confirm",
                )
            },
        ),
        (
            "相机与备注",
            {
                "fields": (
                    "camera_version",
                    "camera_version_other",
                    "notes",
                )
            },
        ),
        (
            "物流同步",
            {
                "fields": (
                    "tracking_number",
                    "tracking_link",
                )
            },
        ),
        (
            "系统信息",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    @admin.display(description="相机版本")
    def camera_version_display(self, obj):
        if obj.camera_version == ShippingInformation.CameraVersion.OTHER and obj.camera_version_other:
            return obj.camera_version_other
        return obj.camera_version

    @admin.display(description="收货地址")
    def shipping_address_display(self, obj):
        if len(obj.full_shipping_address) <= 36:
            return obj.full_shipping_address
        return f"{obj.full_shipping_address[:36]}..."

    @admin.display(description="17TRACK 链接")
    def tracking_link(self, obj):
        if not obj.tracking_url:
            return "-"
        return format_html('<a href="{}" target="_blank" rel="noopener">打开 17TRACK</a>', obj.tracking_url)
