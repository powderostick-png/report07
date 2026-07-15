from django.db import models


class ShippingInformation(models.Model):
    class CameraVersion(models.TextChoices):
        SONY = "Sony", "Sony"
        CANON = "Canon", "Canon"
        FUJIFILM = "Fujifilm", "Fujifilm"
        NIKON = "Nikon", "Nikon"
        OTHER = "Other", "Other"

    full_name = models.CharField("姓名", max_length=120)
    account_name = models.CharField("账号名称", max_length=120, db_index=True)
    phone = models.CharField("电话", max_length=60)
    country = models.CharField("国家/地区", max_length=100)
    country_other = models.CharField("其他国家/地区", max_length=120, blank=True)
    state_province = models.CharField("州/省", max_length=120, blank=True)
    city = models.CharField("城市", max_length=120)
    postal_code = models.CharField("邮编", max_length=40)
    full_shipping_address = models.TextField("完整收货地址")
    camera_version = models.CharField(
        "相机版本",
        max_length=40,
        choices=CameraVersion.choices,
    )
    camera_version_other = models.CharField("其他相机版本", max_length=120, blank=True)
    notes = models.TextField("备注", blank=True)
    gls_confirm = models.BooleanField("已确认 GLS 可派送", default=False)
    tracking_number = models.CharField("物流单号", max_length=120, blank=True, db_index=True)
    created_at = models.DateTimeField("提交时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "红人样品申请"
        verbose_name_plural = "红人样品申请"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} / {self.account_name}"

    @property
    def tracking_url(self):
        if not self.tracking_number:
            return ""
        return f"https://t.17track.net/en#nums={self.tracking_number}"
