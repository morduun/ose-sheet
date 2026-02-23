#!/usr/bin/env python
"""
Phase 2 Functionality Tests
Tests authentication, permissions, items, and spells functionality.
"""

import requests
import json
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8000"


class Phase2TestRunner:
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.token1 = None  # User 1 token
        self.token2 = None  # User 2 token (for permission tests)
        self.campaign_id = None
        self.character_id = None
        self.item_id = None
        self.spell_id = None

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

    # ========== Authentication Tests ==========

    def test_health_check_no_auth(self):
        """Test health check works without authentication."""
        response = requests.get(f"{BASE_URL}/api/health")
        self.assert_status(response, 200)
        data = response.json()
        self.assert_field(data, "status", "healthy")
        print(f"Health check successful")

    def test_dev_token_endpoint(self):
        """Test getting a development token."""
        payload = {"email": "test@example.com"}
        response = requests.post(f"{BASE_URL}/api/auth/token", json=payload)
        self.assert_status(response, 200)
        data = response.json()

        self.assert_field(data, "access_token")
        self.assert_field(data, "token_type", "bearer")
        self.assert_field(data, "user")

        self.token1 = data["access_token"]
        print(f"Token obtained: {self.token1[:20]}...")
        print(f"User: {data['user']}")

    def test_get_current_user(self):
        """Test /api/auth/me endpoint."""
        if not self.token1:
            raise AssertionError("No token available")

        headers = {"Authorization": f"Bearer {self.token1}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        self.assert_status(response, 200)
        data = response.json()

        self.assert_field(data, "id")
        self.assert_field(data, "name", "Test User")
        print(f"Current user: {data}")

    def test_invalid_token_401(self):
        """Test that invalid token returns 401."""
        headers = {"Authorization": "Bearer invalid-token"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        self.assert_status(response, 401)
        print(f"✓ Invalid token correctly rejected with 401")

    # ========== Protected Endpoints Tests ==========

    def test_campaigns_require_auth(self):
        """Test that campaign endpoints require authentication."""
        response = requests.get(f"{BASE_URL}/api/campaigns/")
        self.assert_status(response, 401)
        print(f"✓ Campaign list correctly requires authentication")

    def test_characters_require_auth(self):
        """Test that character endpoints require authentication."""
        response = requests.get(f"{BASE_URL}/api/characters/")
        self.assert_status(response, 401)
        print(f"✓ Character list correctly requires authentication")

    # ========== Campaign with Auth Tests ==========

    def test_create_campaign_authenticated(self):
        """Test creating a campaign with authentication."""
        if not self.token1:
            raise AssertionError("No token available")

        headers = {"Authorization": f"Bearer {self.token1}"}
        payload = {"name": "Test Campaign", "description": "Phase 2 test campaign"}
        response = requests.post(f"{BASE_URL}/api/campaigns/", json=payload, headers=headers)
        self.assert_status(response, 201)
        data = response.json()

        self.assert_field(data, "id")
        self.assert_field(data, "name", "Test Campaign")
        self.assert_field(data, "gm_id", 1)  # Should be current user
        self.assert_field(data, "invite_code")

        self.campaign_id = data["id"]
        print(f"Created campaign ID: {self.campaign_id}")
        print(f"Invite code: {data['invite_code']}")

    def test_list_user_campaigns(self):
        """Test listing campaigns filters by user access."""
        if not self.token1:
            raise AssertionError("No token available")

        headers = {"Authorization": f"Bearer {self.token1}"}
        response = requests.get(f"{BASE_URL}/api/campaigns/", headers=headers)
        self.assert_status(response, 200)
        data = response.json()

        if not isinstance(data, list):
            raise AssertionError("Expected list of campaigns")

        # Should see our campaign
        if len(data) != 1 or data[0]["id"] != self.campaign_id:
            raise AssertionError("Should see exactly our campaign")

        print(f"✓ User sees {len(data)} campaign(s) they have access to")

    # ========== Items CRUD Tests ==========

    def test_create_item(self):
        """Test creating an item for a campaign."""
        if not self.token1 or not self.campaign_id:
            raise AssertionError("Prerequisites not met")

        headers = {"Authorization": f"Bearer {self.token1}"}
        payload = {
            "name": "Longsword +1",
            "item_type": "weapon",
            "description_player": "A fine longsword with a +1 enchantment",
            "description_gm": "This sword was forged by elven smiths",
            "item_metadata": {
                "damage_dice": "1d8",
                "damage_bonus": 1,
                "hit_bonus": 1
            },
            "campaign_id": self.campaign_id,
            "is_default": False
        }
        response = requests.post(f"{BASE_URL}/api/items/", json=payload, headers=headers)
        self.assert_status(response, 201)
        data = response.json()

        self.assert_field(data, "id")
        self.assert_field(data, "name", "Longsword +1")
        self.assert_field(data, "item_type", "weapon")
        self.assert_field(data, "campaign_id", self.campaign_id)

        self.item_id = data["id"]
        print(f"Created item ID: {self.item_id}")
        print(f"Item metadata: {data['item_metadata']}")

    def test_list_items(self):
        """Test listing items."""
        if not self.token1:
            raise AssertionError("No token available")

        headers = {"Authorization": f"Bearer {self.token1}"}
        response = requests.get(
            f"{BASE_URL}/api/items/?campaign_id={self.campaign_id}",
            headers=headers
        )
        self.assert_status(response, 200)
        data = response.json()

        if not isinstance(data, list):
            raise AssertionError("Expected list of items")

        # Should see our item
        found = any(item["id"] == self.item_id for item in data)
        if not found:
            raise AssertionError(f"Item {self.item_id} not in list")

        print(f"✓ Found {len(data)} item(s) in campaign")

    def test_get_item_as_gm(self):
        """Test GM sees full item details including GM description."""
        if not self.token1 or not self.item_id:
            raise AssertionError("Prerequisites not met")

        headers = {"Authorization": f"Bearer {self.token1}"}
        response = requests.get(f"{BASE_URL}/api/items/{self.item_id}", headers=headers)
        self.assert_status(response, 200)
        data = response.json()

        # GM should see description_gm
        self.assert_field(data, "description_gm")
        print(f"✓ GM sees full details including GM description")

    def test_update_item(self):
        """Test updating an item."""
        if not self.token1 or not self.item_id:
            raise AssertionError("Prerequisites not met")

        headers = {"Authorization": f"Bearer {self.token1}"}
        payload = {"description_player": "An even finer longsword"}
        response = requests.patch(
            f"{BASE_URL}/api/items/{self.item_id}",
            json=payload,
            headers=headers
        )
        self.assert_status(response, 200)
        data = response.json()

        self.assert_field(data, "description_player", "An even finer longsword")
        print(f"✓ Item updated successfully")

    # ========== Spells CRUD Tests ==========

    def test_create_spell(self):
        """Test creating a spell."""
        if not self.token1:
            raise AssertionError("No token available")

        headers = {"Authorization": f"Bearer {self.token1}"}
        payload = {
            "name": "Magic Missile",
            "level": 1,
            "spell_class": "magic-user",
            "description": "1d4+1 force damage per missile, auto-hit",
            "range": "150'",
            "duration": "Instantaneous"
        }
        response = requests.post(f"{BASE_URL}/api/spells/", json=payload, headers=headers)
        self.assert_status(response, 201)
        data = response.json()

        self.assert_field(data, "id")
        self.assert_field(data, "name", "Magic Missile")
        self.assert_field(data, "level", 1)
        self.assert_field(data, "spell_class", "magic-user")

        self.spell_id = data["id"]
        print(f"Created spell ID: {self.spell_id}")

    def test_list_spells_by_level(self):
        """Test listing spells filtered by level."""
        if not self.token1:
            raise AssertionError("No token available")

        headers = {"Authorization": f"Bearer {self.token1}"}
        response = requests.get(f"{BASE_URL}/api/spells/?level=1", headers=headers)
        self.assert_status(response, 200)
        data = response.json()

        if not isinstance(data, list):
            raise AssertionError("Expected list of spells")

        # All spells should be level 1
        for spell in data:
            if spell["level"] != 1:
                raise AssertionError(f"Spell {spell['id']} is not level 1")

        print(f"✓ Found {len(data)} level 1 spell(s)")

    def test_list_spells_by_class(self):
        """Test listing spells filtered by class."""
        if not self.token1:
            raise AssertionError("No token available")

        headers = {"Authorization": f"Bearer {self.token1}"}
        response = requests.get(
            f"{BASE_URL}/api/spells/?spell_class=magic-user",
            headers=headers
        )
        self.assert_status(response, 200)
        data = response.json()

        # All spells should be magic-user
        for spell in data:
            if spell["spell_class"] != "magic-user":
                raise AssertionError(f"Spell {spell['id']} is not magic-user")

        print(f"✓ Found {len(data)} magic-user spell(s)")

    # ========== Character with Items/Spells Tests ==========

    def test_create_character_with_auth(self):
        """Test creating a character with authentication."""
        if not self.token1 or not self.campaign_id:
            raise AssertionError("Prerequisites not met")

        headers = {"Authorization": f"Bearer {self.token1}"}
        payload = {
            "campaign_id": self.campaign_id,
            "name": "Gandalf",
            "character_class": "Magic-User",
            "level": 5,
            "intelligence": 18,
            "hp_max": 15
        }
        response = requests.post(f"{BASE_URL}/api/characters/", json=payload, headers=headers)
        self.assert_status(response, 201)
        data = response.json()

        self.assert_field(data, "id")
        self.assert_field(data, "name", "Gandalf")
        self.assert_field(data, "player_id", 1)  # Should be current user

        self.character_id = data["id"]
        print(f"Created character ID: {self.character_id}")

    def test_assign_item_to_character(self):
        """Test assigning an item to a character."""
        if not self.token1 or not self.item_id or not self.character_id:
            raise AssertionError("Prerequisites not met")

        headers = {"Authorization": f"Bearer {self.token1}"}
        payload = {
            "character_id": self.character_id,
            "quantity": 1
        }
        response = requests.post(
            f"{BASE_URL}/api/items/{self.item_id}/assign",
            json=payload,
            headers=headers
        )
        self.assert_status(response, 200)
        data = response.json()

        self.assert_field(data, "message")
        print(f"✓ Item assigned: {data['message']}")

    def test_add_spell_to_spellbook(self):
        """Test adding a spell to character's spellbook."""
        if not self.token1 or not self.spell_id or not self.character_id:
            raise AssertionError("Prerequisites not met")

        headers = {"Authorization": f"Bearer {self.token1}"}
        payload = {"character_id": self.character_id}
        response = requests.post(
            f"{BASE_URL}/api/spells/{self.spell_id}/learn",
            json=payload,
            headers=headers
        )
        self.assert_status(response, 200)
        data = response.json()

        self.assert_field(data, "message")
        print(f"✓ Spell learned: {data['message']}")

    # ========== Permission Tests ==========

    def test_create_second_user(self):
        """Create a second user for permission testing."""
        # First create the user in database
        from app.database import SessionLocal
        from app.models import User

        db = SessionLocal()
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == "user2@example.com").first()
        if not existing_user:
            user2 = User(
                google_id="test-google-id-2",
                email="user2@example.com",
                name="Test User 2"
            )
            db.add(user2)
            db.commit()
        db.close()

        # Get token for user 2
        payload = {"email": "user2@example.com"}
        response = requests.post(f"{BASE_URL}/api/auth/token", json=payload)
        self.assert_status(response, 200)
        data = response.json()

        self.token2 = data["access_token"]
        print(f"✓ Created second user and obtained token")

    def test_non_gm_cannot_edit_campaign(self):
        """Test that non-GM cannot edit campaign."""
        if not self.token2 or not self.campaign_id:
            raise AssertionError("Prerequisites not met")

        headers = {"Authorization": f"Bearer {self.token2}"}
        payload = {"name": "Hacked Campaign"}
        response = requests.patch(
            f"{BASE_URL}/api/campaigns/{self.campaign_id}",
            json=payload,
            headers=headers
        )
        self.assert_status(response, 403)
        print(f"✓ Non-GM correctly blocked from editing campaign (403)")

    def test_non_owner_cannot_edit_character(self):
        """Test that non-owner cannot edit character."""
        if not self.token2 or not self.character_id:
            raise AssertionError("Prerequisites not met")

        headers = {"Authorization": f"Bearer {self.token2}"}
        payload = {"hp_current": 1}
        response = requests.patch(
            f"{BASE_URL}/api/characters/{self.character_id}",
            json=payload,
            headers=headers
        )
        self.assert_status(response, 403)
        print(f"✓ Non-owner correctly blocked from editing character (403)")

    def test_user_cannot_see_other_campaigns(self):
        """Test that user 2 cannot see user 1's campaign."""
        if not self.token2:
            raise AssertionError("No token2 available")

        headers = {"Authorization": f"Bearer {self.token2}"}
        response = requests.get(f"{BASE_URL}/api/campaigns/", headers=headers)
        self.assert_status(response, 200)
        data = response.json()

        # User 2 should not see any campaigns
        if len(data) != 0:
            raise AssertionError(f"User 2 should not see campaigns, found {len(data)}")

        print(f"✓ User correctly sees only their own campaigns (0)")

    # ========== Cleanup Tests ==========

    def test_unassign_item(self):
        """Test unassigning an item from character."""
        if not self.token1 or not self.item_id or not self.character_id:
            raise AssertionError("Prerequisites not met")

        headers = {"Authorization": f"Bearer {self.token1}"}
        response = requests.delete(
            f"{BASE_URL}/api/items/{self.item_id}/assign/{self.character_id}",
            headers=headers
        )
        self.assert_status(response, 204)
        print(f"✓ Item unassigned successfully")

    def test_remove_spell_from_spellbook(self):
        """Test removing a spell from spellbook."""
        if not self.token1 or not self.spell_id or not self.character_id:
            raise AssertionError("Prerequisites not met")

        headers = {"Authorization": f"Bearer {self.token1}"}
        response = requests.delete(
            f"{BASE_URL}/api/spells/{self.spell_id}/forget/{self.character_id}",
            headers=headers
        )
        self.assert_status(response, 204)
        print(f"✓ Spell removed from spellbook")

    def test_delete_character(self):
        """Test deleting a character."""
        if not self.token1 or not self.character_id:
            raise AssertionError("Prerequisites not met")

        headers = {"Authorization": f"Bearer {self.token1}"}
        response = requests.delete(
            f"{BASE_URL}/api/characters/{self.character_id}",
            headers=headers
        )
        self.assert_status(response, 204)
        print(f"✓ Character deleted")

    def test_delete_item(self):
        """Test deleting an item."""
        if not self.token1 or not self.item_id:
            raise AssertionError("Prerequisites not met")

        headers = {"Authorization": f"Bearer {self.token1}"}
        response = requests.delete(f"{BASE_URL}/api/items/{self.item_id}", headers=headers)
        self.assert_status(response, 204)
        print(f"✓ Item deleted")

    def test_delete_spell(self):
        """Test deleting a spell."""
        if not self.token1 or not self.spell_id:
            raise AssertionError("Prerequisites not met")

        headers = {"Authorization": f"Bearer {self.token1}"}
        response = requests.delete(f"{BASE_URL}/api/spells/{self.spell_id}", headers=headers)
        self.assert_status(response, 204)
        print(f"✓ Spell deleted")

    def test_delete_campaign(self):
        """Test deleting a campaign."""
        if not self.token1 or not self.campaign_id:
            raise AssertionError("Prerequisites not met")

        headers = {"Authorization": f"Bearer {self.token1}"}
        response = requests.delete(
            f"{BASE_URL}/api/campaigns/{self.campaign_id}",
            headers=headers
        )
        self.assert_status(response, 204)
        print(f"✓ Campaign deleted")

    def run_all_tests(self):
        """Run all Phase 2 tests."""
        print("\n" + "=" * 60)
        print("PHASE 2 FUNCTIONALITY TESTS")
        print("=" * 60)

        # Basic health checks
        self.test("Health check without auth", self.test_health_check_no_auth)

        # Authentication tests
        self.test("Get development token", self.test_dev_token_endpoint)
        self.test("Get current user with token", self.test_get_current_user)
        self.test("Invalid token returns 401", self.test_invalid_token_401)

        # Protected endpoint tests
        self.test("Campaigns require authentication", self.test_campaigns_require_auth)
        self.test("Characters require authentication", self.test_characters_require_auth)

        # Authenticated campaign tests
        self.test("Create campaign with auth", self.test_create_campaign_authenticated)
        self.test("List user's campaigns", self.test_list_user_campaigns)

        # Items tests
        self.test("Create item", self.test_create_item)
        self.test("List items", self.test_list_items)
        self.test("Get item as GM (full details)", self.test_get_item_as_gm)
        self.test("Update item", self.test_update_item)

        # Spells tests
        self.test("Create spell", self.test_create_spell)
        self.test("List spells by level", self.test_list_spells_by_level)
        self.test("List spells by class", self.test_list_spells_by_class)

        # Character integration tests
        self.test("Create character with auth", self.test_create_character_with_auth)
        self.test("Assign item to character", self.test_assign_item_to_character)
        self.test("Add spell to spellbook", self.test_add_spell_to_spellbook)

        # Permission tests
        self.test("Create second user", self.test_create_second_user)
        self.test("Non-GM cannot edit campaign", self.test_non_gm_cannot_edit_campaign)
        self.test("Non-owner cannot edit character", self.test_non_owner_cannot_edit_character)
        self.test("User only sees own campaigns", self.test_user_cannot_see_other_campaigns)

        # Cleanup tests
        self.test("Unassign item from character", self.test_unassign_item)
        self.test("Remove spell from spellbook", self.test_remove_spell_from_spellbook)
        self.test("Delete character", self.test_delete_character)
        self.test("Delete item", self.test_delete_item)
        self.test("Delete spell", self.test_delete_spell)
        self.test("Delete campaign", self.test_delete_campaign)

        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"✓ Passed: {self.tests_passed}")
        print(f"✗ Failed: {self.tests_failed}")
        print(f"Total: {self.tests_passed + self.tests_failed}")
        print("=" * 60)

        if self.tests_failed == 0:
            print("\n🎉 ALL TESTS PASSED! Phase 2 is fully functional.")
            return 0
        else:
            print(f"\n❌ {self.tests_failed} test(s) failed.")
            return 1


if __name__ == "__main__":
    runner = Phase2TestRunner()
    sys.exit(runner.run_all_tests())
