#!/usr/bin/env python
"""
Phase 1 Functionality Tests
Tests all Phase 1 deliverables to ensure proper functionality.
"""

import requests
import json
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8000"


class TestRunner:
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.campaign_id = None
        self.character_id = None

    def test(self, name: str, func):
        """Run a test and track results."""
        try:
            print(f"\n{'='*60}")
            print(f"TEST: {name}")
            print(f"{'='*60}")
            func()
            print(f"✓ PASSED")
            self.tests_passed += 1
        except AssertionError as e:
            print(f"✗ FAILED: {e}")
            self.tests_failed += 1
        except Exception as e:
            print(f"✗ ERROR: {e}")
            self.tests_failed += 1

    def assert_status(self, response, expected_status: int):
        """Assert response status code."""
        if response.status_code != expected_status:
            raise AssertionError(
                f"Expected status {expected_status}, got {response.status_code}\n"
                f"Response: {response.text}"
            )

    def assert_field(self, data: Dict, field: str, value: Any = None):
        """Assert field exists and optionally has expected value."""
        if field not in data:
            raise AssertionError(f"Field '{field}' not found in response: {data}")
        if value is not None and data[field] != value:
            raise AssertionError(
                f"Field '{field}' = {data[field]}, expected {value}"
            )

    def test_health_check(self):
        """Test health check endpoint."""
        response = requests.get(f"{BASE_URL}/api/health")
        self.assert_status(response, 200)
        data = response.json()
        self.assert_field(data, "status", "healthy")
        self.assert_field(data, "version", "0.1.0")
        print(f"Response: {json.dumps(data, indent=2)}")

    def test_root_endpoint(self):
        """Test root endpoint."""
        response = requests.get(f"{BASE_URL}/")
        self.assert_status(response, 200)
        data = response.json()
        self.assert_field(data, "message")
        self.assert_field(data, "version")
        self.assert_field(data, "docs")
        print(f"Response: {json.dumps(data, indent=2)}")

    def test_create_campaign(self):
        """Test creating a campaign."""
        payload = {
            "name": "Test Campaign",
            "description": "A test campaign for Phase 1 validation"
        }
        response = requests.post(f"{BASE_URL}/api/campaigns/", json=payload)
        self.assert_status(response, 201)
        data = response.json()

        self.assert_field(data, "id")
        self.assert_field(data, "name", "Test Campaign")
        self.assert_field(data, "description", "A test campaign for Phase 1 validation")
        self.assert_field(data, "invite_code")
        self.assert_field(data, "gm_id")
        self.assert_field(data, "created_at")

        self.campaign_id = data["id"]
        print(f"Created campaign with ID: {self.campaign_id}")
        print(f"Invite code: {data['invite_code']}")
        print(f"Response: {json.dumps(data, indent=2)}")

    def test_list_campaigns(self):
        """Test listing campaigns."""
        response = requests.get(f"{BASE_URL}/api/campaigns/")
        self.assert_status(response, 200)
        data = response.json()

        if not isinstance(data, list):
            raise AssertionError("Expected list of campaigns")
        if len(data) == 0:
            raise AssertionError("Expected at least one campaign")

        print(f"Found {len(data)} campaign(s)")
        print(f"Response: {json.dumps(data, indent=2)}")

    def test_get_campaign(self):
        """Test getting a specific campaign."""
        if not self.campaign_id:
            raise AssertionError("No campaign ID available")

        response = requests.get(f"{BASE_URL}/api/campaigns/{self.campaign_id}")
        self.assert_status(response, 200)
        data = response.json()

        self.assert_field(data, "id", self.campaign_id)
        self.assert_field(data, "name", "Test Campaign")
        self.assert_field(data, "gm")  # Should include GM details
        self.assert_field(data, "players")  # Should include players list

        print(f"Response: {json.dumps(data, indent=2)}")

    def test_update_campaign(self):
        """Test updating a campaign."""
        if not self.campaign_id:
            raise AssertionError("No campaign ID available")

        payload = {
            "name": "Updated Test Campaign",
            "description": "Updated description"
        }
        response = requests.patch(
            f"{BASE_URL}/api/campaigns/{self.campaign_id}", json=payload
        )
        self.assert_status(response, 200)
        data = response.json()

        self.assert_field(data, "id", self.campaign_id)
        self.assert_field(data, "name", "Updated Test Campaign")
        self.assert_field(data, "description", "Updated description")

        print(f"Response: {json.dumps(data, indent=2)}")

    def test_create_character(self):
        """Test creating a character."""
        if not self.campaign_id:
            raise AssertionError("No campaign ID available")

        payload = {
            "campaign_id": self.campaign_id,
            "name": "Thorin Ironforge",
            "character_class": "Fighter",
            "level": 3,
            "alignment": "Lawful",
            "xp": 4000,
            "strength": 16,
            "intelligence": 10,
            "wisdom": 12,
            "dexterity": 14,
            "constitution": 15,
            "charisma": 11,
            "hp_max": 20,
            "hp_current": 20,
            "ac": 5,
            "gold": 150,
            "silver": 25
        }
        response = requests.post(f"{BASE_URL}/api/characters/", json=payload)
        self.assert_status(response, 201)
        data = response.json()

        self.assert_field(data, "id")
        self.assert_field(data, "name", "Thorin Ironforge")
        self.assert_field(data, "character_class", "Fighter")
        self.assert_field(data, "level", 3)
        self.assert_field(data, "strength", 16)
        self.assert_field(data, "hp_max", 20)
        self.assert_field(data, "gold", 150)

        self.character_id = data["id"]
        print(f"Created character with ID: {self.character_id}")
        print(f"Response: {json.dumps(data, indent=2)}")

    def test_list_characters(self):
        """Test listing all characters."""
        response = requests.get(f"{BASE_URL}/api/characters/")
        self.assert_status(response, 200)
        data = response.json()

        if not isinstance(data, list):
            raise AssertionError("Expected list of characters")
        if len(data) == 0:
            raise AssertionError("Expected at least one character")

        print(f"Found {len(data)} character(s)")
        print(f"Response: {json.dumps(data, indent=2)}")

    def test_list_characters_by_campaign(self):
        """Test listing characters filtered by campaign."""
        if not self.campaign_id:
            raise AssertionError("No campaign ID available")

        response = requests.get(
            f"{BASE_URL}/api/characters/?campaign_id={self.campaign_id}"
        )
        self.assert_status(response, 200)
        data = response.json()

        if not isinstance(data, list):
            raise AssertionError("Expected list of characters")
        if len(data) == 0:
            raise AssertionError("Expected at least one character")

        # Verify all characters belong to this campaign
        for char in data:
            if char["campaign_id"] != self.campaign_id:
                raise AssertionError(
                    f"Character {char['id']} belongs to campaign {char['campaign_id']}, "
                    f"expected {self.campaign_id}"
                )

        print(f"Found {len(data)} character(s) in campaign {self.campaign_id}")

    def test_get_character(self):
        """Test getting a specific character."""
        if not self.character_id:
            raise AssertionError("No character ID available")

        response = requests.get(f"{BASE_URL}/api/characters/{self.character_id}")
        self.assert_status(response, 200)
        data = response.json()

        self.assert_field(data, "id", self.character_id)
        self.assert_field(data, "name", "Thorin Ironforge")

        print(f"Response: {json.dumps(data, indent=2)}")

    def test_update_character(self):
        """Test updating a character."""
        if not self.character_id:
            raise AssertionError("No character ID available")

        payload = {
            "hp_current": 15,
            "gold": 175,
            "notes": "Wounded in battle"
        }
        response = requests.patch(
            f"{BASE_URL}/api/characters/{self.character_id}", json=payload
        )
        self.assert_status(response, 200)
        data = response.json()

        self.assert_field(data, "id", self.character_id)
        self.assert_field(data, "hp_current", 15)
        self.assert_field(data, "gold", 175)
        self.assert_field(data, "notes", "Wounded in battle")

        print(f"Response: {json.dumps(data, indent=2)}")

    def test_data_persistence(self):
        """Test that data persists across requests."""
        if not self.campaign_id or not self.character_id:
            raise AssertionError("No campaign or character ID available")

        # Get campaign again
        response = requests.get(f"{BASE_URL}/api/campaigns/{self.campaign_id}")
        self.assert_status(response, 200)
        campaign = response.json()
        self.assert_field(campaign, "name", "Updated Test Campaign")

        # Get character again
        response = requests.get(f"{BASE_URL}/api/characters/{self.character_id}")
        self.assert_status(response, 200)
        character = response.json()
        self.assert_field(character, "hp_current", 15)
        self.assert_field(character, "notes", "Wounded in battle")

        print("✓ Data persists correctly across requests")

    def test_404_errors(self):
        """Test that 404 errors are returned for non-existent resources."""
        # Non-existent campaign
        response = requests.get(f"{BASE_URL}/api/campaigns/99999")
        self.assert_status(response, 404)

        # Non-existent character
        response = requests.get(f"{BASE_URL}/api/characters/99999")
        self.assert_status(response, 404)

        print("✓ 404 errors returned correctly")

    def test_delete_character(self):
        """Test deleting a character."""
        if not self.character_id:
            raise AssertionError("No character ID available")

        response = requests.delete(f"{BASE_URL}/api/characters/{self.character_id}")
        self.assert_status(response, 204)

        # Verify character is deleted
        response = requests.get(f"{BASE_URL}/api/characters/{self.character_id}")
        self.assert_status(response, 404)

        print(f"✓ Character {self.character_id} deleted successfully")

    def test_delete_campaign(self):
        """Test deleting a campaign."""
        if not self.campaign_id:
            raise AssertionError("No campaign ID available")

        response = requests.delete(f"{BASE_URL}/api/campaigns/{self.campaign_id}")
        self.assert_status(response, 204)

        # Verify campaign is deleted
        response = requests.get(f"{BASE_URL}/api/campaigns/{self.campaign_id}")
        self.assert_status(response, 404)

        print(f"✓ Campaign {self.campaign_id} deleted successfully")

    def run_all_tests(self):
        """Run all Phase 1 tests."""
        print("\n" + "=" * 60)
        print("PHASE 1 FUNCTIONALITY TESTS")
        print("=" * 60)

        # Health checks
        self.test("Health Check Endpoint", self.test_health_check)
        self.test("Root Endpoint", self.test_root_endpoint)

        # Campaign CRUD
        self.test("Create Campaign", self.test_create_campaign)
        self.test("List Campaigns", self.test_list_campaigns)
        self.test("Get Campaign", self.test_get_campaign)
        self.test("Update Campaign", self.test_update_campaign)

        # Character CRUD
        self.test("Create Character", self.test_create_character)
        self.test("List Characters", self.test_list_characters)
        self.test("List Characters by Campaign", self.test_list_characters_by_campaign)
        self.test("Get Character", self.test_get_character)
        self.test("Update Character", self.test_update_character)

        # Data persistence and validation
        self.test("Data Persistence", self.test_data_persistence)
        self.test("404 Error Handling", self.test_404_errors)

        # Cleanup
        self.test("Delete Character", self.test_delete_character)
        self.test("Delete Campaign", self.test_delete_campaign)

        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"✓ Passed: {self.tests_passed}")
        print(f"✗ Failed: {self.tests_failed}")
        print(f"Total: {self.tests_passed + self.tests_failed}")
        print("=" * 60)

        if self.tests_failed == 0:
            print("\n🎉 ALL TESTS PASSED! Phase 1 is fully functional.")
            return 0
        else:
            print(f"\n❌ {self.tests_failed} test(s) failed.")
            return 1


if __name__ == "__main__":
    runner = TestRunner()
    sys.exit(runner.run_all_tests())
