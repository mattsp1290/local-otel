#!/usr/bin/env python3
"""
Load generator for social media platform
Simulates realistic user behavior with:
- User registration/login
- Profile creation/updates
- Following other users
- Creating posts
- Viewing timelines
"""

import asyncio
import httpx
import random
import json
import time
from datetime import datetime
from typing import List, Dict, Optional

class SocialMediaLoadGenerator:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.users: List[Dict] = []
        self.posts: List[str] = []
        self.stats = {
            "requests": 0,
            "errors": 0,
            "start_time": time.time(),
            "response_times": []
        }
        
    async def register_user(self, username: str) -> Optional[Dict]:
        """Register a new user and get their token"""
        try:
            async with httpx.AsyncClient() as client:
                start = time.time()
                response = await client.post(
                    f"{self.base_url}/api/auth/register",
                    json={"username": username, "password": "testpass123"}
                )
                self.stats["response_times"].append(time.time() - start)
                self.stats["requests"] += 1
                
                if response.status_code == 201:
                    data = response.json()
                    return {
                        "username": username,
                        "user_id": data.get("user_id"),
                        "token": data.get("token"),
                        "interactions": {}
                    }
                else:
                    self.stats["errors"] += 1
                    print(f"Failed to register {username}: {response.status_code}")
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Error registering {username}: {e}")
        return None
        
    async def create_post(self, user: Dict, content: str) -> Optional[str]:
        """Create a post for a user"""
        try:
            async with httpx.AsyncClient() as client:
                start = time.time()
                response = await client.post(
                    f"{self.base_url}/api/posts",
                    json={"content": content},
                    headers={"X-User-ID": user["user_id"]}
                )
                self.stats["response_times"].append(time.time() - start)
                self.stats["requests"] += 1
                
                if response.status_code == 201:
                    post = response.json()
                    return post.get("id")
                else:
                    self.stats["errors"] += 1
                    print(f"Failed to create post for {user['username']}: {response.status_code}")
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Error creating post: {e}")
        return None
        
    async def view_timeline(self, user: Dict) -> List[Dict]:
        """View a user's timeline"""
        try:
            async with httpx.AsyncClient() as client:
                start = time.time()
                response = await client.get(
                    f"{self.base_url}/api/timeline/{user['user_id']}",
                    headers={"X-User-ID": user["user_id"]}
                )
                self.stats["response_times"].append(time.time() - start)
                self.stats["requests"] += 1
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("posts", [])
                else:
                    self.stats["errors"] += 1
                    print(f"Failed to get timeline for {user['username']}: {response.status_code}")
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Error viewing timeline: {e}")
        return []
        
    async def follow_user(self, follower: Dict, target_username: str) -> bool:
        """Follow another user"""
        try:
            async with httpx.AsyncClient() as client:
                start = time.time()
                response = await client.post(
                    f"{self.base_url}/api/users/{target_username}/follow",
                    headers={"X-User-ID": follower["user_id"]}
                )
                self.stats["response_times"].append(time.time() - start)
                self.stats["requests"] += 1
                
                if response.status_code == 200:
                    # Track interactions
                    if target_username not in follower["interactions"]:
                        follower["interactions"][target_username] = 0
                    follower["interactions"][target_username] += 1
                    return True
                else:
                    self.stats["errors"] += 1
                    print(f"Failed to follow {target_username}: {response.status_code}")
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Error following user: {e}")
        return False
        
    async def like_post(self, user: Dict, post_id: str) -> bool:
        """Like a post"""
        try:
            async with httpx.AsyncClient() as client:
                start = time.time()
                response = await client.post(
                    f"{self.base_url}/api/posts/{post_id}/like",
                    headers={"X-User-ID": user["user_id"]}
                )
                self.stats["response_times"].append(time.time() - start)
                self.stats["requests"] += 1
                
                if response.status_code == 200:
                    return True
                else:
                    self.stats["errors"] += 1
                    print(f"Failed to like post {post_id}: {response.status_code}")
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Error liking post: {e}")
        return False
        
    async def comment_on_post(self, user: Dict, post_id: str, comment: str) -> bool:
        """Comment on a post"""
        try:
            async with httpx.AsyncClient() as client:
                start = time.time()
                response = await client.post(
                    f"{self.base_url}/api/posts/{post_id}/comment",
                    json={"content": comment},
                    headers={"X-User-ID": user["user_id"]}
                )
                self.stats["response_times"].append(time.time() - start)
                self.stats["requests"] += 1
                
                if response.status_code == 201:
                    return True
                else:
                    self.stats["errors"] += 1
                    print(f"Failed to comment on post {post_id}: {response.status_code}")
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Error commenting on post: {e}")
        return False
        
    def generate_post_content(self) -> str:
        """Generate realistic post content"""
        templates = [
            "Just finished {activity}! Feeling {emotion} 🎉",
            "Anyone else love {topic}? Let's discuss!",
            "Beautiful day for {activity}. What are you up to?",
            "Thoughts on {topic}? I'm curious what you think.",
            "Pro tip: {advice}. You're welcome! 😊",
            "Can't believe it's already {time}. Time flies!",
            "{emotion} about {topic} right now. Anyone else?",
            "Working on {project}. Progress is progress! 💪",
        ]
        
        activities = ["coding", "reading", "exercising", "cooking", "traveling", "learning"]
        emotions = ["excited", "happy", "grateful", "motivated", "inspired", "curious"]
        topics = ["AI", "music", "technology", "nature", "books", "movies", "food"]
        advice = [
            "take breaks while coding",
            "stay hydrated",
            "practice gratitude daily",
            "learn something new every day",
            "embrace failure as learning"
        ]
        projects = ["a new app", "my side project", "learning Go", "improving my skills"]
        times = ["Friday", "the weekend", "December", "2025"]
        
        template = random.choice(templates)
        return template.format(
            activity=random.choice(activities),
            emotion=random.choice(emotions),
            topic=random.choice(topics),
            advice=random.choice(advice),
            project=random.choice(projects),
            time=random.choice(times)
        )
        
    def generate_comment(self) -> str:
        """Generate realistic comment content"""
        comments = [
            "Great point! I totally agree.",
            "Interesting perspective, thanks for sharing!",
            "This is so relatable 😂",
            "Love this! Keep it up!",
            "Couldn't agree more!",
            "Thanks for sharing this!",
            "This made my day!",
            "So true! 💯",
            "I needed to hear this today.",
            "Awesome! Looking forward to more."
        ]
        return random.choice(comments)
        
    async def simulate_user_session(self, user: Dict, duration_seconds: int):
        """Simulate realistic user behavior for a session"""
        start_time = time.time()
        
        while time.time() - start_time < duration_seconds:
            # Randomly choose an action with realistic probabilities
            action = random.choices(
                ["view_timeline", "create_post", "interact", "browse"],
                weights=[40, 10, 30, 20],
                k=1
            )[0]
            
            if action == "view_timeline":
                # View timeline
                posts = await self.view_timeline(user)
                
                # Sometimes interact with posts from timeline
                if posts and random.random() < 0.3:
                    post = random.choice(posts[:5])  # Interact with recent posts
                    if random.random() < 0.7:
                        await self.like_post(user, post.get("id"))
                    if random.random() < 0.3:
                        await self.comment_on_post(user, post.get("id"), self.generate_comment())
                        
            elif action == "create_post" and random.random() < 0.3:
                # Create a post (but not too frequently)
                content = self.generate_post_content()
                post_id = await self.create_post(user, content)
                if post_id:
                    self.posts.append(post_id)
                    
            elif action == "interact" and len(self.users) > 1:
                # Follow someone new
                if random.random() < 0.2 and len(self.users) > 1:
                    other_users = [u for u in self.users if u["username"] != user["username"]]
                    if other_users:
                        target = random.choice(other_users)
                        await self.follow_user(user, target["username"])
                        
                # Like or comment on random posts
                if self.posts and random.random() < 0.5:
                    post_id = random.choice(self.posts)
                    if random.random() < 0.7:
                        await self.like_post(user, post_id)
                    else:
                        await self.comment_on_post(user, post_id, self.generate_comment())
                        
            # Simulate reading time between actions
            await asyncio.sleep(random.uniform(2, 8))
            
    async def generate_initial_content(self):
        """Generate some initial content for new users"""
        print("Generating initial content...")
        
        # Each user creates 1-3 initial posts
        for user in self.users[:5]:  # First 5 users create content
            num_posts = random.randint(1, 3)
            for _ in range(num_posts):
                content = self.generate_post_content()
                post_id = await self.create_post(user, content)
                if post_id:
                    self.posts.append(post_id)
                await asyncio.sleep(0.5)
                
        # Create some initial follows
        for i, user in enumerate(self.users):
            # Each user follows 2-4 others
            num_follows = min(random.randint(2, 4), len(self.users) - 1)
            others = [u for u in self.users if u["username"] != user["username"]]
            
            for target in random.sample(others, min(num_follows, len(others))):
                await self.follow_user(user, target["username"])
                await asyncio.sleep(0.2)
                
    def print_stats(self):
        """Print current statistics"""
        elapsed = time.time() - self.stats["start_time"]
        total_requests = self.stats["requests"]
        error_rate = (self.stats["errors"] / total_requests * 100) if total_requests > 0 else 0
        
        avg_response_time = 0
        if self.stats["response_times"]:
            avg_response_time = sum(self.stats["response_times"]) / len(self.stats["response_times"])
            
        requests_per_second = total_requests / elapsed if elapsed > 0 else 0
        
        print("\n" + "="*50)
        print(f"Load Test Statistics - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*50)
        print(f"Duration: {elapsed:.1f} seconds")
        print(f"Total Requests: {total_requests}")
        print(f"Requests/Second: {requests_per_second:.2f}")
        print(f"Error Rate: {error_rate:.1f}%")
        print(f"Average Response Time: {avg_response_time*1000:.1f}ms")
        print(f"Active Users: {len(self.users)}")
        print(f"Total Posts Created: {len(self.posts)}")
        print("="*50)
        
    async def run(self, num_users: int = 10, duration_minutes: float = 5):
        """Run the load test"""
        print(f"Starting load test with {num_users} users for {duration_minutes} minutes...")
        print(f"Target URL: {self.base_url}")
        
        # Register users
        print("\nRegistering users...")
        for i in range(num_users):
            username = f"loadtest_user_{i}_{int(time.time())}"
            user = await self.register_user(username)
            if user:
                self.users.append(user)
            await asyncio.sleep(0.5)  # Don't overwhelm the auth service
            
        print(f"Successfully registered {len(self.users)} users")
        
        if len(self.users) < 2:
            print("Not enough users registered. Exiting.")
            return
            
        # Generate initial content
        await self.generate_initial_content()
        
        # Start user sessions
        print(f"\nStarting user sessions for {duration_minutes} minutes...")
        duration_seconds = duration_minutes * 60
        
        # Create tasks for all user sessions
        tasks = []
        for user in self.users:
            task = asyncio.create_task(self.simulate_user_session(user, duration_seconds))
            tasks.append(task)
            
        # Print stats periodically
        stats_interval = min(30, duration_seconds / 4)  # Print stats 4 times during test
        stats_task = asyncio.create_task(self.print_stats_periodically(stats_interval, duration_seconds))
        
        # Wait for all sessions to complete
        await asyncio.gather(*tasks)
        stats_task.cancel()
        
        # Print final stats
        self.print_stats()
        
    async def print_stats_periodically(self, interval: float, total_duration: float):
        """Print statistics periodically during the test"""
        elapsed = 0
        while elapsed < total_duration:
            await asyncio.sleep(interval)
            self.print_stats()
            elapsed += interval

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Load test for social media platform")
    parser.add_argument("--users", type=int, default=10, help="Number of users to simulate")
    parser.add_argument("--duration", type=float, default=5, help="Test duration in minutes")
    parser.add_argument("--url", type=str, default="http://localhost:8080", help="Base URL of the API")
    
    args = parser.parse_args()
    
    generator = SocialMediaLoadGenerator(base_url=args.url)
    asyncio.run(generator.run(num_users=args.users, duration_minutes=args.duration))
