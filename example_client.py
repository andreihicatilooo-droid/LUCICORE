"""
Example: Multiple Services Connecting to LUCICORE API

This example demonstrates how multiple services can connect to and interact
with the LUCICORE API.
"""

import requests
import json
from typing import Dict, Any

# Base URL for the API
BASE_URL = "http://localhost:8000"


class LucicoreClient:
    """Client library for connecting to LUCICORE API."""
    
    def __init__(self, base_url: str, service_name: str):
        """
        Initialize the client.
        
        Args:
            base_url: Base URL of the LUCICORE API
            service_name: Name of the service connecting to the API
        """
        self.base_url = base_url
        self.service_name = service_name
        self.service_id = None
        
    def register_service(self, description: str = None, endpoint: str = None) -> Dict[str, Any]:
        """Register this service with the API."""
        data = {
            "name": self.service_name,
            "description": description or f"{self.service_name} service",
            "endpoint": endpoint
        }
        response = requests.post(f"{self.base_url}/services/", json=data)
        response.raise_for_status()
        service = response.json()
        self.service_id = service["id"]
        return service
    
    def create_item(self, name: str, description: str = None) -> Dict[str, Any]:
        """Create a new item."""
        data = {"name": name, "description": description}
        response = requests.post(f"{self.base_url}/items/", json=data)
        response.raise_for_status()
        return response.json()
    
    def get_items(self) -> list:
        """Get all items."""
        response = requests.get(f"{self.base_url}/items/")
        response.raise_for_status()
        return response.json()
    
    def get_item(self, item_id: int) -> Dict[str, Any]:
        """Get a specific item."""
        response = requests.get(f"{self.base_url}/items/{item_id}")
        response.raise_for_status()
        return response.json()
    
    def update_item(self, item_id: int, name: str = None, description: str = None) -> Dict[str, Any]:
        """Update an item."""
        data = {}
        if name:
            data["name"] = name
        if description:
            data["description"] = description
        response = requests.put(f"{self.base_url}/items/{item_id}", json=data)
        response.raise_for_status()
        return response.json()
    
    def delete_item(self, item_id: int) -> Dict[str, Any]:
        """Delete an item."""
        response = requests.delete(f"{self.base_url}/items/{item_id}")
        response.raise_for_status()
        return response.json()


def main():
    """Demonstrate multiple services connecting to the API."""
    print("=== LUCICORE API - Multiple Services Example ===\n")
    
    # Service 1: Data Producer
    print("1. Service A (Data Producer) connecting...")
    service_a = LucicoreClient(BASE_URL, "Data Producer")
    service_a.register_service(
        description="Service that produces data",
        endpoint="http://producer.example.com"
    )
    print(f"   Service A registered with ID: {service_a.service_id}\n")
    
    # Service 2: Data Consumer
    print("2. Service B (Data Consumer) connecting...")
    service_b = LucicoreClient(BASE_URL, "Data Consumer")
    service_b.register_service(
        description="Service that consumes data",
        endpoint="http://consumer.example.com"
    )
    print(f"   Service B registered with ID: {service_b.service_id}\n")
    
    # Service 3: Data Processor
    print("3. Service C (Data Processor) connecting...")
    service_c = LucicoreClient(BASE_URL, "Data Processor")
    service_c.register_service(
        description="Service that processes data",
        endpoint="http://processor.example.com"
    )
    print(f"   Service C registered with ID: {service_c.service_id}\n")
    
    # Service A creates some items
    print("4. Service A creating items...")
    item1 = service_a.create_item("User Data", "Data from user activity")
    item2 = service_a.create_item("System Logs", "System log entries")
    print(f"   Created item {item1['id']}: {item1['name']}")
    print(f"   Created item {item2['id']}: {item2['name']}\n")
    
    # Service B reads items
    print("5. Service B reading all items...")
    items = service_b.get_items()
    print(f"   Found {len(items)} items:")
    for item in items:
        print(f"   - ID {item['id']}: {item['name']}")
    print()
    
    # Service C processes and updates items
    print("6. Service C processing items...")
    updated_item = service_c.update_item(
        item1['id'],
        description="Processed user activity data"
    )
    print(f"   Updated item {updated_item['id']}")
    print(f"   New description: {updated_item['description']}\n")
    
    # Service B reads updated data
    print("7. Service B reading updated item...")
    updated = service_b.get_item(item1['id'])
    print(f"   Item {updated['id']}: {updated['name']}")
    print(f"   Description: {updated['description']}\n")
    
    print("=== All services successfully interacted with the API ===")


if __name__ == "__main__":
    # Note: Make sure the LUCICORE API is running before executing this example
    # Run: python -m app.main
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to LUCICORE API.")
        print("Please make sure the API is running:")
        print("  python -m app.main")
    except Exception as e:
        print(f"ERROR: {e}")
