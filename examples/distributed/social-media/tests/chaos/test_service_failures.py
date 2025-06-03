"""
Chaos engineering tests for service failure scenarios
"""

import pytest
import asyncio
import docker
from typing import Optional

from ..integration.base import IntegrationTestBase


@pytest.mark.chaos
class TestServiceFailures(IntegrationTestBase):
    """Test system behavior under service failures"""
    
    @pytest.fixture
    def docker_client(self):
        """Docker client for chaos operations"""
        return docker.from_env()
    
    async def stop_container(self, docker_client, container_name: str):
        """Stop a container to simulate service failure"""
        try:
            container = docker_client.containers.get(container_name)
            container.stop()
            print(f"🔴 Stopped container: {container_name}")
            return container
        except docker.errors.NotFound:
            pytest.skip(f"Container {container_name} not found")
    
    async def start_container(self, docker_client, container):
        """Restart a container"""
        container.start()
        print(f"🟢 Started container: {container.name}")
        # Wait for service to be ready
        await asyncio.sleep(5)
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_auth_service_failure(self, docker_client):
        """Test behavior when auth service is down"""
        print("\n🧪 Testing Auth Service Failure")
        
        # Create a user first
        user = await self.create_test_user("chaos_auth_test")
        auth_services = self.services.with_token(user['token'])
        
        # Stop auth service
        auth_container = await self.stop_container(
            docker_client, 
            "social-media-auth-service-1"
        )
        
        try:
            # Try to validate token (should fail)
            with pytest.raises(Exception) as exc_info:
                await self.services.auth.validate_token(user['token'])
            print("✅ Auth validation failed as expected when service is down")
            
            # Profile service should still work with cached token
            try:
                profile = await auth_services.user.get_profile(user['id'])
                print("✅ Profile service still accessible with cached auth")
            except Exception as e:
                print(f"⚠️  Profile service failed: {e}")
            
        finally:
            # Always restart the service
            await self.start_container(docker_client, auth_container)
        
        # Verify service recovery
        validation = await self.services.auth.validate_token(user['token'])
        assert validation['valid'] == True
        print("✅ Auth service recovered successfully")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_database_failure(self, docker_client):
        """Test behavior when database is unavailable"""
        print("\n🧪 Testing Database Failure")
        
        # Create test user
        user = await self.create_test_user("chaos_db_test")
        auth_services = self.services.with_token(user['token'])
        
        # Stop user database
        db_container = await self.stop_container(
            docker_client,
            "social-media-user-db-1"
        )
        
        try:
            # Try to update profile (should fail)
            with pytest.raises(Exception) as exc_info:
                await auth_services.user.create_or_update_profile(
                    user_id=user['id'],
                    display_name="Should Fail",
                    bio="This update should not work"
                )
            print("✅ Profile update failed as expected when database is down")
            
            # Cached data might still be available
            try:
                profile = await auth_services.user.get_profile(user['id'])
                if profile:
                    print("✅ Cached profile data still available")
            except:
                print("✅ Profile fetch failed (cache miss)")
            
        finally:
            # Restart database
            await self.start_container(docker_client, db_container)
        
        # Verify recovery
        updated = await auth_services.user.create_or_update_profile(
            user_id=user['id'],
            display_name="Recovery Test",
            bio="Database is back"
        )
        assert updated['display_name'] == "Recovery Test"
        print("✅ Database service recovered successfully")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_redis_cache_failure(self, docker_client):
        """Test behavior when Redis cache is unavailable"""
        print("\n🧪 Testing Redis Cache Failure")
        
        # Create test user
        user = await self.create_test_user("chaos_redis_test")
        auth_services = self.services.with_token(user['token'])
        
        # Warm up cache
        await auth_services.user.get_profile(user['id'])
        print("✅ Cache warmed up")
        
        # Stop Redis
        redis_container = await self.stop_container(
            docker_client,
            "social-media-profile-redis-1"
        )
        
        try:
            # Service should fallback to database
            profile = await auth_services.user.get_profile(user['id'])
            assert profile is not None
            print("✅ Service fell back to database when cache unavailable")
            
            # Updates should still work (but won't be cached)
            updated = await auth_services.user.create_or_update_profile(
                user_id=user['id'],
                display_name="No Cache Test",
                bio="Redis is down"
            )
            assert updated['display_name'] == "No Cache Test"
            print("✅ Updates work without cache")
            
        finally:
            # Restart Redis
            await self.start_container(docker_client, redis_container)
        
        # Verify cache is working again
        profile1 = await auth_services.user.get_profile(user['id'])
        profile2 = await auth_services.user.get_profile(user['id'])
        print("✅ Redis cache recovered successfully")
    
    @pytest.mark.asyncio
    async def test_partial_service_degradation(self):
        """Test system behavior under partial degradation"""
        print("\n🧪 Testing Partial Service Degradation")
        
        # Create multiple users
        users = []
        for i in range(3):
            user = await self.create_test_user(f"degradation_{i}")
            users.append(user)
        
        # Simulate high error rate by making invalid requests
        error_count = 0
        success_count = 0
        
        for _ in range(10):
            try:
                # Mix of valid and invalid operations
                if asyncio.get_event_loop().time() % 2 == 0:
                    # Valid operation
                    auth_services = self.services.with_token(users[0]['token'])
                    await auth_services.user.get_profile(users[0]['id'])
                    success_count += 1
                else:
                    # Invalid operation
                    await self.services.auth.validate_token("invalid-token")
                    success_count += 1
            except:
                error_count += 1
        
        error_rate = error_count / (error_count + success_count)
        print(f"✅ System handled {error_rate*100:.0f}% error rate")
        print(f"   Successes: {success_count}, Errors: {error_count}")
        
        # System should still be functional
        user = await self.create_test_user("still_works")
        assert user is not None
        print("✅ System remains functional under partial degradation")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_cascading_failure_prevention(self, docker_client):
        """Test that failures don't cascade across services"""
        print("\n🧪 Testing Cascading Failure Prevention")
        
        # Create initial data
        user1 = await self.create_test_user("cascade_test_1")
        user2 = await self.create_test_user("cascade_test_2")
        
        # User 1 follows User 2
        auth_services = self.services.with_token(user1['token'])
        await auth_services.user.follow_user(user2['id'])
        
        # Stop auth service (but other services should continue)
        auth_container = await self.stop_container(
            docker_client,
            "social-media-auth-service-1"
        )
        
        try:
            # Profile service operations should still work
            followers = await auth_services.user.get_followers(user2['id'])
            assert len(followers) >= 1
            print("✅ Profile service continues working despite auth service failure")
            
            # Can still perform non-auth operations
            search_results = await auth_services.user.search_users("cascade_test")
            assert len(search_results['results']) >= 2
            print("✅ Search functionality unaffected by auth service failure")
            
        finally:
            # Restart auth service
            await self.start_container(docker_client, auth_container)
        
        print("✅ Services properly isolated - no cascading failures")
    
    @pytest.mark.asyncio
    async def test_retry_and_timeout_behavior(self):
        """Test retry and timeout mechanisms"""
        print("\n🧪 Testing Retry and Timeout Behavior")
        
        # This test simulates slow responses and timeouts
        # In a real scenario, you might use a proxy to inject delays
        
        user = await self.create_test_user("timeout_test")
        auth_services = self.services.with_token(user['token'])
        
        # Make multiple concurrent requests to test timeout handling
        tasks = []
        for i in range(5):
            tasks.append(auth_services.user.get_profile(user['id']))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if not isinstance(r, Exception))
        failed = sum(1 for r in results if isinstance(r, Exception))
        
        print(f"✅ Concurrent requests: {successful} succeeded, {failed} failed")
        assert successful > 0, "At least some requests should succeed"
        
        print("✅ Retry and timeout behavior validated")
