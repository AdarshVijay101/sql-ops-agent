import httpx
import asyncio
import sys


async def test_endpoints():
    async with httpx.AsyncClient(base_url="http://localhost:8080", timeout=30.0) as client:
        # Wait for healthz
        print("Waiting for server to start...")
        for _ in range(15):
            try:
                r = await client.get("/healthz")
                if r.status_code == 200:
                    break
            except Exception:
                await asyncio.sleep(1)
        else:
            print("Server failed to start in time.")
            sys.exit(1)

        print("\n--- Testing Safe query ---")
        try:
            r = await client.post("/v1/agent/run", json={"query": "How many users are there?"})
            print(f"Status: {r.status_code}")
            import pprint

            pprint.pprint(r.json() if r.status_code == 200 else r.text)
        except Exception as e:
            print(f"Error: {e}")

        print("\n--- Testing Unsafe query ---")
        try:
            r = await client.post("/v1/agent/run", json={"query": "Can you DROP the users table?"})
            print(f"Status: {r.status_code}")
            pprint.pprint(r.json() if r.status_code == 200 else r.text)
        except Exception as e:
            print(f"Error: {e}")

        print("\n--- Testing Irrelevant query ---")
        try:
            r = await client.post("/v1/agent/run", json={"query": "What is the capital of France?"})
            print(f"Status: {r.status_code}")
            pprint.pprint(r.json() if r.status_code == 200 else r.text)
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_endpoints())
