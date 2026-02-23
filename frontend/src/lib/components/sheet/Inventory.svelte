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

  // Currency fields (cp, sp, ep, gp, pp)
  const currencies = ['cp', 'sp', 'ep', 'gp', 'pp'];
  let currency = {};
  let savingCurrency = false;

  const slotLabels = {
    'armor': 'Armor',
    'shield': 'Shield',
    'main-hand': 'Main Hand',
    'off-hand': 'Off-Hand',
    'ammo': 'Ammo',
  };

  onMount(async () => {
    await loadItems();
    const meta = character.character_metadata ?? {};
    for (const c of currencies) {
      currency[c] = meta[c] ?? 0;
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
    i.name.toLowerCase().includes(searchQuery.toLowerCase())
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
      await loadItems();
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
    // Ammo goes straight to ammo slot
    if (entry.item.item_type === 'ammo') {
      equipItem(entry);
    // For weapons: if main-hand is occupied, offer choice
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
      const meta = { ...(character.character_metadata ?? {}), ...currency };
      await api.patch(`/characters/${character.id}`, { character_metadata: meta });
      character = { ...character, character_metadata: meta };
    } catch (e) {
      alert(e.message);
    } finally {
      savingCurrency = false;
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
          <label class="text-xs text-ink-faint uppercase" for="cur-{c}">{c}</label>
          <input
            id="cur-{c}"
            class="input w-16 text-center"
            type="number"
            min="0"
            bind:value={currency[c]}
          />
        </div>
      {/each}
      <button class="btn text-xs" on:click={saveCurrency} disabled={savingCurrency}>
        Save
      </button>
    </div>
  </div>

  <!-- Inventory list -->
  <div class="panel">
    <div class="flex items-center justify-between mb-4">
      <h2 class="section-title mb-0 border-none">Inventory</h2>
      <button class="btn text-xs" on:click={openAddModal}>+ Add Item</button>
    </div>

    {#if loading}
      <p class="text-ink-faint text-sm">Loading…</p>
    {:else if error}
      <p class="text-red-700 text-sm">{error}</p>
    {:else if items.length === 0}
      <p class="text-ink-faint text-sm text-center py-4">No items in inventory.</p>
    {:else}
      <div class="space-y-2">
        {#each items as entry}
          <div class="flex items-start gap-3 border-b border-parchment-200 pb-2 last:border-0">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="text-sm text-ink" class:font-bold={entry.slot}>{entry.item.name}</span>
                {#if entry.slot}
                  <Badge label={slotLabels[entry.slot] ?? entry.slot} />
                {/if}
              </div>
              {#if entry.item.description_player}
                <div class="text-xs text-ink-faint mt-0.5">{entry.item.description_player}</div>
              {/if}
              <div class="text-xs text-ink-faint">
                {itemTypeLabel(entry.item)}
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
              <!-- Secrets: GM sees all with toggles, players see only revealed -->
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
              <!-- GM-only description -->
              {#if isGM && entry.item.description_gm}
                <div class="text-xs text-amber-700 mt-0.5">{entry.item.description_gm}</div>
              {/if}
            </div>
            <div class="flex items-center gap-1 shrink-0">
              {#if entry.item.equippable}
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
              <button
                class="btn-ghost text-xs px-1.5 py-0.5"
                on:click={() => adjustQty(entry, -1)}
              >−</button>
              <span class="text-sm text-ink w-6 text-center">{entry.quantity}</span>
              <button
                class="btn-ghost text-xs px-1.5 py-0.5"
                on:click={() => adjustQty(entry, 1)}
              >+</button>
              <button
                class="btn-ghost text-xs px-1.5 py-0.5"
                on:click={() => returnToStash(entry)}
                title="Return to party stash"
              >Stash</button>
              <button
                class="btn-danger text-xs px-1.5 py-0.5 ml-1"
                on:click={() => removeItem(entry)}
              >✕</button>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>

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
          <div class="text-sm font-medium text-ink">{item.name}</div>
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
