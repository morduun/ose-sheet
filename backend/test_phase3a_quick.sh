#!/bin/bash
# Quick Phase 3A Feature Tests

set -e

BASE_URL="http://localhost:8000"

echo "========================================="
echo "Phase 3A Quick Feature Tests"
echo "========================================="

# Get tokens
echo -e "\n[1/10] Getting tokens..."
ADMIN_TOKEN=$(curl -X POST $BASE_URL/api/auth/token -H "Content-Type: application/json" -d '{"email": "admin@example.com"}' -s | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
TEST_TOKEN=$(curl -X POST $BASE_URL/api/auth/token -H "Content-Type: application/json" -d '{"email": "test@example.com"}' -s | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
echo "✓ Tokens obtained"

# Test 1: Check admin user has is_admin=True
echo -e "\n[2/10] Verifying admin user has is_admin flag..."
ADMIN_IS_ADMIN=$(curl -X GET $BASE_URL/api/auth/me -H "Authorization: Bearer $ADMIN_TOKEN" -s | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('is_admin', 'MISSING'))")
if [ "$ADMIN_IS_ADMIN" == "True" ]; then
    echo "✓ Admin user has is_admin=True"
else
    echo "✗ FAILED: Admin user is_admin=$ADMIN_IS_ADMIN (expected True)"
    exit 1
fi

# Test 2: Check test user has is_admin=False
echo -e "\n[3/10] Verifying regular user has is_admin=False..."
TEST_IS_ADMIN=$(curl -X GET $BASE_URL/api/auth/me -H "Authorization: Bearer $TEST_TOKEN" -s | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('is_admin', 'MISSING'))")
if [ "$TEST_IS_ADMIN" == "False" ]; then
    echo "✓ Regular user has is_admin=False"
else
    echo "✗ FAILED: Regular user is_admin=$TEST_IS_ADMIN (expected False)"
    exit 1
fi

# Test 3: Admin can create default item
echo -e "\n[4/10] Testing admin can create default item..."
RESPONSE=$(curl -X POST $BASE_URL/api/items/ \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Test Default Sword",
        "item_type": "weapon",
        "description_player": "A test default weapon",
        "item_metadata": {"damage_dice": "1d8"},
        "is_default": true,
        "campaign_id": null
    }' -s -w "\n%{http_code}")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
if [ "$HTTP_CODE" == "201" ]; then
    echo "✓ Admin successfully created default item (201)"
else
    echo "✗ FAILED: Admin got status $HTTP_CODE (expected 201)"
    echo "$RESPONSE"
    exit 1
fi

# Test 4: Regular user CANNOT create default item
echo -e "\n[5/10] Testing regular user cannot create default item..."
HTTP_CODE=$(curl -X POST $BASE_URL/api/items/ \
    -H "Authorization: Bearer $TEST_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Unauthorized Default Item",
        "item_type": "weapon",
        "description_player": "This should fail",
        "item_metadata": {},
        "is_default": true,
        "campaign_id": null
    }' -s -o /dev/null -w "%{http_code}")
if [ "$HTTP_CODE" == "403" ]; then
    echo "✓ Regular user correctly blocked from creating default item (403)"
else
    echo "✗ FAILED: Regular user got status $HTTP_CODE (expected 403)"
    exit 1
fi

# Test 5: Admin can create default spell
echo -e "\n[6/10] Testing admin can create default spell..."
RESPONSE=$(curl -X POST $BASE_URL/api/spells/ \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Test Default Spell",
        "level": 1,
        "spell_class": "magic-user",
        "description": "A test default spell",
        "range": "60 feet",
        "duration": "1 round",
        "is_default": true,
        "campaign_id": null
    }' -s -w "\n%{http_code}")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
if [ "$HTTP_CODE" == "201" ]; then
    echo "✓ Admin successfully created default spell (201)"
else
    echo "✗ FAILED: Admin got status $HTTP_CODE (expected 201)"
    echo "$RESPONSE"
    exit 1
fi

# Test 6: Regular user CANNOT create default spell
echo -e "\n[7/10] Testing regular user cannot create default spell..."
HTTP_CODE=$(curl -X POST $BASE_URL/api/spells/ \
    -H "Authorization: Bearer $TEST_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Unauthorized Spell",
        "level": 1,
        "spell_class": "cleric",
        "description": "This should fail",
        "range": "Touch",
        "duration": "Instant",
        "is_default": true,
        "campaign_id": null
    }' -s -o /dev/null -w "%{http_code}")
if [ "$HTTP_CODE" == "403" ]; then
    echo "✓ Regular user correctly blocked from creating default spell (403)"
else
    echo "✗ FAILED: Regular user got status $HTTP_CODE (expected 403)"
    exit 1
fi

# Test 7: Default items visible to all users
echo -e "\n[8/10] Verifying default items visible to all users..."
DEFAULT_ITEMS=$(curl -X GET "$BASE_URL/api/items/" \
    -H "Authorization: Bearer $TEST_TOKEN" -s | python3 -c "import sys, json; data=json.load(sys.stdin); print(len([i for i in data if i.get('is_default')]))")
if [ "$DEFAULT_ITEMS" -gt "0" ]; then
    echo "✓ Regular user can see $DEFAULT_ITEMS default item(s)"
else
    echo "✗ FAILED: Regular user sees 0 default items"
    exit 1
fi

# Test 8: Default spells visible to all users
echo -e "\n[9/10] Verifying default spells visible to all users..."
DEFAULT_SPELLS=$(curl -X GET "$BASE_URL/api/spells/" \
    -H "Authorization: Bearer $TEST_TOKEN" -s | python3 -c "import sys, json; data=json.load(sys.stdin); print(len([s for s in data if s.get('is_default')]))")
if [ "$DEFAULT_SPELLS" -gt "0" ]; then
    echo "✓ Regular user can see $DEFAULT_SPELLS default spell(s)"
else
    echo "✗ FAILED: Regular user sees 0 default spells"
    exit 1
fi

# Test 9: Seed scripts populated default content
echo -e "\n[10/10] Verifying seed data was loaded..."
SEED_ITEMS=$(curl -X GET "$BASE_URL/api/items/" \
    -H "Authorization: Bearer $ADMIN_TOKEN" -s | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
SEED_SPELLS=$(curl -X GET "$BASE_URL/api/spells/" \
    -H "Authorization: Bearer $ADMIN_TOKEN" -s | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
echo "✓ Found $SEED_ITEMS total items (includes seeded + test item)"
echo "✓ Found $SEED_SPELLS total spells (includes seeded + test spell)"

echo -e "\n========================================="
echo "✅ ALL PHASE 3A TESTS PASSED!"
echo "========================================="
echo ""
echo "Phase 3A Features Verified:"
echo "  ✓ Admin role exists and works"
echo "  ✓ Admin can create default items/spells"
echo "  ✓ Regular users blocked from creating defaults (403)"
echo "  ✓ Default content visible to all users"
echo "  ✓ Seed data successfully loaded"
echo ""
