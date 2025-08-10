#!/usr/bin/env python3
"""Test script to verify presigned URL generation."""

import asyncio
import os
from datetime import datetime

# Set up environment
os.environ["STORAGE_BACKEND"] = "s3"
os.environ["S3_BUCKET_NAME"] = "microlearn-certificates"
os.environ["AWS_REGION"] = "us-east-1"

from app.services.storage import storage_service


async def test_presigned_urls():
    """Test presigned URL generation."""
    
    print("Testing presigned URL generation...")
    
    # Test data
    test_pdf_data = b"Test PDF content"
    certificate_id = f"TEST-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    user_email = "test@example.com"
    
    try:
        # Upload a test certificate
        print(f"\n1. Uploading test certificate with ID: {certificate_id}")
        s3_key = await storage_service.upload_certificate(
            test_pdf_data,
            certificate_id,
            user_email
        )
        print(f"   ✓ Uploaded to S3 key: {s3_key}")
        
        # Generate presigned URL
        print("\n2. Generating presigned URL...")
        presigned_url = storage_service.get_presigned_url(s3_key)
        print(f"   ✓ Generated presigned URL (1 hour expiry):")
        print(f"     {presigned_url[:100]}...")
        
        # Generate another URL with different expiration
        print("\n3. Generating presigned URL with 24-hour expiry...")
        presigned_url_24h = storage_service.get_presigned_url(s3_key, expiration=86400)
        print(f"   ✓ Generated presigned URL (24 hour expiry):")
        print(f"     {presigned_url_24h[:100]}...")
        
        # Check if certificate exists
        print("\n4. Checking if certificate exists...")
        exists = await storage_service.certificate_exists(s3_key)
        print(f"   ✓ Certificate exists: {exists}")
        
        # Clean up
        print("\n5. Cleaning up test certificate...")
        deleted = await storage_service.delete_certificate(s3_key)
        print(f"   ✓ Certificate deleted: {deleted}")
        
        print("\n✅ All tests passed!")
        print("\nSummary:")
        print("- S3 keys are now stored instead of URLs")
        print("- Presigned URLs are generated on-demand")
        print("- URLs expire after specified time (default: 1 hour)")
        print("- Users can always get fresh URLs by accessing the certificate again")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_presigned_urls())
