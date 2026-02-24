<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import Badge from '$lib/components/shared/Badge.svelte';

  let monsters = [];
  let loading = true;
  let error = '';
  let searchName = '';

  // Admin guard
  $: if (browser && $isAdmin === false) goto('/campaigns');

  async function fetchMonsters() {
    loading = true;
    error = '';
    try {
      monsters = await api.get('/monsters/?is_default=true&limit=500');
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  onMount(fetchMonsters);

  $: filtered = searchName.trim()
    ? monsters.filter(m => m.name.toLowerCase().includes(searchName.toLowerCase()))
    : monsters;
</script>

<svelte:head>
  <title>Monsters — OSE Sheet</title>
</svelte:head>

<PageWrapper title="Monsters">
  <div class="flex flex-wrap gap-3 mb-4 items-end">
    <div>
      <label class="block text-xs text-ink-faint mb-1" for="filter-name">Search</label>
      <input id="filter-name" class="input" type="text" bind:value={searchName} placeholder="Filter by name..." />
    </div>
    <a href="/monsters/new" class="btn ml-auto">+ New Monster</a>
  </div>

  {#if loading}
    <p class="text-ink-faint">Loading monsters...</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else if filtered.length === 0}
    <p class="text-ink-faint">No monsters found.</p>
  {:else}
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {#each filtered as monster}
        <a href="/monsters/{monster.id}" class="panel hover:shadow-md transition-shadow block">
          <div class="flex items-start justify-between mb-1">
            <h3 class="font-serif text-lg text-ink">{monster.name}</h3>
            {#if monster.alignment}
              <Badge label={monster.alignment} variant="default" />
            {/if}
          </div>
          <div class="flex flex-wrap gap-x-3 gap-y-1 text-xs text-ink-faint">
            {#if monster.ac != null}<span>AC {monster.ac}</span>{/if}
            {#if monster.hit_dice}<span>HD {monster.hit_dice}</span>{/if}
            {#if monster.hp != null}<span>HP {monster.hp}</span>{/if}
            {#if monster.thac0 != null}<span>THAC0 {monster.thac0}</span>{/if}
            {#if monster.movement_rate}<span>Mv {monster.movement_rate}</span>{/if}
            {#if monster.xp != null}<span>XP {monster.xp}</span>{/if}
          </div>
          {#if monster.description}
            <p class="text-sm text-ink-light mt-1 line-clamp-2">{monster.description}</p>
          {/if}
        </a>
      {/each}
    </div>
  {/if}
</PageWrapper>
