import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from time import time

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

import auth
import config


def test_oidc_jwks_validation_maps_tenant_user_and_departments(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk.update({"kid": "test-key", "use": "sig", "alg": "RS256"})

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            body = json.dumps({"keys": [public_jwk]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setattr(config, "OIDC_JWKS_URL", f"http://127.0.0.1:{server.server_port}/jwks")
        monkeypatch.setattr(config, "OIDC_ISSUER", "https://issuer.example/")
        monkeypatch.setattr(config, "OIDC_AUDIENCE", "assistant")
        monkeypatch.setattr(config, "OIDC_TENANT_CLAIM", "tenant_id")
        monkeypatch.setattr(config, "OIDC_ROLES_CLAIM", "roles")
        monkeypatch.setattr(config, "OIDC_DEPARTMENTS_CLAIM", "departments")
        token = jwt.encode(
            {
                "sub": "employee-1", "tenant_id": "company-a", "roles": ["employee"],
                "departments": ["sales"], "iss": "https://issuer.example/",
                "aud": "assistant", "exp": int(time()) + 60,
            },
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key"},
        )
        principal = auth.authenticate(token)
        assert principal.tenant_id == "company-a"
        assert principal.user_id == "employee-1"
        assert principal.departments == ("sales",)
    finally:
        server.shutdown()
        thread.join(timeout=2)
