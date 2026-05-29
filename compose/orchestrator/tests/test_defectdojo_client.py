from unittest.mock import patch, MagicMock
from app.defectdojo_client import import_scan


@patch("app.defectdojo_client.requests.post")
def test_import_scan_posts_multipart(mock_post):
    mock_post.return_value = MagicMock(status_code=201, json=lambda: {"test": 5})
    rc = import_scan("http://dd:8080", "tok", "Trivy Scan", "nginx", '{"Results":[]}')
    assert rc == 5
    kwargs = mock_post.call_args.kwargs
    assert kwargs["data"]["scan_type"] == "Trivy Scan"
    assert kwargs["data"]["product_type_name"] == "TIZIM"
    assert kwargs["data"]["close_old_findings"] == "true"
    assert "Authorization" in kwargs["headers"]
