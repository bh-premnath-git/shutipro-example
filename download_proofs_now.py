#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, '/app')

from app.db.dynamo import download_proof_documents

async def main():
    proofs = {
        "document": {
            "proof": "https://ns.shuftipro.com/api/pea/7bcdfd1525cb5591e278b0ca0274f9da1a4f5616"
        },
        "access_token": "b2545ef785d5986301ac156534568a1ce3e0ab2a25a0e6c18136dcb8064eed57",
        "address": {
            "proof": "https://ns.shuftipro.com/api/pea/df1e2f30b84aa4f44657b73e8cd300d5e091a1ca"
        },
        "verification_video": "https://ns.shuftipro.com/api/pea/778ba23663ec849c1d777a7499f6d1ab29f26215",
        "verification_report": "https://ns.shuftipro.com/api/pea/1fddefee5bc2633e140172b3c4bae9d57f682831"
    }
    
    user_id = "user-1764934158"
    access_token = proofs["access_token"]
    
    print(f"Downloading proofs for {user_id}...")
    downloaded = await download_proof_documents(user_id, proofs, access_token)
    
    print(f"\n✅ Downloaded {len(downloaded)} files:")
    for proof_type, s3_key in downloaded.items():
        print(f"  - {proof_type}: {s3_key}")

if __name__ == "__main__":
    asyncio.run(main())
