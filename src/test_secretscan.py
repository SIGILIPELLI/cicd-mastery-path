from secretscan import scan_text, entropy, redact
AWS = "AKIA" + "IOSFODNN7EXAMPLE"            # AWS's documented example key id, not a real credential
GH = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
def rules(t): return [r for _, _, r, _ in scan_text(t)]
def test_aws_key(): assert rules(f"key = {AWS}") == ["aws-access-key-id"]
def test_github_token(): assert "github-token" in rules(f"export TOKEN={GH}")
def test_private_key_header(): assert rules("-----BEGIN OPENSSH PRIVATE KEY-----") == ["private-key-block"]
def test_generic_assignment(): assert rules('db_password = "correct-horse-battery"') == ["generic-assignment"]
def test_placeholders_ignored():
    for v in ["${{ secrets.DB_PASSWORD }}", "<your-password>", "changeme", "xxxxxxxxxxxx"]:
        assert rules(f'password: "{v}"') == [], v
def test_env_reference_not_flagged(): assert rules('password: "$DB_PASSWORD"') == []
def test_url_credentials(): assert "url-with-credentials" in rules("DATABASE_URL=postgres://app:s3cretpw@db.internal/prod")
def test_allowlist_comment(): assert rules(f'token = "{GH}"  # pragma: allowlist secret') == []
def test_high_entropy(): assert rules("blob = Zm9vYmFyOnN1cGVyLXNlY3JldC1rZXktMTIzNDU2Nzg5MEFCQw0KXzs") == ["high-entropy-string"]
def test_commit_sha_not_flagged(): assert rules("sha = 3a7bd3e2360a3d29eea436fcfb7e44c735d117c4") == []
def test_redaction_never_returns_full_secret():
    (finding,) = scan_text(f"x={GH}"); assert GH not in finding[3] and finding[3].startswith("ghp_")
def test_entropy_ordering(): assert entropy("aaaaaaaaaaaa") < entropy("aB3$kL9#mQ2z")
