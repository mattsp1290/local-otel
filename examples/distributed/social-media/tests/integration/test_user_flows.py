"""
Integration tests for user flows across services
"""

import pytest
import asyncio
from typing import Dict, Any

from .base import IntegrationTestBase


@pytest.mark.integration
class TestUserFlows(IntegrationTestBase):
    """Test complete user journeys through the system"""
    
    @pytest.mark.asyncio
    async def test_user_onboarding_flow(self):
        """Test complete user onboarding: register → create profile → view profile"""
        print("\n🧪 Testing User Onboarding Flow")
        
        # Create a new user (includes registration and profile creation)
        user = await self.create_test_user("onboarding")
        
        print(f"✅ Created user: {user['username']} (ID: {user['id']})")
        self.log_trace_url(user['trace_id'])
        
        # Validate the trace
        trace_result = await self.wait_for_trace_and_validate(
            trace_id=user['trace_id'],
            expected_services=["auth-service", "user-profile-service"],
            expected_operations=[
                "POST /register",
                "POST /{user_id}/profile"
            ]
        )
        
        # Assert trace is valid
        self.assert_trace_valid(trace_result['validation'])
        
        # Check latencies
        self.assert_latency_within_limits(
            trace_result['latencies'],
            "auth-service",
            max_avg_latency_ms=500
        )
        self.assert_latency_within_limits(
            trace_result['latencies'],
            "user-profile-service",
            max_avg_latency_ms=300
        )
        
        # Verify profile can be retrieved
        auth_services = self.services.with_token(user['token'])
        profile = await auth_services.user.get_profile(user['id'])
        
        assert profile['user_id'] == user['id']
        assert profile['display_name'] == user['profile']['display_name']
        assert profile['bio'] == user['profile']['bio']
        
        print("✅ User onboarding flow completed successfully")
    
    @pytest.mark.asyncio
    async def test_social_interaction_flow(self):
        """Test social interactions: User A follows User B, B sees A as follower"""
        print("\n🧪 Testing Social Interaction Flow")
        
        # Create two users
        user_a = await self.create_test_user("user_a")
        user_b = await self.create_test_user("user_b")
        
        print(f"✅ Created User A: {user_a['username']}")
        print(f"✅ Created User B: {user_b['username']}")
        
        # User A follows User B
        follow_result = await self.create_user_relationship(
            follower_token=user_a['token'],
            following_id=user_b['id']
        )
        
        print(f"✅ User A followed User B")
        self.log_trace_url(follow_result['trace_id'])
        
        # Validate follow trace
        trace_result = await self.wait_for_trace_and_validate(
            trace_id=follow_result['trace_id'],
            expected_services=["user-profile-service"],
            expected_operations=["POST /{user_id}/follow"]
        )
        
        self.assert_trace_valid(trace_result['validation'])
        
        # Verify User B has User A as a follower
        auth_services_b = self.services.with_token(user_b['token'])
        followers = await auth_services_b.user.get_followers(user_b['id'])
        
        follower_ids = [f['user_id'] for f in followers]
        assert user_a['id'] in follower_ids, "User A should be in User B's followers"
        
        # Verify User A is following User B
        auth_services_a = self.services.with_token(user_a['token'])
        following = await auth_services_a.user.get_following(user_a['id'])
        
        following_ids = [f['user_id'] for f in following]
        assert user_b['id'] in following_ids, "User B should be in User A's following list"
        
        # Test unfollow
        unfollow_result = await auth_services_a.user.unfollow_user(user_b['id'])
        
        # Verify unfollow worked
        followers_after = await auth_services_b.user.get_followers(user_b['id'])
        follower_ids_after = [f['user_id'] for f in followers_after]
        assert user_a['id'] not in follower_ids_after, "User A should not be in User B's followers after unfollow"
        
        print("✅ Social interaction flow completed successfully")
    
    @pytest.mark.asyncio
    async def test_profile_search_flow(self):
        """Test user search functionality"""
        print("\n🧪 Testing Profile Search Flow")
        
        # Create users with specific names for searching
        users = []
        for i in range(3):
            user = await self.create_test_user(f"searchable_{i}")
            # Update profile with searchable display name
            auth_services = self.services.with_token(user['token'])
            await auth_services.user.create_or_update_profile(
                user_id=user['id'],
                display_name=f"TestSearchUser{i}",
                bio=f"Bio for search test user {i}"
            )
            users.append(user)
        
        print(f"✅ Created {len(users)} searchable users")
        
        # Search for users
        search_query = "TestSearchUser"
        auth_services = self.services.with_token(users[0]['token'])
        search_results = await auth_services.user.search_users(search_query)
        
        # Verify search results
        assert search_results['query'] == search_query
        assert len(search_results['results']) >= 3, "Should find at least 3 users"
        
        # Verify all created users are in results
        result_ids = {r['user_id'] for r in search_results['results']}
        for user in users:
            assert user['id'] in result_ids, f"User {user['id']} should be in search results"
        
        print(f"✅ Search returned {len(search_results['results'])} results")
        print("✅ Profile search flow completed successfully")
    
    @pytest.mark.asyncio
    async def test_concurrent_user_operations(self):
        """Test multiple users performing operations concurrently"""
        print("\n🧪 Testing Concurrent User Operations")
        
        # Create base users
        num_users = 5
        users = []
        
        print(f"Creating {num_users} users...")
        create_tasks = [self.create_test_user(f"concurrent_{i}") for i in range(num_users)]
        users = await asyncio.gather(*create_tasks)
        
        print(f"✅ Created {len(users)} users concurrently")
        
        # Have each user follow all others concurrently
        follow_tasks = []
        for i, follower in enumerate(users):
            for j, following in enumerate(users):
                if i != j:  # Don't follow self
                    task = self.create_user_relationship(
                        follower_token=follower['token'],
                        following_id=following['id']
                    )
                    follow_tasks.append(task)
        
        print(f"Creating {len(follow_tasks)} follow relationships...")
        follow_results = await asyncio.gather(*follow_tasks, return_exceptions=True)
        
        # Count successful follows
        successful_follows = sum(1 for r in follow_results if not isinstance(r, Exception))
        print(f"✅ Created {successful_follows} follow relationships")
        
        # Verify each user has correct follower/following counts
        for user in users:
            auth_services = self.services.with_token(user['token'])
            profile = await auth_services.user.get_profile(user['id'])
            
            # Each user should have (num_users - 1) followers and following
            expected_count = num_users - 1
            assert profile['follower_count'] == expected_count, \
                f"User {user['id']} should have {expected_count} followers"
            assert profile['following_count'] == expected_count, \
                f"User {user['id']} should be following {expected_count} users"
        
        print("✅ Concurrent user operations completed successfully")
    
    @pytest.mark.asyncio
    async def test_authentication_flow_across_services(self):
        """Test authentication token validation across services"""
        print("\n🧪 Testing Authentication Flow Across Services")
        
        # Create user
        user = await self.create_test_user("auth_test")
        print(f"✅ Created user: {user['username']}")
        
        # Test token validation
        validation_result = await self.services.auth.validate_token(user['token'])
        assert validation_result['valid'] == True
        assert validation_result['user']['id'] == user['id']
        
        # Test accessing profile service with token
        auth_services = self.services.with_token(user['token'])
        profile = await auth_services.user.get_profile(user['id'])
        assert profile is not None
        
        # Test token refresh
        refresh_result = await self.services.auth.refresh_token(user['token'])
        new_token = refresh_result['token']
        assert new_token != user['token'], "Should receive new token"
        
        # Verify new token works
        new_auth_services = self.services.with_token(new_token)
        profile_with_new_token = await new_auth_services.user.get_profile(user['id'])
        assert profile_with_new_token is not None
        
        # Test logout
        await self.services.auth.logout(new_token)
        
        # Verify token is invalidated (this should fail)
        try:
            await self.services.auth.validate_token(new_token)
            pytest.fail("Token should be invalid after logout")
        except Exception as e:
            # Expected to fail
            pass
        
        print("✅ Authentication flow across services completed successfully")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_profile_caching_behavior(self):
        """Test that profile caching works correctly"""
        print("\n🧪 Testing Profile Caching Behavior")
        
        # Create user
        user = await self.create_test_user("cache_test")
        auth_services = self.services.with_token(user['token'])
        
        # First profile fetch (cache miss)
        profile1 = await auth_services.user.get_profile(user['id'])
        
        # Second fetch should hit cache
        profile2 = await auth_services.user.get_profile(user['id'])
        
        # Profiles should be identical
        assert profile1 == profile2
        
        # Update profile (should invalidate cache)
        updated_profile = await auth_services.user.create_or_update_profile(
            user_id=user['id'],
            display_name="Updated Name",
            bio="Updated bio"
        )
        
        # Fetch again - should get updated data
        profile3 = await auth_services.user.get_profile(user['id'])
        assert profile3['display_name'] == "Updated Name"
        assert profile3['bio'] == "Updated bio"
        
        print("✅ Profile caching behavior verified successfully")
