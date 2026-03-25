from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models import ClassificationRequest, ClassificationResponse
from app.services.classifier import WebsiteClassifier
import asyncio

router = APIRouter()
classifier = WebsiteClassifier()

@router.post("/classify", response_model=ClassificationResponse)
async def classify_website(request: ClassificationRequest):
    """Classify a publisher website"""
    try:
        result = await asyncio.wait_for(
            classifier.classify(str(request.url)),
            timeout=25.0
        )
        return ClassificationResponse(**result)
        
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=408,
            detail="Classification timed out after 25 seconds"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Classification failed: {str(e)}"
        )
