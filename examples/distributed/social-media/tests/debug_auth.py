"""Debug script to test auth service validation"""

import asyncio
import httpx
import json

async def test_auth_flow():
    async with httpx.AsyncClient() as client:
        # 1. Register a user
        print("1. Registering user...")
        reg_response = await client.post(
            "http://localhost:3001/api/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "TestPass123!"
            }
        )
        print(f"Registration status: {reg_response.status_code}")
        if reg_response.status_code != 201:
            print(f"Registration error: {reg_response.text}")
            return
        
        reg_data = reg_response.json()
        token = reg_data["token"]
        user_id = reg_data["user"]["id"]
        print(f"Got token: {token[:20]}...")
        print(f"User ID: {user_id}")
        
        # 2. Validate token directly with auth service
        print("\n2. Validating token with auth service...")
        val_response = await client.post(
            "http://localhost:3001/api/validate/token",
            json={"token": token}
        )
        print(f"Validation status: {val_response.status_code}")
        print(f"Validation response: {val_response.json()}")
        
        # 3. Try to create profile
        print("\n3. Creating profile...")
        profile_response = await client.post(
            f"http://localhost:8000/api/users/{user_id}/profile",
            json={
                "display_name": "Test User",
                "bio": "Test bio"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Profile creation status: {profile_response.status_code}")
        if profile_response.status_code != 200:
            print(f"Profile creation error: {profile_response.text}")

if __name__ == "__main__":
    asyncio.run(test_auth_flow())
