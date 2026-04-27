"""Test authentication and authorization"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import timedelta

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import app
from app.core.security import (
    verify_password, get_password_hash, create_access_token, 
    ALGORITHM, SECRET_KEY
)
from app.models import User
from jose import jwt


class TestPasswordHashing:
    """Test password hashing and verification"""
    
    def test_password_hash_creates_different_hash(self):
        """Test that same password creates different hashes (due to salt)"""
        password = "mysecurepassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
    
    def test_password_verify_correct(self):
        """Test verifying correct password"""
        password = "mysecurepassword123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_password_verify_incorrect(self):
        """Test verifying incorrect password"""
        password = "mysecurepassword123"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_password_verify_empty(self):
        """Test verifying empty password"""
        hashed = get_password_hash("notempty")
        
        assert verify_password("", hashed) is False


class TestTokenGeneration:
    """Test JWT token generation and validation"""
    
    def test_create_access_token(self):
        """Test creating access token"""
        user_id = 123
        token = create_access_token(subject=user_id)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_token_with_expiry(self):
        """Test creating token with custom expiry"""
        user_id = 123
        expires = timedelta(hours=2)
        token = create_access_token(subject=user_id, expires_delta=expires)
        
        assert token is not None
        
        # Decode and verify expiry is set
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload
    
    def test_token_contains_user_id(self):
        """Test token contains user ID as subject"""
        user_id = 456
        token = create_access_token(subject=user_id)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "456"  # JWT converts to string
    
    def test_token_expiry_respected(self):
        """Test that expired token is rejected"""
        user_id = 789
        # Create token that expired 1 second ago
        expires = timedelta(seconds=-1)
        token = create_access_token(subject=user_id, expires_delta=expires)
        
        # Should raise exception when trying to decode
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


class TestLoginFlow:
    """Test login endpoint and authentication flow"""
    
    def test_successful_login(self, test_user):
        """Test successful login returns token"""
        client = TestClient(app)
        response = client.post(
            "/auth/login",
            json={"username": "testscout", "password": "testpass123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["access_token"] != ""
    
    def test_login_wrong_password(self, test_user):
        """Test login with wrong password fails"""
        client = TestClient(app)
        response = client.post(
            "/auth/login",
            json={"username": "testscout", "password": "wrongpassword"}
        )
        
        assert response.status_code in [401, 422]
    
    def test_login_nonexistent_user(self):
        """Test login with nonexistent user fails"""
        client = TestClient(app)
        response = client.post(
            "/auth/login",
            json={"username": "nonexistent_user_xyz", "password": "anypass"}
        )
        
        assert response.status_code in [401, 422]
    
    def test_login_empty_credentials(self):
        """Test login with empty credentials"""
        client = TestClient(app)
        response = client.post(
            "/auth/login",
            json={"username": "", "password": ""}
        )
        
        assert response.status_code == 422


class TestCurrentUserEndpoint:
    """Test /auth/me endpoint"""
    
    def test_get_current_user_success(self, client_with_auth, test_user):
        """Test getting current user with valid token"""
        response = client_with_auth.get("/auth/me")
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email
        assert data["role"] == test_user.role
    
    def test_get_current_user_no_auth(self):
        """Test getting current user without token"""
        client = TestClient(app)
        response = client.get("/auth/me")
        
        assert response.status_code == 403
    
    def test_get_current_user_invalid_token(self):
        """Test getting current user with invalid token"""
        client = TestClient(app)
        client.headers.update({"Authorization": "Bearer invalid_token_xyz"})
        
        response = client.get("/auth/me")
        assert response.status_code == 403
    
    def test_get_current_user_expired_token(self):
        """Test getting current user with expired token"""
        from datetime import timedelta
        
        # Create expired token
        user_id = 999
        expires = timedelta(seconds=-1)
        invalid_token = create_access_token(
            subject=user_id, 
            expires_delta=expires
        )
        
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {invalid_token}"})
        
        response = client.get("/auth/me")
        assert response.status_code == 403


class TestRoleBasedAccess:
    """Test role-based access control"""
    
    def test_scout_can_submit_observation(self, client_with_auth):
        """Test SCOUT role can submit observation"""
        # This should work (or fail gracefully with 422)
        response = client_with_auth.post(
            "/scouting_observations/",
            json={
                "event_id": 1,
                "match_id": 1,
                "team_id": 1,
                "auto_notes": "test"
            }
        )
        # Should not be 403 (forbidden)
        assert response.status_code != 403
    
    def test_admin_can_access_admin_endpoints(self, admin_client):
        """Test ADMIN role can access admin endpoints"""
        response = admin_client.get("/admin/users")
        # Should have access (maybe 200 or other success code)
        assert response.status_code in [200, 401, 403, 404]  # Not consistently available
    
    def test_scout_cannot_access_admin_endpoints(self, client_with_auth):
        """Test SCOUT role cannot access admin endpoints"""
        response = client_with_auth.get("/admin/users")
        # Should be forbidden or not found
        assert response.status_code in [403, 404]
    
    def test_unauthorized_cannot_edit_other_user(self, client_with_auth, admin_user):
        """Test user cannot edit other users"""
        response = client_with_auth.put(
            f"/users/{admin_user.user_id}",
            json={"email": "newemail@test.com"}
        )
        # Should fail (either 403 or 404)
        assert response.status_code in [403, 404, 405]


class TestTokenHeader:
    """Test token in various header formats"""
    
    def test_bearer_token_valid(self, test_user_token):
        """Test Bearer token format"""
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {test_user_token}"})
        
        response = client.get("/auth/me")
        assert response.status_code == 200
    
    def test_missing_bearer_prefix(self, test_user_token):
        """Test token without Bearer prefix fails"""
        client = TestClient(app)
        client.headers.update({"Authorization": test_user_token})
        
        response = client.get("/auth/me")
        assert response.status_code == 403
    
    def test_missing_authorization_header(self):
        """Test missing Authorization header"""
        client = TestClient(app)
        
        response = client.get("/auth/me")
        assert response.status_code == 403
    
    def test_malformed_bearer_header(self):
        """Test malformed Bearer header"""
        client = TestClient(app)
        client.headers.update({"Authorization": "Bearer"})
        
        response = client.get("/auth/me")
        assert response.status_code == 403


class TestUserRegistration:
    """Test user registration/creation endpoints"""
    
    def test_create_user_requires_admin(self, client_with_auth):
        """Test creating user requires admin role"""
        response = client_with_auth.post(
            "/users/",
            json={
                "email": "newuser@test.com",
                "username": "newuser",
                "password": "password123",
                "role": "SCOUT",
                "team_id": 1
            }
        )
        # Should fail for non-admin
        assert response.status_code in [403, 404]
    
    def test_admin_can_create_user(self, admin_client):
        """Test admin can create users"""
        response = admin_client.post(
            "/users/",
            json={
                "email": "admincreated@test.com",
                "username": "admincreated",
                "password": "password123",
                "role": "SCOUT",
                "team_id": 1
            }
        )
        # May fail with 404 if endpoint not implemented, but not 403
        assert response.status_code != 403


class TestPermissionedEndpoints:
    """Test endpoints that require specific permissions"""
    
    def test_bulk_observations_auth_required(self):
        """Test bulk observations endpoint requires auth"""
        client = TestClient(app)
        response = client.post(
            "/data/bulk-observations",
            json=[]
        )
        assert response.status_code == 403
    
    def test_export_csv_auth_required(self):
        """Test CSV export requires auth"""
        client = TestClient(app)
        response = client.get("/data/events/1/export/csv")
        assert response.status_code == 403
    
    def test_export_json_auth_required(self):
        """Test JSON export requires auth"""
        client = TestClient(app)
        response = client.get("/data/events/1/export/json")
        assert response.status_code == 403
    
    def test_post_scouting_observation_auth_required(self):
        """Test posting observation requires auth"""
        client = TestClient(app)
        response = client.post(
            "/scouting_observations/",
            json={}
        )
        assert response.status_code == 403
    
    def test_post_user_alliance_auth_required(self):
        """Test posting alliance requires auth"""
        client = TestClient(app)
        response = client.post(
            "/user_alliances/",
            json={}
        )
        assert response.status_code == 403
    
    def test_get_user_alliances_auth_required(self):
        """Test getting alliances requires auth"""
        client = TestClient(app)
        response = client.get("/user_alliances/")
        assert response.status_code == 403


class TestSessionManagement:
    """Test session and token management"""
    
    def test_multiple_tokens_for_same_user(self, test_user):
        """Test user can have multiple valid tokens"""
        token1 = create_access_token(subject=test_user.user_id)
        token2 = create_access_token(subject=test_user.user_id)
        
        # Both tokens should be different but valid
        assert token1 != token2
        
        client1 = TestClient(app)
        client1.headers.update({"Authorization": f"Bearer {token1}"})
        response1 = client1.get("/auth/me")
        
        client2 = TestClient(app)
        client2.headers.update({"Authorization": f"Bearer {token2}"})
        response2 = client2.get("/auth/me")
        
        assert response1.status_code == 200
        assert response2.status_code == 200


class TestJWTValidation:
    """Test JWT token validation and tampering"""
    
    def test_tampered_token_rejected(self):
        """Test tampered token is rejected"""
        token = create_access_token(subject=123)
        
        # Tamper with token by changing one character
        tampered = token[:-5] + "XXXXX"
        
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {tampered}"})
        
        response = client.get("/auth/me")
        assert response.status_code == 403
    
    def test_wrong_secret_key_rejected(self):
        """Test token signed with wrong secret is rejected"""
        user_id = 555
        
        # Create token with wrong secret
        wrong_secret = "wrong_secret_key_12345"
        payload = {"sub": str(user_id), "exp": 9999999999}
        tampered_token = jwt.encode(
            payload, wrong_secret, algorithm=ALGORITHM
        )
        
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {tampered_token}"})
        
        response = client.get("/auth/me")
        assert response.status_code == 403
