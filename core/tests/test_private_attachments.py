import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from core.api.serializers import AttachmentSerializer
from core.models import Attachment
from core.tests.factories import TransactionFactory, UserFactory


@pytest.mark.django_db
def test_receipt_download_is_private(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    tx = TransactionFactory()
    receipt = Attachment.objects.create(
        transaction=tx,
        file=SimpleUploadedFile(
            "receipt.pdf", b"%PDF-1.4 demo", content_type="application/pdf"
        ),
        original_filename="receipt.pdf", content_type="application/pdf", size=13,
    )
    url = reverse("core:attachment_download", args=[receipt.pk])
    assert client.get(url).status_code == 302
    client.force_login(UserFactory())
    assert client.get(url).status_code == 404
    client.force_login(tx.user)
    response = client.get(url)
    assert response.status_code == 200
    assert b"".join(response.streaming_content) == b"%PDF-1.4 demo"
    assert response["Cache-Control"] == "private, no-store"
    assert "attachment;" in response["Content-Disposition"]
    assert AttachmentSerializer(receipt).data["file"] == url
    assert client.get(receipt.file.url).status_code == 404
