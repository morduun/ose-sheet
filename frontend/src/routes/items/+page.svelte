<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import Badge from '$lib/components/shared/Badge.svelte';
  import { WEAPON_QUALITIES, itemTypeLabel, normalizeQualities } from '$lib/item-metadata.js';

  const ITEM_TYPES = [
    'weapon', 'armor', 'ammo',
    'potion', 'scroll', 'ring', 'wand', 'wondrous',
    'consumable', 'tool', 'treasure',
  ];

  let items = [];
  let loading = true;
  let error = '';

  // Filter state
  let filterType = '';
  let searchName = '';

  // Admin guard
  $: if (browser && $isAdmin === false) goto('/campaigns');

  async function fetchItems() {
    loading = true;
    error = '';
    try {
      let params = ['is_default=true', 'limit=500'];
      if (filterType) params.push(`item_type=${filterType}`);
      const qs = '?' + params.join('&');
      items = await api.get(`/items/${qs}`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  onMount(fetchItems);

  function onFilterChange() {
    fetchItems();
  }

  // Client-side name filter (search both names)
  $: filtered = searchName.trim()
    ? items.filter(i =>
        i.name.toLowerCase().includes(searchName.toLowerCase()) ||
        (i.unidentified_name && i.unidentified_name.toLowerCase().includes(searchName.toLowerCase()))
      )
    : items;

  // Group by item_type
  $: grouped = ITEM_TYPES
    .map(t => ({
      label: t,
      items: filtered.filter(i => i.item_type === t),
    }))
    .filter(g => g.items.length > 0);

  function truncate(text, max = 100) {
    if (!text || text.length <= max) return text || '';
    return text.slice(0, max) + '...';
  }

  function formatCost(cost) {
    if (cost == null) return '—';
    if (cost < 1) return `${Math.round(cost * 100)} cp`;
    return `${cost} gp`;
  }
</script>

<svelte:head>
  <title>Items — OSE Sheet</title>
</svelte:head>

<PageWrapper title="Items">
  <!-- Filter bar -->
  <div class="flex flex-wrap gap-3 mb-4 items-end">
    <div>
      <label class="block text-xs text-ink-faint mb-1" for="filter-type">Type</label>
      <select id="filter-type" class="input" bind:value={filterType} on:change={onFilterChange}>
        <option value="">All Types</option>
        {#each ITEM_TYPES as t}
          <option value={t}>{t}</option>
        {/each}
      </select>
    </div>
    <div>
      <label class="block text-xs text-ink-faint mb-1" for="filter-name">Search</label>
      <input id="filter-name" class="input" type="text" bind:value={searchName} placeholder="Filter by name..." />
    </div>
    <a href="/items/new" class="btn ml-auto">+ New Item</a>
  </div>

  {#if loading}
    <p class="text-ink-faint">Loading items...</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else if filtered.length === 0}
    <p class="text-ink-faint">No items found.</p>
  {:else}
    {#each grouped as group}
      <h2 class="section-title mt-6 mb-3 capitalize">{group.label}</h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {#each group.items as item}
          <a href="/items/{item.id}" class="panel hover:shadow-md transition-shadow block">
            <div class="flex items-start justify-between mb-1">
              <h3 class="font-serif text-lg text-ink">
                {item.name}
                {#if item.unidentified_name}
                  <span class="text-sm text-ink-faint font-sans">({item.unidentified_name})</span>
                {/if}
              </h3>
              <Badge label={itemTypeLabel(item)} variant="default" />
            </div>
            <div class="flex gap-3 text-xs text-ink-faint mb-1">
              {#if item.weight != null}<span>Wt: {item.weight}</span>{/if}
              {#if item.cost_gp != null}<span>Cost: {formatCost(item.cost_gp)}</span>{/if}
              {#if item.equippable}<span class="text-ink">Equippable</span>{/if}
            </div>
            {#if normalizeQualities(item.item_metadata?.qualities).length}
              <div class="flex flex-wrap gap-1 mb-1">
                {#each normalizeQualities(item.item_metadata?.qualities) as q}
                  <span
                    class="text-[10px] px-1.5 py-0 rounded bg-parchment-200 text-ink-faint leading-relaxed"
                    title={WEAPON_QUALITIES[q] ?? ''}
                  >{q}</span>
                {/each}
              </div>
            {/if}
            {#if item.item_metadata?.onset || item.item_metadata?.effect_failed}
              <div class="flex gap-3 text-xs text-ink-faint mb-1">
                {#if item.item_metadata.onset}<span>Onset: {item.item_metadata.onset}</span>{/if}
                {#if item.item_metadata.effect_failed}<span>Fail: {item.item_metadata.effect_failed}</span>{/if}
                {#if item.item_metadata.save != null}<span>Save: {item.item_metadata.save}+</span>{/if}
              </div>
            {/if}
            <p class="text-sm text-ink-light line-clamp-2">{truncate(item.description_player)}</p>
          </a>
        {/each}
      </div>
    {/each}
  {/if}
</PageWrapper>
