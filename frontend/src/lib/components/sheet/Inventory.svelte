<script>
  import { onMount, createEventDispatcher } from 'svelte';
  import { api } from '$lib/api.js';
  import Modal from '$lib/components/shared/Modal.svelte';
  import Badge from '$lib/components/shared/Badge.svelte';
  import { WEAPON_QUALITIES, itemTypeLabel, normalizeQualities } from '$lib/item-metadata.js';

  export let character;
  export let isGM = false;
  const dispatch = createEventDispatcher();

  let items = [];
  let loading = true;
  let error = '';

  // Add item modal
  let showAddModal = false;
  let availableItems = [];
  let searchQuery = '';
  let addingItem = null;
  let addQty = 1;

  // Off-hand choice modal
  let showSlotChoice = false;
  let slotChoiceEntry = null;

  // Container UI state
  let collapsedContainers = new Set();

  // Send modal
  let showSendModal = false;
  let sendEntry = null;
  let sendQty = 1;
  let sendDestination = null;
  let sending = false;

  // Destination data (fetched on modal open)
  let campaignVehicles = [];
  let characterAnimals = [];
  let characterPorters = [];

  // Currency (loaded from API)
  let currencyInstances = [];
  let currencyTotals = { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 };
  let currencyLoading = false;

  // Spend coins modal
  let showSpendModal = false;
  let spendAmounts = { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 };
  let spending = false;

  // Add coins modal (for GM adding treasure, etc.)
  let showAddCoinsModal = false;
  let addCoinAmounts = { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 };
  let addCoinContainerId = null;
  let addingCoins = false;

  // Send coins to treasury modal
  let showSendCoinsModal = false;
  let sendCoinAmounts = { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 };
  let sendingCoins = false;

  // Encumbrance
  const MAX_CARRY = 1600;
  const ENC_TABLE = [
    [400, 120], [600, 90], [800, 60], [1600, 30],
  ];

  // Denomination labels for display
  const DENOM_KEYS = ['pp', 'gp', 'ep', 'sp', 'cp'];
  const DENOM_LABELS = { pp: 'PP', gp: 'GP', ep: 'EP', sp: 'SP', cp: 'CP' };

  // Identify containers and dropped state
  $: containerEntries = items.filter(e => !e.stashed && (e.item?.item_metadata?.capacity ?? 0) > 0);
  $: droppedContainerIds = new Set(
    items.filter(e => e.dropped && (e.item?.item_metadata?.capacity ?? 0) > 0).map(e => e.instance_id)
  );

  // Items NOT in any container (and not themselves containers, not stashed, not currency)
  $: carriedItems = items.filter(e =>
    !e.stashed && !e.container_id && !(e.item?.item_metadata?.capacity > 0) && e.item?.item_type !== 'currency'
  );

  // Items at home base
  $: stashedItems = items.filter(e => e.stashed);

  // Build container groups — currency items inside containers are already counted as contents
  $: containerGroups = containerEntries.map(c => {
    const contents = items.filter(e => e.container_id === c.instance_id);
    let load = contents.reduce((sum, e) => {
      if (e.item?.item_type === 'currency') {
        const s = e.state || {};
        return sum + (s.cp || 0) + (s.sp || 0) + (s.ep || 0) + (s.gp || 0) + (s.pp || 0);
      }
      return sum + ((e.item?.weight ?? 0) * e.quantity);
    }, 0);
    const capacity = c.item.item_metadata.capacity;
    return { entry: c, contents, load, capacity };
  });

  // Encumbrance excluding dropped containers and their contents
  // Currency items have item.weight=0, so compute their weight from state
  $: itemWeight = items.reduce((sum, e) => {
    if (e.stashed) return sum;
    if (e.dropped) return sum;
    if (droppedContainerIds.has(e.container_id)) return sum;
    if (e.item?.item_type === 'currency') {
      const s = e.state || {};
      return sum + (s.cp || 0) + (s.sp || 0) + (s.ep || 0) + (s.gp || 0) + (s.pp || 0);
    }
    return sum + ((e.item?.weight ?? 0) * e.quantity);
  }, 0);
  $: encumbrance = Math.round(itemWeight);
  $: encMovement = ENC_TABLE.find(([t]) => encumbrance <= t)?.[1] ?? 0;
  $: encPct = Math.min(100, (encumbrance / MAX_CARRY) * 100);

  // Total coin weight for display (from currency totals)
  $: totalCoinWeight = (currencyTotals.cp || 0) + (currencyTotals.sp || 0) +
    (currencyTotals.ep || 0) + (currencyTotals.gp || 0) + (currencyTotals.pp || 0);

  // Non-zero denominations for summary display
  $: nonZeroDenoms = DENOM_KEYS.filter(k => (currencyTotals[k] || 0) > 0);

  const slotLabels = {
    'armor': 'Armor',
    'shield': 'Shield',
    'main-hand': 'Main Hand',
    'off-hand': 'Off-Hand',
    'ammo': 'Ammo',
  };

  onMount(async () => {
    await Promise.all([loadItems(), loadCurrency()]);
  });

  async function loadItems() {
    loading = true;
    try {
      items = await api.get(`/characters/${character.id}/inventory`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  // --- Currency API ---

  async function loadCurrency() {
    currencyLoading = true;
    try {
      const data = await api.get(`/characters/${character.id}/currency`);
      currencyInstances = data.instances;
      currencyTotals = data.totals;
    } catch {
      currencyInstances = [];
      currencyTotals = { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 };
    } finally {
      currencyLoading = false;
    }
  }

  async function spendCoins() {
    spending = true;
    try {
      await api.post(`/characters/${character.id}/currency/spend`, spendAmounts);
      await loadCurrency();
      await loadItems();
      showSpendModal = false;
      spendAmounts = { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 };
      dispatch('ac-changed');
    } catch (e) {
      alert(e.message);
    } finally {
      spending = false;
    }
  }

  async function addCoins() {
    addingCoins = true;
    try {
      const body = { ...addCoinAmounts };
      if (addCoinContainerId) body.container_id = addCoinContainerId;
      await api.post(`/characters/${character.id}/currency/add`, body);
      await loadCurrency();
      await loadItems();
      showAddCoinsModal = false;
      addCoinAmounts = { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 };
      addCoinContainerId = null;
      dispatch('ac-changed');
    } catch (e) {
      alert(e.message);
    } finally {
      addingCoins = false;
    }
  }

  async function sendCoinsToTreasury() {
    sendingCoins = true;
    try {
      await api.post(`/campaigns/${character.campaign_id}/treasury/return`, {
        character_id: character.id,
        ...sendCoinAmounts,
      });
      await loadCurrency();
      await loadItems();
      showSendCoinsModal = false;
      sendCoinAmounts = { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 };
      dispatch('ac-changed');
    } catch (e) {
      alert(e.message);
    } finally {
      sendingCoins = false;
    }
  }

  function openSpendModal() {
    spendAmounts = { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 };
    showSpendModal = true;
  }

  function openAddCoinsModal() {
    addCoinAmounts = { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 };
    addCoinContainerId = null;
    showAddCoinsModal = true;
  }

  function openSendCoinsModal() {
    sendCoinAmounts = { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 };
    showSendCoinsModal = true;
  }

  // Derive equipped items by slot
  $: equipped = {
    'armor': items.find(e => e.slot === 'armor') ?? null,
    'shield': items.find(e => e.slot === 'shield') ?? null,
    'main-hand': items.find(e => e.slot === 'main-hand') ?? null,
    'off-hand': items.find(e => e.slot === 'off-hand') ?? null,
    'ammo': items.find(e => e.slot === 'ammo') ?? null,
  };

  function itemStat(entry) {
    if (!entry) return '';
    const meta = entry.item.item_metadata ?? {};
    if (entry.slot === 'armor') return meta.ac != null ? `AC ${meta.ac}` : '';
    if (entry.slot === 'shield') return 'AC -1';
    if (meta.damage_dice) return meta.damage_dice;
    return '';
  }

  async function openAddModal() {
    showAddModal = true;
    searchQuery = '';
    try {
      availableItems = await api.get(
        `/items/?campaign_id=${character.campaign_id}&limit=100`
      );
    } catch {
      availableItems = [];
    }
  }

  $: filteredItems = availableItems.filter((i) =>
    i.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (i.unidentified_name && i.unidentified_name.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  async function assignItem(item) {
    addingItem = item.id;
    try {
      await api.post(`/items/${item.id}/assign`, {
        character_id: character.id,
        quantity: addQty,
      });
      await loadItems();
      showAddModal = false;
    } catch (e) {
      alert(e.message);
    } finally {
      addingItem = null;
    }
  }

  async function adjustQty(item, delta) {
    const current = item.quantity;
    const newQty = current + delta;
    if (newQty <= 0) {
      await removeItem(item);
      return;
    }
    try {
      await api.patch(`/characters/${character.id}/inventory/${item.instance_id}`, {
        quantity: newQty,
      });
      // Update locally to avoid full re-fetch and scroll jump
      item.quantity = newQty;
      items = items;
      // If this item is equipped (e.g. ammo), refresh character to recompute weapons
      if (item.slot) {
        dispatch('ac-changed');
      }
    } catch (e) {
      alert(e.message);
    }
  }

  async function removeItem(item) {
    try {
      await api.patch(`/characters/${character.id}/inventory/${item.instance_id}`, {
        quantity: 0,
      });
      await loadItems();
      await loadCurrency();
    } catch (e) {
      alert(e.message);
    }
  }

  async function equipItem(entry, slot) {
    try {
      const body = slot ? { slot } : {};
      items = await api.post(
        `/characters/${character.id}/inventory/${entry.instance_id}/equip`,
        body
      );
      dispatch('ac-changed');
    } catch (e) {
      alert(e.message);
    }
  }

  async function unequipItem(entry) {
    try {
      items = await api.post(
        `/characters/${character.id}/inventory/${entry.instance_id}/unequip`,
        {}
      );
      dispatch('ac-changed');
    } catch (e) {
      alert(e.message);
    }
  }

  function handleEquipClick(entry) {
    if (entry.item.item_type === 'ammo') {
      equipItem(entry);
    } else if (entry.item.item_type === 'weapon' && equipped['main-hand']) {
      slotChoiceEntry = entry;
      showSlotChoice = true;
    } else {
      equipItem(entry);
    }
  }

  function chooseSlot(slot) {
    if (slotChoiceEntry) {
      equipItem(slotChoiceEntry, slot);
    }
    showSlotChoice = false;
    slotChoiceEntry = null;
  }

  async function returnToStash(entry, qty = null) {
    try {
      await api.post(
        `/campaigns/${character.campaign_id}/stash/return`,
        { instance_id: entry.instance_id, character_id: character.id, quantity: qty ?? entry.quantity }
      );
      await loadItems();
      await loadCurrency();
      dispatch('ac-changed');
    } catch (e) {
      alert(e.message);
    }
  }

  async function identifyItem(entry) {
    try {
      await api.patch(`/characters/${character.id}/inventory/${entry.instance_id}/identify`);
      await loadItems();
      dispatch('ac-changed');
    } catch (e) {
      alert(e.message);
    }
  }

  async function toggleSecret(itemId, secretIndex, currentRevealed) {
    try {
      await api.patch(`/items/${itemId}/secrets/${secretIndex}`, {
        revealed: !currentRevealed,
      });
      await loadItems();
    } catch (e) {
      alert(e.message);
    }
  }

  // --- Stash (home base) ---
  async function stashItem(entry) {
    try {
      items = await api.post(
        `/characters/${character.id}/inventory/${entry.instance_id}/stash`,
        { stashed: true }
      );
      await loadCurrency();
      dispatch('ac-changed');
    } catch (e) {
      alert(e.message);
    }
  }

  async function retrieveItem(entry) {
    try {
      items = await api.post(
        `/characters/${character.id}/inventory/${entry.instance_id}/stash`,
        { stashed: false }
      );
      await loadCurrency();
      dispatch('ac-changed');
    } catch (e) {
      alert(e.message);
    }
  }

  // --- Container functions ---

  async function moveItem(entry, containerInstanceId) {
    try {
      items = await api.post(
        `/characters/${character.id}/inventory/${entry.instance_id}/move`,
        { container_id: containerInstanceId }
      );
    } catch (e) {
      alert(e.message);
    }
  }

  async function toggleDrop(containerEntry) {
    try {
      items = await api.post(
        `/characters/${character.id}/inventory/${containerEntry.instance_id}/drop`,
        { dropped: !containerEntry.dropped }
      );
      dispatch('ac-changed');
    } catch (e) {
      alert(e.message);
    }
  }

  function toggleCollapse(containerId) {
    if (collapsedContainers.has(containerId)) {
      collapsedContainers.delete(containerId);
    } else {
      collapsedContainers.add(containerId);
    }
    collapsedContainers = collapsedContainers;
  }

  function containerMoveTargets(entry) {
    // Build list of move targets: "Carried" + each non-dropped container (excluding current)
    const targets = [{ id: null, label: 'Carried', full: false }];
    for (const cg of containerGroups) {
      if (cg.entry.instance_id === entry.container_id) continue; // already here
      if (cg.entry.dropped) continue; // can't put items in dropped containers
      const itemWt = (entry.item?.weight ?? 0) * entry.quantity;
      const wouldExceed = cg.load + itemWt > cg.capacity;
      targets.push({
        id: cg.entry.instance_id,
        label: `${cg.entry.item.name} (${Math.round(cg.load)}/${cg.capacity})`,
        full: wouldExceed,
      });
    }
    return targets;
  }

  function isInDroppedContainer(entry) {
    return entry.container_id != null && droppedContainerIds.has(entry.container_id);
  }

  function fillPct(load, capacity) {
    return capacity > 0 ? Math.min(100, (load / capacity) * 100) : 0;
  }

  // --- Fillable item functions ---

  const FILL_STATES = ['full', 'half', 'empty'];
  const FILL_ICONS = { full: '\u25CF', half: '\u25D1', empty: '\u25CB' };
  const FILL_COLORS = { full: 'text-blue-700', half: 'text-blue-400', empty: 'text-ink-faint' };

  function isFillable(entry) {
    return !!(entry.item?.item_metadata?.fillable);
  }

  function getFill(entry) {
    return entry.state?.fill ?? 'empty';
  }

  function getContents(entry) {
    return entry.state?.contents ?? '';
  }

  async function cycleFill(entry) {
    const current = getFill(entry);
    const idx = FILL_STATES.indexOf(current);
    const next = FILL_STATES[(idx + 1) % FILL_STATES.length];
    try {
      const updated = await api.patch(
        `/characters/${character.id}/inventory/${entry.instance_id}/state`,
        { state: { fill: next } }
      );
      entry.state = updated.state;
      items = items;
    } catch (e) {
      alert(e.message);
    }
  }

  function getAppraisedValue(entry) {
    return entry.state?.appraised_value ?? null;
  }

  function getTreasureMaterial(entry) {
    return entry.state?.material ?? null;
  }

  function getTreasureDescription(entry) {
    return entry.state?.description ?? null;
  }

  async function saveAppraisedValue(entry, value) {
    const numVal = value === '' ? null : parseFloat(value);
    try {
      const updated = await api.patch(
        `/characters/${character.id}/inventory/${entry.instance_id}/state`,
        { state: { appraised_value: numVal } }
      );
      entry.state = updated.state;
      items = items;
    } catch (e) {
      alert(e.message);
    }
  }

  async function saveTreasureField(entry, field, value) {
    const trimmed = value.trim() || null;
    try {
      const updated = await api.patch(
        `/characters/${character.id}/inventory/${entry.instance_id}/state`,
        { state: { [field]: trimmed } }
      );
      entry.state = updated.state;
      items = items;
    } catch (e) {
      alert(e.message);
    }
  }

  async function saveContents(entry, value) {
    try {
      const updated = await api.patch(
        `/characters/${character.id}/inventory/${entry.instance_id}/state`,
        { state: { contents: value } }
      );
      entry.state = updated.state;
      items = items;
    } catch (e) {
      alert(e.message);
    }
  }

  // --- Split / Merge ---

  async function splitStack(entry) {
    const max = entry.quantity - 1;
    const input = prompt(`Split how many from stack of ${entry.quantity}? (1–${max})`);
    if (input == null) return;
    const qty = parseInt(input, 10);
    if (isNaN(qty) || qty < 1 || qty > max) {
      alert(`Invalid quantity. Must be between 1 and ${max}.`);
      return;
    }
    try {
      items = await api.post(
        `/characters/${character.id}/inventory/${entry.instance_id}/split`,
        { quantity: qty }
      );
    } catch (e) {
      alert(e.message);
    }
  }

  function mergeTargets(entry) {
    // Find other stacks of the same item with identical state
    // (blocks merging gems/treasures with different value, material, etc.)
    return items.filter(e =>
      e.instance_id !== entry.instance_id &&
      e.item.id === entry.item.id &&
      JSON.stringify(e.state ?? {}) === JSON.stringify(entry.state ?? {})
    );
  }

  async function mergeStack(sourceEntry, targetEntry) {
    try {
      items = await api.post(
        `/characters/${character.id}/inventory/merge`,
        { source_id: sourceEntry.instance_id, target_id: targetEntry.instance_id }
      );
    } catch (e) {
      alert(e.message);
    }
  }

  // --- Send modal ---

  $: sendIsContainer = sendEntry && (sendEntry.item?.item_metadata?.capacity ?? 0) > 0;

  async function openSendModal(entry) {
    sendEntry = entry;
    sendQty = entry.quantity;
    sendDestination = null;
    sending = false;
    showSendModal = true;

    // Fetch destinations in parallel
    try {
      const [vehicles, animals] = await Promise.all([
        character.campaign_id
          ? api.get(`/campaigns/${character.campaign_id}/vehicles?campaign_id=${character.campaign_id}`)
          : Promise.resolve([]),
        api.get(`/characters/${character.id}/animals`),
      ]);
      campaignVehicles = vehicles;
      characterAnimals = animals.filter(a => (a.container_capacity ?? 0) > 0);
    } catch {
      campaignVehicles = [];
      characterAnimals = [];
    }

    // Derive porters from character specialists
    characterPorters = (character.specialists ?? []).filter(s => s.spec_type === 'porter');
  }

  async function executeSend() {
    if (!sendDestination || !sendEntry) return;
    sending = true;
    try {
      if (sendDestination === 'home') {
        await stashItem(sendEntry);
      } else if (sendDestination === 'party') {
        await returnToStash(sendEntry, sendQty);
      } else if (sendDestination.startsWith('vehicle:')) {
        const vehicleId = parseInt(sendDestination.split(':')[1]);
        await api.post(
          `/campaigns/${character.campaign_id}/vehicles/${vehicleId}/cargo/0/return`,
          { character_id: character.id, instance_id: sendEntry.instance_id, quantity: sendQty }
        );
        await loadItems();
        await loadCurrency();
      } else if (sendDestination.startsWith('animal:')) {
        const animalId = parseInt(sendDestination.split(':')[1]);
        await api.post(
          `/characters/${character.id}/animals/${animalId}/load`,
          { instance_id: sendEntry.instance_id, quantity: sendQty }
        );
        await loadItems();
        await loadCurrency();
      }
      showSendModal = false;
    } catch (e) {
      alert(e.message);
    } finally {
      sending = false;
    }
  }

  // --- Currency pile helpers ---

  function pileWeight(inst) {
    const s = inst.state || {};
    return (s.cp || 0) + (s.sp || 0) + (s.ep || 0) + (s.gp || 0) + (s.pp || 0);
  }

  function pileSummary(state) {
    const s = state || {};
    const parts = [];
    for (const k of DENOM_KEYS) {
      if (s[k]) parts.push(`${s[k]} ${DENOM_LABELS[k]}`);
    }
    return parts.join(', ') || 'Empty';
  }
</script>

<div class="space-y-6">
  <!-- Equipment Summary -->
  {#if !loading && items.length > 0}
    <div class="panel">
      <h2 class="section-title">Equipment</h2>
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {#each ['armor', 'shield', 'main-hand', 'off-hand', 'ammo'] as slot}
          <div class="text-center">
            <div class="text-xs text-ink-faint uppercase tracking-wide">{slotLabels[slot]}</div>
            {#if equipped[slot]}
              <div class="text-sm font-medium text-ink">{equipped[slot].item.name}</div>
              {#if itemStat(equipped[slot])}
                <div class="text-xs text-ink-faint">{itemStat(equipped[slot])}</div>
              {/if}
            {:else}
              <div class="text-sm text-ink-faint">— None —</div>
            {/if}
          </div>
        {/each}
      </div>
    </div>
  {/if}

  <!-- Currency -->
  <div class="panel">
    <h2 class="section-title">Currency</h2>

    {#if currencyLoading}
      <p class="text-ink-faint text-sm">Loading...</p>
    {:else}
      <!-- Totals summary -->
      <div class="flex flex-wrap items-center gap-3 mb-2">
        {#if nonZeroDenoms.length > 0}
          {#each nonZeroDenoms as k}
            <span class="text-sm font-medium text-ink">
              {currencyTotals[k].toLocaleString()} <span class="text-xs text-ink-faint">{DENOM_LABELS[k]}</span>
            </span>
          {/each}
        {:else}
          <span class="text-sm text-ink-faint">No coins</span>
        {/if}
        {#if totalCoinWeight > 0}
          <span class="text-xs text-ink-faint ml-auto">({totalCoinWeight.toLocaleString()} cn)</span>
        {/if}
      </div>

      <!-- Action buttons -->
      <div class="flex flex-wrap gap-2 mb-3">
        {#if totalCoinWeight > 0}
          <button class="btn text-xs" on:click={openSpendModal}>Spend</button>
        {/if}
        {#if isGM}
          <button class="btn text-xs" on:click={openAddCoinsModal}>+ Add Coins</button>
        {/if}
        {#if totalCoinWeight > 0 && character.campaign_id}
          <button class="btn-ghost text-xs" on:click={openSendCoinsModal} title="Send coins to party treasury">
            Send to Treasury
          </button>
        {/if}
      </div>

      <!-- Individual currency piles -->
      {#if currencyInstances.length > 0}
        <div class="border-t border-parchment-200 pt-2 space-y-1.5">
          <div class="text-xs text-ink-faint uppercase tracking-wide">Coin Piles</div>
          {#each currencyInstances as inst (inst.instance_id)}
            <div class="flex items-center justify-between text-sm border-b border-parchment-100 pb-1 last:border-0">
              <div class="flex-1 min-w-0">
                <span class="text-ink">{pileSummary(inst.state)}</span>
                {#if inst.container_name}
                  <span class="text-xs text-ink-faint ml-1">in {inst.container_name}</span>
                {/if}
                {#if inst.stashed}
                  <Badge label="Stashed" />
                {/if}
              </div>
              <span class="text-xs text-ink-faint shrink-0">{pileWeight(inst)} cn</span>
            </div>
          {/each}
        </div>
      {/if}
    {/if}
  </div>

  <!-- Inventory list -->
  <div class="panel">
    <div class="flex items-center justify-between mb-2">
      <h2 class="section-title mb-0 border-none">Inventory</h2>
      <button class="btn text-xs" on:click={openAddModal}>+ Add Item</button>
    </div>

    <!-- Encumbrance bar -->
    <div class="mb-4">
      <div class="flex justify-between text-xs text-ink-faint mb-1">
        <span>Encumbrance: <span class="text-ink font-medium">{encumbrance}</span> / {MAX_CARRY} coins</span>
        <span>Move: <span class="text-ink font-medium">{encMovement}' ({Math.floor(encMovement / 3)}')</span></span>
      </div>
      <div class="w-full h-2 bg-parchment-200 rounded overflow-hidden">
        <div
          class="h-full rounded transition-all duration-300"
          class:bg-green-600={encPct <= 25}
          class:bg-yellow-600={encPct > 25 && encPct <= 50}
          class:bg-orange-600={encPct > 50 && encPct <= 75}
          class:bg-red-700={encPct > 75}
          style="width: {encPct}%"
        ></div>
      </div>
    </div>

    {#if loading}
      <p class="text-ink-faint text-sm">Loading...</p>
    {:else if error}
      <p class="text-red-700 text-sm">{error}</p>
    {:else if items.length === 0}
      <p class="text-ink-faint text-sm text-center py-4">No items in inventory.</p>
    {:else}
      <!-- Carried items (not in any container, not containers themselves, not currency) -->
      {#if carriedItems.length > 0}
        <div class="mb-4">
          <div class="text-xs text-ink-faint uppercase tracking-wide mb-2">Carried</div>
          <div class="space-y-2">
            {#each carriedItems as entry (entry.instance_id)}
              {@render itemRow(entry)}
            {/each}
          </div>
        </div>
      {/if}

      <!-- Container sections -->
      {#each containerGroups as cg (cg.entry.instance_id)}
        {@const pct = fillPct(cg.load, cg.capacity)}
        {@const isDropped = cg.entry.dropped}
        {@const isCollapsed = collapsedContainers.has(cg.entry.instance_id)}
        {@const nonCurrencyContents = cg.contents.filter(e => e.item?.item_type !== 'currency')}
        {@const currencyContents = cg.contents.filter(e => e.item?.item_type === 'currency')}
        <div class="mb-4 border border-parchment-200 rounded-sm" class:opacity-50={isDropped}>
          <!-- Container header -->
          <div class="flex items-center gap-2 px-3 py-2 bg-parchment-100/50">
            <button
              class="text-ink-faint text-xs w-4 shrink-0"
              on:click={() => toggleCollapse(cg.entry.instance_id)}
              title={isCollapsed ? 'Expand' : 'Collapse'}
            >{isCollapsed ? '\u25B6' : '\u25BC'}</button>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="text-sm font-medium text-ink">{cg.entry.item.name}</span>
                <span class="text-xs text-ink-faint">{Math.round(cg.load)} / {cg.capacity} cn</span>
                {#if isDropped}
                  <Badge label="Dropped" />
                {/if}
              </div>
              <!-- Fullness meter -->
              <div class="w-full h-1.5 bg-parchment-200 rounded overflow-hidden mt-1">
                <div
                  class="h-full rounded transition-all duration-300"
                  class:bg-green-600={pct <= 50}
                  class:bg-yellow-600={pct > 50 && pct <= 75}
                  class:bg-orange-600={pct > 75 && pct <= 90}
                  class:bg-red-700={pct > 90}
                  style="width: {pct}%"
                ></div>
              </div>
            </div>
            <div class="flex items-center gap-1 shrink-0">
              <button
                class="text-xs px-2 py-0.5 rounded border transition-colors {isDropped
                  ? 'border-green-700 text-green-800 hover:bg-green-50'
                  : 'border-red-700 text-red-800 hover:bg-red-50'}"
                on:click={() => toggleDrop(cg.entry)}
              >{isDropped ? 'Pick Up' : 'Drop'}</button>
              <button
                class="btn-ghost text-xs px-1.5 py-0.5"
                on:click={() => adjustQty(cg.entry, -1)}
              >−</button>
              <span class="text-sm text-ink w-6 text-center">{cg.entry.quantity}</span>
              <button
                class="btn-ghost text-xs px-1.5 py-0.5"
                on:click={() => adjustQty(cg.entry, 1)}
              >+</button>
              <button
                class="btn-ghost text-xs px-1.5 py-0.5"
                on:click={() => openSendModal(cg.entry)}
                title="Send to another location"
              >Send</button>
              {#if cg.contents.length === 0}
                <button
                  class="btn-danger text-xs px-1.5 py-0.5 ml-1"
                  on:click={() => removeItem(cg.entry)}
                >✕</button>
              {/if}
            </div>
          </div>
          <!-- Container contents -->
          {#if !isCollapsed}
            <div class="px-3 py-2 space-y-2">
              {#if currencyContents.length > 0}
                {#each currencyContents as ce (ce.instance_id)}
                  <div class="flex items-center justify-between text-sm border-b border-parchment-200 pb-2">
                    <span class="text-ink-faint italic">Currency: {pileSummary(ce.state)}</span>
                    <span class="text-xs text-ink-faint">{pileWeight(ce)} cn</span>
                  </div>
                {/each}
              {/if}
              {#if nonCurrencyContents.length === 0 && currencyContents.length === 0}
                <p class="text-ink-faint text-xs text-center py-2">Empty</p>
              {:else}
                {#each nonCurrencyContents as entry (entry.instance_id)}
                  {@render itemRow(entry)}
                {/each}
              {/if}
            </div>
          {/if}
        </div>
      {/each}
    {/if}
  </div>

  <!-- Home Base (stashed items) -->
  {#if stashedItems.length > 0}
    <div class="mt-4 pt-4 border-t border-parchment-200">
      <h3 class="text-xs text-ink-faint uppercase tracking-wide mb-2">Home Base ({stashedItems.length} items)</h3>
      <div class="space-y-2 opacity-75">
        {#each stashedItems as entry (entry.instance_id)}
          {@render itemRow(entry)}
        {/each}
      </div>
    </div>
  {/if}
</div>

{#snippet itemRow(entry)}
  <div class="flex items-start gap-3 border-b border-parchment-200 pb-2 last:border-0">
    <div class="flex-1 min-w-0">
      <div class="flex items-center gap-2">
        {#if isGM && !entry.identified && entry.item.unidentified_name}
          <span class="text-sm text-ink" class:font-bold={entry.slot}>
            {entry.item.unidentified_name}
            <span class="text-ink-faint">({entry.item.name})</span>
          </span>
        {:else}
          <span class="text-sm text-ink" class:font-bold={entry.slot}>{entry.item.name}</span>
        {/if}
        {#if entry.slot}
          <Badge label={slotLabels[entry.slot] ?? entry.slot} />
        {/if}
        {#if !entry.identified && (entry.item.unidentified_name || (isGM && entry.item.unidentified_name))}
          <Badge label="Unidentified" variant="gm" />
        {/if}
        {#if isFillable(entry)}
          {@const fill = getFill(entry)}
          {@const contents = getContents(entry)}
          <button
            class="text-sm cursor-pointer {FILL_COLORS[fill]}"
            on:click={() => cycleFill(entry)}
            title="{fill}{contents ? ` — ${contents}` : ''} (click to cycle)"
          >{FILL_ICONS[fill]}</button>
          <span class="text-xs text-ink-faint italic">
            {#if contents}{contents}, {/if}{fill}
          </span>
        {/if}
      </div>
      {#if isFillable(entry)}
        <div class="flex items-center gap-1 mt-0.5">
          <input
            class="input text-xs py-0 px-1 w-28"
            type="text"
            placeholder="Contents..."
            value={getContents(entry)}
            on:blur={(e) => saveContents(entry, e.target.value)}
            on:keydown={(e) => e.key === 'Enter' && e.target.blur()}
          />
        </div>
      {/if}
      {#if entry.item.description_player}
        <div class="text-xs text-ink-faint mt-0.5">{entry.item.description_player}</div>
      {/if}
      <div class="text-xs text-ink-faint">
        {itemTypeLabel(entry.item)}
        {#if entry.item.weight}
          <span class="ml-1">{entry.item.weight} cn</span>
        {/if}
        {#if getTreasureMaterial(entry)}
          <span class="ml-1 text-amber-800">({getTreasureMaterial(entry)})</span>
        {/if}
        {#if getAppraisedValue(entry) != null}
          <span class="ml-1 text-amber-700">{getAppraisedValue(entry).toLocaleString()} gp</span>
        {/if}
        {#if getTreasureDescription(entry)}
          <span class="ml-1 italic">&mdash; {getTreasureDescription(entry)}</span>
        {/if}
        {#if entry.state?.scroll_spells?.length}
          <div class="text-xs text-violet-700 mt-0.5">
            Contains: {entry.state.scroll_spells.map(s => `${s.name} (L${s.level})`).join(', ')}
          </div>
        {/if}
        {#if normalizeQualities(entry.item.item_metadata?.qualities).length}
          <span class="ml-1">
            {#each normalizeQualities(entry.item.item_metadata?.qualities) as q}
              <span
                class="inline-block px-1 rounded bg-parchment-200 text-ink-faint ml-0.5"
                title={WEAPON_QUALITIES[q] ?? ''}
              >{q}</span>
            {/each}
          </span>
        {/if}
      </div>
      {#if entry.item.item_metadata?.onset || entry.item.item_metadata?.effect_failed}
        <div class="text-xs text-ink-faint">
          {#if entry.item.item_metadata.onset}<span>Onset: {entry.item.item_metadata.onset}</span>{/if}
          {#if entry.item.item_metadata.effect_failed}<span class="ml-2">Fail: {entry.item.item_metadata.effect_failed}</span>{/if}
          {#if entry.item.item_metadata.save != null}<span class="ml-2">Save: {entry.item.item_metadata.save}+</span>{/if}
        </div>
      {/if}
      {#if entry.item.item_type === 'treasure' && isGM}
        <div class="flex flex-wrap items-center gap-x-3 gap-y-1 mt-0.5">
          <div class="flex items-center gap-1">
            <span class="text-xs text-ink-faint">Value:</span>
            <input
              class="input text-xs py-0 px-1 w-20"
              type="number"
              step="any"
              placeholder="gp"
              value={getAppraisedValue(entry) ?? ''}
              on:blur={(e) => saveAppraisedValue(entry, e.target.value)}
              on:keydown={(e) => e.key === 'Enter' && e.target.blur()}
            />
            <span class="text-xs text-ink-faint">gp</span>
          </div>
          <div class="flex items-center gap-1">
            <span class="text-xs text-ink-faint">Material:</span>
            <input
              class="input text-xs py-0 px-1 w-24"
              type="text"
              placeholder="Ruby, Gold..."
              value={getTreasureMaterial(entry) ?? ''}
              on:blur={(e) => saveTreasureField(entry, 'material', e.target.value)}
              on:keydown={(e) => e.key === 'Enter' && e.target.blur()}
            />
          </div>
          <div class="flex items-center gap-1">
            <span class="text-xs text-ink-faint">Desc:</span>
            <input
              class="input text-xs py-0 px-1 w-44"
              type="text"
              placeholder="A bust of Stefan Karameikos..."
              value={getTreasureDescription(entry) ?? ''}
              on:blur={(e) => saveTreasureField(entry, 'description', e.target.value)}
              on:keydown={(e) => e.key === 'Enter' && e.target.blur()}
            />
          </div>
        </div>
      {/if}
      {#if isGM && entry.item.secrets?.length}
        <div class="mt-1 space-y-0.5">
          {#each entry.item.secrets as secret, idx}
            <div class="flex items-center gap-1.5 text-xs">
              <button
                class="shrink-0 w-5 h-5 flex items-center justify-center rounded border {secret.revealed ? 'border-green-600 text-green-700 bg-green-50' : 'border-ink-faint text-ink-faint bg-parchment-100'}"
                title={secret.revealed ? 'Click to hide from players' : 'Click to reveal to players'}
                on:click={() => toggleSecret(entry.item.id, idx, secret.revealed)}
              >
                {secret.revealed ? '&#x1f441;' : '&#x2022;'}
              </button>
              <span class="italic {secret.revealed ? 'text-ink' : 'text-ink-faint'}">{secret.text}</span>
            </div>
          {/each}
        </div>
      {:else if !isGM && entry.item.revealed_secrets?.length}
        {#each entry.item.revealed_secrets as secret}
          <div class="text-xs text-ink-faint mt-0.5 italic">{secret}</div>
        {/each}
      {/if}
      {#if isGM && entry.item.description_gm}
        <div class="text-xs text-amber-700 mt-0.5">{entry.item.description_gm}</div>
      {/if}
    </div>
    <div class="flex items-center gap-1 shrink-0">
      {#if isGM && !entry.identified && entry.item.unidentified_name}
        <button
          class="btn text-xs px-1.5 py-0.5"
          on:click={() => identifyItem(entry)}
          title="Identify this item"
        >Identify</button>
      {/if}
      {#if entry.item.equippable && !isInDroppedContainer(entry)}
        {#if entry.slot}
          <button
            class="btn-ghost text-xs px-1.5 py-0.5"
            on:click={() => unequipItem(entry)}
            title="Unequip"
          >Unequip</button>
        {:else}
          <button
            class="btn text-xs px-1.5 py-0.5"
            on:click={() => handleEquipClick(entry)}
            title="Equip"
          >Equip</button>
        {/if}
      {/if}
      <!-- Move to container dropdown -->
      {#if containerEntries.length > 0 && !entry.slot && !(entry.item?.item_metadata?.capacity > 0)}
        {@const targets = containerMoveTargets(entry)}
        <select
          class="input text-xs py-0.5 px-1 w-20"
          value={entry.container_id ?? ''}
          on:change={(e) => moveItem(entry, e.target.value === '' ? null : parseInt(e.target.value))}
        >
          {#each targets as t}
            <option value={t.id ?? ''} disabled={t.full}>{t.label}</option>
          {/each}
        </select>
      {/if}
      <!-- Split button (stacks > 1) -->
      {#if entry.quantity > 1}
        <button
          class="btn-ghost text-xs px-1.5 py-0.5"
          on:click={() => splitStack(entry)}
          title="Split stack"
        >Split</button>
      {/if}
      <!-- Merge button (other stacks of same item exist) -->
      {#if mergeTargets(entry).length > 0}
        {@const mTargets = mergeTargets(entry)}
        {#if mTargets.length === 1}
          <button
            class="btn-ghost text-xs px-1.5 py-0.5"
            on:click={() => mergeStack(entry, mTargets[0])}
            title="Merge into other stack"
          >Merge</button>
        {:else}
          <select
            class="input text-xs py-0.5 px-1 w-20"
            value=""
            on:change={(e) => {
              const tid = parseInt(e.target.value);
              const target = mTargets.find(t => t.instance_id === tid);
              if (target) mergeStack(entry, target);
              e.target.value = '';
            }}
          >
            <option value="" disabled>Merge...</option>
            {#each mTargets as t}
              <option value={t.instance_id}>x{t.quantity}{t.container_id ? ' (in container)' : ''}{t.stashed ? ' (home)' : ''}</option>
            {/each}
          </select>
        {/if}
      {/if}
      <button
        class="btn-ghost text-xs px-1.5 py-0.5"
        on:click={() => adjustQty(entry, -1)}
      >−</button>
      <span class="text-sm text-ink w-6 text-center">{entry.quantity}</span>
      <button
        class="btn-ghost text-xs px-1.5 py-0.5"
        on:click={() => adjustQty(entry, 1)}
      >+</button>
      {#if !entry.stashed}
        <button
          class="btn-ghost text-xs px-1.5 py-0.5"
          on:click={() => openSendModal(entry)}
          title="Send to another location"
        >Send</button>
      {:else}
        <button
          class="btn text-xs px-1.5 py-0.5"
          on:click={() => retrieveItem(entry)}
          title="Retrieve from home base"
        >Retrieve</button>
      {/if}
      <button
        class="btn-danger text-xs px-1.5 py-0.5 ml-1"
        on:click={() => removeItem(entry)}
      >✕</button>
    </div>
  </div>
{/snippet}

<!-- Add Item Modal -->
<Modal bind:open={showAddModal} title="Add Item">
  <div class="space-y-3">
    <input
      class="input w-full"
      type="text"
      placeholder="Search items..."
      bind:value={searchQuery}
    />
    <div class="flex items-center gap-2">
      <label class="text-xs text-ink" for="add-qty">Quantity</label>
      <input id="add-qty" class="input w-16" type="number" min="1" bind:value={addQty} />
    </div>
    <div class="space-y-1 max-h-60 overflow-y-auto">
      {#each filteredItems as item}
        <button
          class="w-full text-left panel py-2 px-3 hover:bg-parchment-100 transition-colors"
          on:click={() => assignItem(item)}
          disabled={addingItem === item.id}
        >
          <div class="text-sm font-medium text-ink">
            {item.name}
            {#if item.unidentified_name}
              <span class="font-normal text-ink-faint">({item.unidentified_name})</span>
            {/if}
          </div>
          <div class="text-xs text-ink-faint">
            {itemTypeLabel(item)}
            {#if normalizeQualities(item.item_metadata?.qualities).length}
              <span class="ml-1">
                {#each normalizeQualities(item.item_metadata?.qualities) as q}
                  <span
                    class="inline-block px-1 rounded bg-parchment-200 text-ink-faint ml-0.5"
                    title={WEAPON_QUALITIES[q] ?? ''}
                  >{q}</span>
                {/each}
              </span>
            {/if}
          </div>
        </button>
      {:else}
        <p class="text-ink-faint text-sm text-center py-4">No items found.</p>
      {/each}
    </div>
  </div>
</Modal>

<!-- Weapon Slot Choice Modal -->
<Modal bind:open={showSlotChoice} title="Choose Weapon Slot">
  <div class="space-y-3">
    <p class="text-sm text-ink">Where do you want to equip this weapon?</p>
    <div class="flex gap-3">
      <button class="btn flex-1" on:click={() => chooseSlot('main-hand')}>
        Main Hand
      </button>
      <button class="btn flex-1" on:click={() => chooseSlot('off-hand')}>
        Off-Hand
      </button>
    </div>
  </div>
</Modal>

<!-- Send Item Modal -->
<Modal bind:open={showSendModal} title="Send Item">
  {#if sendEntry}
    <!-- Item info header -->
    <div class="mb-4">
      <div class="text-sm font-medium text-ink">{sendEntry.item.name}</div>
      <div class="text-xs text-ink-faint">Available: {sendEntry.quantity}</div>
    </div>

    <!-- Quantity (only show for stacks > 1) -->
    {#if sendEntry.quantity > 1}
      <div class="flex items-center gap-2 mb-4">
        <label class="text-xs text-ink" for="send-qty">Quantity</label>
        <input id="send-qty" class="input w-20" type="number" min="1" max={sendEntry.quantity} bind:value={sendQty} />
      </div>
    {/if}

    <!-- Destinations -->
    <div class="space-y-1">
      <h4 class="text-xs text-ink-faint uppercase tracking-wide mb-2">Destination</h4>

      <!-- Home Base -->
      <button
        class="w-full text-left panel py-2 px-3 transition-colors {sendDestination === 'home' ? 'bg-parchment-200 ring-1 ring-ink/20' : 'hover:bg-parchment-100'}"
        on:click={() => sendDestination = 'home'}
        disabled={sendEntry.stashed}
      >
        <div class="text-sm text-ink">Home Base</div>
        <div class="text-xs text-ink-faint">Store at home — doesn't count toward encumbrance</div>
      </button>

      <!-- Party Stash -->
      <button
        class="w-full text-left panel py-2 px-3 transition-colors {sendDestination === 'party' ? 'bg-parchment-200 ring-1 ring-ink/20' : 'hover:bg-parchment-100'}"
        on:click={() => sendDestination = 'party'}
      >
        <div class="text-sm text-ink">Party Stash</div>
        <div class="text-xs text-ink-faint">Shared party loot pool</div>
      </button>

      <!-- Vehicles (hidden for containers) -->
      {#if !sendIsContainer}
        {#each campaignVehicles as v}
          {@const remaining = v.cargo_capacity - v.cargo_weight}
          <button
            class="w-full text-left panel py-2 px-3 transition-colors {sendDestination === `vehicle:${v.id}` ? 'bg-parchment-200 ring-1 ring-ink/20' : 'hover:bg-parchment-100'}"
            on:click={() => sendDestination = `vehicle:${v.id}`}
          >
            <div class="text-sm text-ink">{v.name}</div>
            <div class="text-xs text-ink-faint">{v.base_type} — {remaining} cn free of {v.cargo_capacity}</div>
          </button>
        {/each}
      {/if}

      <!-- Animals with packs (hidden for containers) -->
      {#if !sendIsContainer}
        {#each characterAnimals as a}
          {@const remaining = a.container_capacity - a.current_load}
          <button
            class="w-full text-left panel py-2 px-3 transition-colors {sendDestination === `animal:${a.id}` ? 'bg-parchment-200 ring-1 ring-ink/20' : 'hover:bg-parchment-100'}"
            on:click={() => sendDestination = `animal:${a.id}`}
          >
            <div class="text-sm text-ink">{a.name}</div>
            <div class="text-xs text-ink-faint">{a.animal_type} — {remaining} cn free of {a.container_capacity}</div>
          </button>
        {/each}
      {/if}

      <!-- Porters (grayed, coming soon) -->
      {#each characterPorters as p}
        <div class="w-full text-left panel py-2 px-3 opacity-50 cursor-not-allowed">
          <div class="text-sm text-ink-faint">Porter — {p.task || 'idle'}</div>
          <div class="text-xs text-ink-faint">Coming soon</div>
        </div>
      {/each}
    </div>

    <!-- Send button -->
    <button
      class="btn w-full mt-4"
      on:click={executeSend}
      disabled={!sendDestination || sending}
    >
      {sending ? 'Sending...' : 'Send'}
    </button>
  {/if}
</Modal>

<!-- Spend Coins Modal -->
<Modal bind:open={showSpendModal} title="Spend Coins">
  <div class="space-y-4">
    <p class="text-sm text-ink-faint">Spend coins from {character.name}'s purse. The server will deduct from available piles automatically.</p>
    <div class="flex flex-wrap gap-3">
      {#each DENOM_KEYS as k}
        {@const available = currencyTotals[k] || 0}
        <div class="flex flex-col items-center">
          <label class="text-[10px] text-ink-faint uppercase" for="spend-{k}">{DENOM_LABELS[k]}</label>
          <input
            id="spend-{k}"
            class="input w-16 text-center"
            type="number"
            min="0"
            max={available}
            bind:value={spendAmounts[k]}
          />
          <span class="text-[10px] text-ink-faint">/ {available}</span>
        </div>
      {/each}
    </div>
    <button
      class="btn w-full"
      on:click={spendCoins}
      disabled={spending || Object.values(spendAmounts).every(v => !v)}
    >
      {spending ? 'Spending...' : 'Spend'}
    </button>
  </div>
</Modal>

<!-- Add Coins Modal (GM) -->
<Modal bind:open={showAddCoinsModal} title="Add Coins">
  <div class="space-y-4">
    <p class="text-sm text-ink-faint">Add coins to {character.name}'s inventory.</p>
    <div class="flex flex-wrap gap-3">
      {#each DENOM_KEYS as k}
        <div class="flex flex-col items-center">
          <label class="text-[10px] text-ink-faint uppercase" for="add-coin-{k}">{DENOM_LABELS[k]}</label>
          <input
            id="add-coin-{k}"
            class="input w-16 text-center"
            type="number"
            min="0"
            bind:value={addCoinAmounts[k]}
          />
        </div>
      {/each}
    </div>
    {#if containerEntries.length > 0}
      <div class="flex items-center gap-2">
        <span class="text-xs text-ink-faint">Put in:</span>
        <select
          class="input text-xs py-0.5 px-1"
          bind:value={addCoinContainerId}
        >
          <option value={null}>Carried (loose)</option>
          {#each containerEntries as c}
            <option value={c.instance_id}>{c.item.name}</option>
          {/each}
        </select>
      </div>
    {/if}
    <button
      class="btn w-full"
      on:click={addCoins}
      disabled={addingCoins || Object.values(addCoinAmounts).every(v => !v)}
    >
      {addingCoins ? 'Adding...' : 'Add Coins'}
    </button>
  </div>
</Modal>

<!-- Send Coins to Treasury Modal -->
<Modal bind:open={showSendCoinsModal} title="Send Coins to Party Treasury">
  <div class="space-y-4">
    <p class="text-sm text-ink-faint">Transfer coins from {character.name}'s purse to the party treasury.</p>
    <div class="flex flex-wrap gap-3">
      {#each DENOM_KEYS as k}
        {@const available = currencyTotals[k] || 0}
        <div class="flex flex-col items-center">
          <label class="text-[10px] text-ink-faint uppercase" for="sc-{k}">{DENOM_LABELS[k]}</label>
          <input
            id="sc-{k}"
            class="input w-16 text-center"
            type="number"
            min="0"
            max={available}
            bind:value={sendCoinAmounts[k]}
          />
          <span class="text-[10px] text-ink-faint">/ {available}</span>
        </div>
      {/each}
    </div>
    <div class="flex gap-2">
      <button
        class="btn flex-1"
        on:click={sendCoinsToTreasury}
        disabled={sendingCoins || Object.values(sendCoinAmounts).every(v => !v)}
      >
        {sendingCoins ? 'Sending...' : 'Send to Treasury'}
      </button>
      <button
        class="btn-ghost text-xs"
        on:click={() => {
          for (const k of DENOM_KEYS) sendCoinAmounts[k] = currencyTotals[k] || 0;
        }}
      >All</button>
    </div>
  </div>
</Modal>
