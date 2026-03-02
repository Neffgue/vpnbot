"""
Example usage and testing of the VPN Sales System API.

This file demonstrates how to use the API programmatically.
"""

import asyncio
from decimal import Decimal

# Example 1: Direct service usage
async def example_user_creation():
    """Example: Create a user directly via service."""
    from backend.database import AsyncSessionLocal
    from backend.services.user_service import UserService

    async with AsyncSessionLocal() as db:
        service = UserService(db)
        
        # Create a new user
        user = await service.create_user(
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
        )
        print(f"Created user: {user.referral_code}")
        
        # Get user by telegram ID
        retrieved = await service.get_user_by_telegram_id(123456789)
        print(f"Retrieved user: {retrieved.id}")
        
        # Add balance
        updated = await service.add_balance(user.id, Decimal("100.00"))
        print(f"Updated balance: {updated.balance}")


# Example 2: Server management
async def example_server_management():
    """Example: Create and manage VPN servers."""
    from backend.database import AsyncSessionLocal
    from backend.services.server_service import ServerService

    async with AsyncSessionLocal() as db:
        service = ServerService(db)
        
        # Create a server
        server = await service.create_server(
            name="NL-Amsterdam-01",
            country_emoji="🇳🇱",
            country_name="Netherlands",
            host="195.154.1.1",
            port=443,
            panel_url="https://xui.example.com",
            panel_username="admin",
            panel_password="secure_password",
            inbound_id=1,
            order_index=1,
        )
        print(f"Created server: {server.name}")
        
        # Get active servers
        active = await service.get_active_servers()
        print(f"Active servers: {len(active)}")


# Example 3: Subscription creation
async def example_subscription_creation():
    """Example: Create a subscription for a user."""
    from backend.database import AsyncSessionLocal
    from backend.services.user_service import UserService
    from backend.services.subscription_service import SubscriptionService

    async with AsyncSessionLocal() as db:
        # Create user first
        user_service = UserService(db)
        user = await user_service.create_user(
            telegram_id=987654321,
            username="vpnuser",
            first_name="VPN",
        )
        
        # Create subscription
        sub_service = SubscriptionService(db)
        subscription = await sub_service.create_subscription(
            user_id=user.id,
            plan_name="Solo",
            period_days=30,
            device_limit=1,
            traffic_gb=100,
        )
        print(f"Created subscription: {subscription.xui_client_uuid}")
        print(f"Expires at: {subscription.expires_at}")


# Example 4: Payment processing
async def example_payment_processing():
    """Example: Create and process a payment."""
    from backend.database import AsyncSessionLocal
    from backend.services.user_service import UserService
    from backend.services.payment_service import PaymentService

    async with AsyncSessionLocal() as db:
        # Create user
        user_service = UserService(db)
        user = await user_service.create_user(
            telegram_id=555666777,
            username="payuser",
        )
        
        # Create payment
        payment_service = PaymentService(db)
        payment = await payment_service.create_payment(
            user_id=user.id,
            plan_name="Family",
            period_days=90,
            device_limit=5,
            amount=Decimal("500.00"),
            provider="telegram_stars",
            provider_payment_id="unique_payment_id_123",
        )
        print(f"Created payment: {payment.id}")
        print(f"Status: {payment.status}")
        
        # Mark as completed
        completed = await payment_service.mark_completed(payment.id)
        print(f"Payment completed: {completed.status}")


# Example 5: Referral system
async def example_referral_system():
    """Example: Create referral relationship."""
    from backend.database import AsyncSessionLocal
    from backend.services.user_service import UserService
    from backend.services.referral_service import ReferralService

    async with AsyncSessionLocal() as db:
        # Create referrer
        user_service = UserService(db)
        referrer = await user_service.create_user(
            telegram_id=111111111,
            username="referrer",
        )
        
        # Create referred user
        referred = await user_service.create_user(
            telegram_id=222222222,
            username="referred",
            referred_by=referrer.id,
        )
        
        # Create referral record
        referral_service = ReferralService(db)
        referral = await referral_service.create_referral(
            referrer_id=referrer.id,
            referred_id=referred.id,
            bonus_days=7,
        )
        print(f"Created referral: {referral.id}")
        
        # Get referrer stats
        stats = await referral_service.get_referrer_stats(referrer.id)
        print(f"Referrer stats: {stats}")


# Example 6: XUI Service (3x-ui panel integration)
async def example_xui_service():
    """Example: Interact with 3x-ui panel."""
    from backend.services.xui_service import XUIService

    # Initialize XUI service
    xui = XUIService(
        panel_url="https://xui.example.com",
        panel_username="admin",
        panel_password="secure_password",
        inbound_id=1,
    )
    
    try:
        # Login to panel
        logged_in = await xui.login()
        if logged_in:
            print("Logged in to XUI panel")
            
            # Add a client
            success = await xui.add_client(
                client_uuid="550e8400-e29b-41d4-a716-446655440000",
                traffic_limit_gb=100,
                expiry_timestamp_ms=1704067200000,  # 2024-01-01
            )
            print(f"Client added: {success}")
            
            # Get client stats
            stats = await xui.get_client_stats("550e8400-e29b-41d4-a716-446655440000")
            print(f"Client stats: {stats}")
    finally:
        await xui.close()


# Example 7: Admin operations
async def example_admin_operations():
    """Example: Admin panel operations."""
    from backend.database import AsyncSessionLocal
    from backend.services.user_service import UserService
    from backend.models.config import PlanPrice, BotText
    from uuid import uuid4
    from decimal import Decimal

    async with AsyncSessionLocal() as db:
        # Create plan price
        plan_price = PlanPrice(
            id=str(uuid4()),
            plan_name="Solo",
            period_days=30,
            price_rub=Decimal("299.99"),
        )
        db.add(plan_price)
        
        # Create bot text
        bot_text = BotText(
            id=str(uuid4()),
            key="welcome_message",
            value="Welcome to our VPN service! 🎉",
            description="Message shown when user starts the bot",
        )
        db.add(bot_text)
        
        await db.commit()
        print("Admin configurations created")
        
        # Search users
        user_service = UserService(db)
        results = await user_service.search_users("test", limit=10)
        print(f"Search results: {len(results)} users found")


async def main():
    """Run all examples."""
    print("=" * 50)
    print("VPN Sales System API - Usage Examples")
    print("=" * 50)
    
    # Note: These examples require a running database
    # Uncomment to run specific examples:
    
    # await example_user_creation()
    # await example_server_management()
    # await example_subscription_creation()
    # await example_payment_processing()
    # await example_referral_system()
    # await example_xui_service()
    # await example_admin_operations()
    
    print("\nExamples are commented out to prevent DB modifications.")
    print("Uncomment the examples you want to run in the main() function.")


if __name__ == "__main__":
    asyncio.run(main())
