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

  // Currency fields
  const currencies = [
    { key: 'cp', field: 'copper' },
    { key: 'sp', field: 'silver' },
    { key: 'ep', field: 'electrum' },
    { key: 'gp', field: 'gold' },
    { key: 'pp', field: 'platinum' },
  ];
  let currency = {};
  let savingCurrency = false;

  // Encumbrance
  const MAX_CARRY = 1600;
  const ENC_TABLE = [
    [400, 120], [600, 90], [800, 60], [1600, 30],
  ];

  // Identify containers and dropped state
  $: containerEntries = items.filter(e => !e.stashed && (e.item?.item_metadata?.capacity ?? 0) > 0);
  $: droppedContainerIds = new Set(
    items.filter(e => e.dropped && (e.item?.item_metadata?.capacity ?? 0) > 0).map(e => e.item.id)
  );

  // Items NOT in any container (and not themselves containers, and not stashed)
  $: carriedItems = items.filter(e =>
    !e.stashed && !e.container_item_id && !(e.item?.item_metadata?.capacity > 0)
  );

  // Items at home base
  $: stashedItems = items.filter(e => e.stashed);

  // Build container groups (include coin weight if coins are in this container)
  $: containerGroups = containerEntries.map(c => {
    const contents = items.filter(e => e.container_item_id === c.item.id);
    let load = contents.reduce((sum, e) => sum + ((e.item?.weight ?? 0) * e.quantity), 0);
    const hasCoinWeight = character.coin_container_id === c.item.id;
    if (hasCoinWeight) load += rawCoinWeight;
    const capacity = c.item.item_metadata.capacity;
    return { entry: c, contents, load, capacity, hasCoinWeight };
  });

  // Encumbrance excluding dropped containers and their contents
  $: itemWeight = items.reduce((sum, e) => {
    if (e.stashed) return sum;
    if (e.dropped) return sum;
    if (droppedContainerIds.has(e.container_item_id)) return sum;
    return sum + ((e.item?.weight ?? 0) * e.quantity);
  }, 0);
  $: rawCoinWeight = (character.copper ?? 0) + (character.silver ?? 0)
    + (character.electrum ?? 0) + (character.gold ?? 0) + (character.platinum ?? 0);
  $: coinWeight = (character.coin_container_id != null && droppedContainerIds.has(character.coin_container_id))
    ? 0 : rawCoinWeight;
  $: encumbrance = Math.round(itemWeight + coinWeight);
  $: encMovement = ENC_TABLE.find(([t]) => encumbrance <= t)?.[1] ?? 0;
  $: encPct = Math.min(100, (encumbrance / MAX_CARRY) * 100);

  const slotLabels = {
    'armor': 'Armor',
    'shield': 'Shield',
    'main-hand': 'Main Hand',
    'off-hand': 'Off-Hand',
    'ammo': 'Ammo',
  };

  onMount(async () => {
    await loadItems();
    for (const c of currencies) {
      currency[c.key] = character[c.field] ?? 0;
    }
  });

  async function loadItems() {
    loading = true;
    try {
      items = await api.get(`/characters/${character.id}/items`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
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
      await api.patch(`/characters/${character.id}/items/${item.item.id}`, {
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
      await api.delete(`/items/${item.item.id}/assign/${character.id}`);
      await loadItems();
    } catch (e) {
      alert(e.message);
    }
  }

  async function equipItem(entry, slot) {
    try {
      const body = slot ? { slot } : {};
      items = await api.post(
        `/characters/${character.id}/items/${entry.item.id}/equip`,
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
        `/characters/${character.id}/items/${entry.item.id}/unequip`,
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

  async function returnToStash(entry) {
    try {
      await api.post(
        `/campaigns/${character.campaign_id}/stash/${entry.item.id}/return`,
        { character_id: character.id, quantity: 1 }
      );
      await loadItems();
    } catch (e) {
      alert(e.message);
    }
  }

  async function identifyItem(entry) {
    try {
      await api.patch(`/characters/${character.id}/items/${entry.item.id}/identify`);
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

  async function saveCurrency() {
    savingCurrency = true;
    try {
      const update = {};
      for (const c of currencies) {
        update[c.field] = currency[c.key] ?? 0;
      }
      await api.patch(`/characters/${character.id}`, update);
      for (const c of currencies) {
        character[c.field] = update[c.field];
      }
      character = character;
    } catch (e) {
      alert(e.message);
    } finally {
      savingCurrency = false;
    }
  }

  // --- Stash (home base) ---
  async function stashItem(entry) {
    try {
      items = await api.post(
        `/characters/${character.id}/items/${entry.item.id}/stash`,
        { stashed: true }
      );
    } catch (e) {
      alert(e.message);
    }
  }

  async function retrieveItem(entry) {
    try {
      items = await api.post(
        `/characters/${character.id}/items/${entry.item.id}/stash`,
        { stashed: false }
      );
    } catch (e) {
      alert(e.message);
    }
  }

  // --- Coin container ---
  // If coin container is stashed or doesn't exist in active containers, treat as null
  $: coinContainerId = (() => {
    const id = character.coin_container_id ?? null;
    if (id == null) return null;
    if (!containerEntries.some(c => c.item.id === id)) return null;
    return id;
  })();
  $: coinContainerDropped = coinContainerId != null && droppedContainerIds.has(coinContainerId);

  async function setCoinContainer(containerItemId) {
    try {
      await api.patch(`/characters/${character.id}`, {
        coin_container_id: containerItemId || null,
      });
      character.coin_container_id = containerItemId || null;
      character = character;
      dispatch('ac-changed');
    } catch (e) {
      alert(e.message);
    }
  }

  // --- Container functions ---

  async function moveItem(entry, containerItemId) {
    try {
      items = await api.post(
        `/characters/${character.id}/items/${entry.item.id}/move`,
        { container_item_id: containerItemId }
      );
    } catch (e) {
      alert(e.message);
    }
  }

  async function toggleDrop(containerEntry) {
    try {
      items = await api.post(
        `/characters/${character.id}/items/${containerEntry.item.id}/drop`,
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
      if (cg.entry.item.id === entry.container_item_id) continue; // already here
      if (cg.entry.dropped) continue; // can't put items in dropped containers
      const itemWt = (entry.item?.weight ?? 0) * entry.quantity;
      const wouldExceed = cg.load + itemWt > cg.capacity;
      targets.push({
        id: cg.entry.item.id,
        label: `${cg.entry.item.name} (${Math.round(cg.load)}/${cg.capacity})`,
        full: wouldExceed,
      });
    }
    return targets;
  }

  function isInDroppedContainer(entry) {
    return entry.container_item_id != null && droppedContainerIds.has(entry.container_item_id);
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
        `/characters/${character.id}/items/${entry.item.id}/state`,
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

  async function saveAppraisedValue(entry, value) {
    const numVal = value === '' ? null : parseFloat(value);
    try {
      const updated = await api.patch(
        `/characters/${character.id}/items/${entry.item.id}/state`,
        { state: { appraised_value: numVal } }
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
        `/characters/${character.id}/items/${entry.item.id}/state`,
        { state: { contents: value } }
      );
      entry.state = updated.state;
      items = items;
    } catch (e) {
      alert(e.message);
    }
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
    <div class="flex flex-wrap gap-3 items-end">
      {#each currencies as c}
        <div class="flex flex-col items-center">
          <label class="text-xs text-ink-faint uppercase" for="cur-{c.key}">{c.key}</label>
          <input
            id="cur-{c.key}"
            class="input w-16 text-center"
            type="number"
            min="0"
            bind:value={currency[c.key]}
          />
        </div>
      {/each}
      <button class="btn text-xs" on:click={saveCurrency} disabled={savingCurrency}>
        Save
      </button>
    </div>
    {#if containerEntries.length > 0}
      <div class="flex items-center gap-2 mt-3 pt-2 border-t border-parchment-200">
        <span class="text-xs text-ink-faint">Kept in:</span>
        <select
          class="input text-xs py-0.5 px-1"
          value={coinContainerId ?? ''}
          on:change={(e) => setCoinContainer(e.target.value === '' ? null : parseInt(e.target.value))}
        >
          <option value="">Carried (loose)</option>
          {#each containerEntries as c}
            <option value={c.item.id}>{c.item.name}</option>
          {/each}
        </select>
        <span class="text-xs text-ink-faint">({rawCoinWeight} cn)</span>
        {#if coinContainerDropped}
          <span class="text-xs text-red-700">Dropped!</span>
        {/if}
      </div>
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
      <p class="text-ink-faint text-sm">Loading…</p>
    {:else if error}
      <p class="text-red-700 text-sm">{error}</p>
    {:else if items.length === 0}
      <p class="text-ink-faint text-sm text-center py-4">No items in inventory.</p>
    {:else}
      <!-- Carried items (not in any container, not containers themselves) -->
      {#if carriedItems.length > 0}
        <div class="mb-4">
          <div class="text-xs text-ink-faint uppercase tracking-wide mb-2">Carried</div>
          <div class="space-y-2">
            {#each carriedItems as entry (entry.item.id)}
              {@render itemRow(entry)}
            {/each}
          </div>
        </div>
      {/if}

      <!-- Container sections -->
      {#each containerGroups as cg (cg.entry.item.id)}
        {@const pct = fillPct(cg.load, cg.capacity)}
        {@const isDropped = cg.entry.dropped}
        {@const isCollapsed = collapsedContainers.has(cg.entry.item.id)}
        <div class="mb-4 border border-parchment-200 rounded-sm" class:opacity-50={isDropped}>
          <!-- Container header -->
          <div class="flex items-center gap-2 px-3 py-2 bg-parchment-100/50">
            <button
              class="text-ink-faint text-xs w-4 shrink-0"
              on:click={() => toggleCollapse(cg.entry.item.id)}
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
                on:click={() => returnToStash(cg.entry)}
                title="Return to party stash (with contents)"
              >Stash</button>
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
              {#if cg.hasCoinWeight}
                <div class="flex items-center justify-between text-sm border-b border-parchment-200 pb-2">
                  <span class="text-ink-faint italic">Currency</span>
                  <span class="text-xs text-ink-faint">{rawCoinWeight} cn</span>
                </div>
              {/if}
              {#if cg.contents.length === 0 && !cg.hasCoinWeight}
                <p class="text-ink-faint text-xs text-center py-2">Empty</p>
              {:else}
                {#each cg.contents as entry (entry.item.id)}
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
        {#each stashedItems as entry (entry.item.id)}
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
            placeholder="Contents…"
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
        {#if getAppraisedValue(entry) != null}
          <span class="ml-1 text-amber-700">{getAppraisedValue(entry).toLocaleString()} gp</span>
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
        <div class="flex items-center gap-1 mt-0.5">
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
          value={entry.container_item_id ?? ''}
          on:change={(e) => moveItem(entry, e.target.value === '' ? null : parseInt(e.target.value))}
        >
          {#each targets as t}
            <option value={t.id ?? ''} disabled={t.full}>{t.label}</option>
          {/each}
        </select>
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
          on:click={() => stashItem(entry)}
          title="Send to home base"
        >Home</button>
      {:else}
        <button
          class="btn text-xs px-1.5 py-0.5"
          on:click={() => retrieveItem(entry)}
          title="Retrieve from home base"
        >Retrieve</button>
      {/if}
      <button
        class="btn-ghost text-xs px-1.5 py-0.5"
        on:click={() => returnToStash(entry)}
        title="Return to party stash"
      >Party</button>
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
      placeholder="Search items…"
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
