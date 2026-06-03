import asyncio
import httpx
from utils.config import NETWORK_DIAGNOSTICS_URL, BILLING_RESOLUTION_URL
from orchestration.adk_remote_client import call_network_diagnostics, call_billing_resolution

async def check_health(url):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{url}/.well-known/agent-card.json")
            print(f"[{url}] Agent Card: {resp.status_code}")
            print(resp.json())
    except Exception as e:
        print(f"[{url}] Error fetching agent card: {e}")

async def main():
    print("Testing Network Diagnostics...")
    await check_health(NETWORK_DIAGNOSTICS_URL)
    res = call_network_diagnostics("My 5G keeps dropping in Austin near tower TX-512. Please diagnose.")
    print("Network Diagnostics Result:")
    print(res)

    print("\nTesting Billing Resolution...")
    await check_health(BILLING_RESOLUTION_URL)
    res = call_billing_resolution("Customer CUST-10002 was charged twice for Unlimited Plus. Investigate and apply credit.")
    print("Billing Resolution Result:")
    print(res)

if __name__ == "__main__":
    asyncio.run(main())
