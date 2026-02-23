<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import Modal from '$lib/components/shared/Modal.svelte';
  import { itemTypeLabel, normalizeQualities, WEAPON_QUALITIES } from '$lib/item-metadata.js';

  export let campaignId;
  export let isGM = false;
  export let characters = [];

  let stashItems = [];
  let loading = true;
  let error = '';

  // Add to stash modal
  let showAddModal = false;
  let availableItems = [];
  let searchQuery = '';
  let addQty = 1;
  let addingItemId = null;

  // Take from stash modal
  let showTakeModal = false;
  let takeEntry = null;
  let takeCharacterId = null;
  let takeQty = 1;
  let takingItem = false;

  onMount(() => {
    loadStash();
  });

  async function loadStash() {
    loading = true;
    try {
      stashItems = await api.get(`/campaigns/${campaignId}/stash`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function openAddModal() {
    showAddModal = true;
    searchQuery = '';
    addQty = 1;
    try {
      availableItems = await api.get(`/items/?campaign_id=${campaignId}&limit=500`);
    } catch {
      availableItems = [];
    }
  }

  $: filteredItems = availableItems.filter((i) =>
    i.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  async function addToStash(item) {
    addingItemId = item.id;
    try {
      await api.post(`/campaigns/${campaignId}/stash`, {
        item_id: item.id,
        quantity: addQty,
      });
      await loadStash();
      showAddModal = false;
    } catch (e) {
      alert(e.message);
    } finally {
      addingItemId = null;
    }
  }

  async function adjustQty(entry, delta) {
    const newQty = entry.quantity + delta;
    if (newQty <= 0) {
      await removeFromStash(entry);
      return;
    }
    try {
      await api.patch(`/campaigns/${campaignId}/stash/${entry.item.id}`, {
        quantity: newQty,
      });
      await loadStash();
    } catch (e) {
      alert(e.message);
    }
  }

  async function removeFromStash(entry) {
    try {
      await api.delete(`/campaigns/${campaignId}/stash/${entry.item.id}`);
      await loadStash();
    } catch (e) {
      alert(e.message);
    }
  }

  function openTakeModal(entry) {
    takeEntry = entry;
    takeCharacterId = characters.length > 0 ? characters[0].id : null;
    takeQty = 1;
    showTakeModal = true;
  }

  async function takeFromStash() {
    if (!takeEntry || !takeCharacterId) return;
    takingItem = true;
    try {
      await api.post(`/campaigns/${campaignId}/stash/${takeEntry.item.id}/take`, {
        character_id: takeCharacterId,
        quantity: takeQty,
      });
      await loadStash();
      showTakeModal = false;
    } catch (e) {
      alert(e.message);
    } finally {
      takingItem = false;
    }
  }
</script>

<div class="panel">
  <div class="flex items-center justify-between mb-4">
    <h2 class="section-title mb-0 border-none">Party Stash</h2>
    {#if isGM}
      <button class="btn text-xs" on:click={openAddModal}>+ Add Loot</button>
    {/if}
  </div>

  {#if loading}
    <p class="text-ink-faint text-sm">Loading...</p>
  {:else if error}
    <p class="text-red-700 text-sm">{error}</p>
  {:else if stashItems.length === 0}
    <p class="text-ink-faint text-sm text-center py-4">The party stash is empty.</p>
  {:else}
    <div class="space-y-2">
      {#each stashItems as entry}
        <div class="flex items-start gap-3 border-b border-parchment-200 pb-2 last:border-0">
          <div class="flex-1 min-w-0">
            <div class="text-sm text-ink font-medium">{entry.item.name}</div>
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
          </div>
          <div class="flex items-center gap-1 shrink-0">
            {#if characters.length > 0}
              <button
                class="btn text-xs px-1.5 py-0.5"
                on:click={() => openTakeModal(entry)}
              >Take</button>
            {/if}
            {#if isGM}
              <button
                class="btn-ghost text-xs px-1.5 py-0.5"
                on:click={() => adjustQty(entry, -1)}
              >-</button>
            {/if}
            <span class="text-sm text-ink w-6 text-center">{entry.quantity}</span>
            {#if isGM}
              <button
                class="btn-ghost text-xs px-1.5 py-0.5"
                on:click={() => adjustQty(entry, 1)}
              >+</button>
              <button
                class="btn-danger text-xs px-1.5 py-0.5 ml-1"
                on:click={() => removeFromStash(entry)}
              >✕</button>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Add to Stash Modal -->
<Modal bind:open={showAddModal} title="Add Loot to Stash">
  <div class="space-y-3">
    <input
      class="input w-full"
      type="text"
      placeholder="Search items..."
      bind:value={searchQuery}
    />
    <div class="flex items-center gap-2">
      <label class="text-xs text-ink" for="stash-add-qty">Quantity</label>
      <input id="stash-add-qty" class="input w-16" type="number" min="1" bind:value={addQty} />
    </div>
    <div class="space-y-1 max-h-60 overflow-y-auto">
      {#each filteredItems as item}
        <button
          class="w-full text-left panel py-2 px-3 hover:bg-parchment-100 transition-colors"
          on:click={() => addToStash(item)}
          disabled={addingItemId === item.id}
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

<!-- Take from Stash Modal -->
<Modal bind:open={showTakeModal} title="Take from Stash">
  {#if takeEntry}
    <div class="space-y-4">
      <div>
        <div class="text-sm font-medium text-ink">{takeEntry.item.name}</div>
        <div class="text-xs text-ink-faint">Available: {takeEntry.quantity}</div>
      </div>
      <div>
        <label class="text-xs text-ink block mb-1" for="take-char">Character</label>
        <select id="take-char" class="input w-full" bind:value={takeCharacterId}>
          {#each characters as char}
            <option value={char.id}>{char.name}</option>
          {/each}
        </select>
      </div>
      <div class="flex items-center gap-2">
        <label class="text-xs text-ink" for="take-qty">Quantity</label>
        <input
          id="take-qty"
          class="input w-16"
          type="number"
          min="1"
          max={takeEntry.quantity}
          bind:value={takeQty}
        />
      </div>
      <button
        class="btn w-full"
        on:click={takeFromStash}
        disabled={takingItem || !takeCharacterId}
      >
        {takingItem ? 'Taking...' : 'Take'}
      </button>
    </div>
  {/if}
</Modal>
