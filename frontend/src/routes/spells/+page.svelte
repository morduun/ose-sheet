<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import Badge from '$lib/components/shared/Badge.svelte';

  const SPELL_CLASSES = ['cleric', 'druid', 'illusionist', 'magic-user'];

  let spells = [];
  let loading = true;
  let error = '';

  // Filter state
  let filterClass = '';
  let filterLevel = '';
  let searchName = '';

  // Admin guard
  $: if (browser && $isAdmin === false) goto('/campaigns');

  async function fetchSpells() {
    loading = true;
    error = '';
    try {
      let params = [];
      if (filterClass) params.push(`spell_class=${filterClass}`);
      if (filterLevel) params.push(`level=${filterLevel}`);
      const qs = params.length ? '?' + params.join('&') + '&limit=500' : '?limit=500';
      spells = await api.get(`/spells/${qs}`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  onMount(fetchSpells);

  function onFilterChange() {
    fetchSpells();
  }

  // Client-side name filter
  $: filtered = searchName.trim()
    ? spells.filter(s => s.name.toLowerCase().includes(searchName.toLowerCase()))
    : spells;

  // Group by spell_class
  $: grouped = SPELL_CLASSES
    .map(sc => ({
      label: sc,
      spells: filtered.filter(s => s.spell_class === sc),
    }))
    .filter(g => g.spells.length > 0);

  function truncate(text, max = 100) {
    if (!text || text.length <= max) return text || '';
    return text.slice(0, max) + '...';
  }
</script>

<svelte:head>
  <title>Spells — OSE Sheet</title>
</svelte:head>

<PageWrapper title="Spells">
  <!-- Filter bar -->
  <div class="flex flex-wrap gap-3 mb-4 items-end">
    <div>
      <label class="block text-xs text-ink-faint mb-1" for="filter-class">Class</label>
      <select id="filter-class" class="input" bind:value={filterClass} on:change={onFilterChange}>
        <option value="">All Classes</option>
        {#each SPELL_CLASSES as sc}
          <option value={sc}>{sc}</option>
        {/each}
      </select>
    </div>
    <div>
      <label class="block text-xs text-ink-faint mb-1" for="filter-level">Level</label>
      <select id="filter-level" class="input" bind:value={filterLevel} on:change={onFilterChange}>
        <option value="">All Levels</option>
        {#each [1,2,3,4,5,6] as l}
          <option value={l}>{l}</option>
        {/each}
      </select>
    </div>
    <div>
      <label class="block text-xs text-ink-faint mb-1" for="filter-name">Search</label>
      <input id="filter-name" class="input" type="text" bind:value={searchName} placeholder="Filter by name..." />
    </div>
    <a href="/spells/new" class="btn ml-auto">+ New Spell</a>
  </div>

  {#if loading}
    <p class="text-ink-faint">Loading spells...</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else if filtered.length === 0}
    <p class="text-ink-faint">No spells found.</p>
  {:else}
    {#each grouped as group}
      <h2 class="section-title mt-6 mb-3 capitalize">{group.label}</h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {#each group.spells as spell}
          <a href="/spells/{spell.id}" class="panel hover:shadow-md transition-shadow block">
            <div class="flex items-start justify-between mb-1">
              <h3 class="font-serif text-lg text-ink">{spell.name}</h3>
              <Badge label="Lvl {spell.level}" variant="default" />
            </div>
            <div class="flex gap-3 text-xs text-ink-faint mb-2">
              {#if spell.range}<span>Range: {spell.range}</span>{/if}
              {#if spell.duration}<span>Dur: {spell.duration}</span>{/if}
            </div>
            <p class="text-sm text-ink-light line-clamp-2">{truncate(spell.description)}</p>
          </a>
        {/each}
      </div>
    {/each}
  {/if}
</PageWrapper>
