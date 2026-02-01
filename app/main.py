"""FastAPI application with REST API endpoints."""
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from contextlib import asynccontextmanager

from app import crud, schemas
from app.database import get_db, init_db


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on startup."""
    init_db()
    yield


# Create FastAPI application
app = FastAPI(
    title="LUCICORE API",
    description="Database API for multiple services to connect",
    version="1.0.0",
    lifespan=lifespan
)


# Root endpoint
@app.get("/")
def read_root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to LUCICORE API",
        "version": "1.0.0",
        "endpoints": {
            "items": "/items",
            "services": "/services",
            "health": "/health"
        }
    }


# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Item endpoints
@app.post("/items/", response_model=schemas.Item, status_code=201)
def create_item(item: schemas.ItemCreate, db: Session = Depends(get_db)):
    """Create a new item."""
    return crud.create_item(db=db, item=item)


@app.get("/items/", response_model=List[schemas.Item])
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get list of items."""
    items = crud.get_items(db, skip=skip, limit=limit)
    return items


@app.get("/items/{item_id}", response_model=schemas.Item)
def read_item(item_id: int, db: Session = Depends(get_db)):
    """Get a specific item by ID."""
    db_item = crud.get_item(db, item_id=item_id)
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item


@app.put("/items/{item_id}", response_model=schemas.Item)
def update_item(item_id: int, item: schemas.ItemUpdate, db: Session = Depends(get_db)):
    """Update an existing item."""
    db_item = crud.update_item(db, item_id=item_id, item=item)
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item


@app.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """Delete an item."""
    success = crud.delete_item(db, item_id=item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted successfully"}


# Service endpoints
@app.post("/services/", response_model=schemas.Service, status_code=201)
def create_service(service: schemas.ServiceCreate, db: Session = Depends(get_db)):
    """Create a new service."""
    db_service = crud.get_service_by_name(db, name=service.name)
    if db_service:
        raise HTTPException(status_code=400, detail="Service with this name already exists")
    return crud.create_service(db=db, service=service)


@app.get("/services/", response_model=List[schemas.Service])
def read_services(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get list of services."""
    services = crud.get_services(db, skip=skip, limit=limit)
    return services


@app.get("/services/{service_id}", response_model=schemas.Service)
def read_service(service_id: int, db: Session = Depends(get_db)):
    """Get a specific service by ID."""
    db_service = crud.get_service(db, service_id=service_id)
    if db_service is None:
        raise HTTPException(status_code=404, detail="Service not found")
    return db_service


@app.put("/services/{service_id}", response_model=schemas.Service)
def update_service(service_id: int, service: schemas.ServiceUpdate, db: Session = Depends(get_db)):
    """Update an existing service."""
    db_service = crud.update_service(db, service_id=service_id, service=service)
    if db_service is None:
        raise HTTPException(status_code=404, detail="Service not found")
    return db_service


@app.delete("/services/{service_id}")
def delete_service(service_id: int, db: Session = Depends(get_db)):
    """Delete a service."""
    success = crud.delete_service(db, service_id=service_id)
    if not success:
        raise HTTPException(status_code=404, detail="Service not found")
    return {"message": "Service deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
