<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import Badge from '$lib/components/shared/Badge.svelte';
  import TreasureRoller from '$lib/components/treasure/TreasureRoller.svelte';

  let types = [];
  let loading = true;
  let error = '';
  let filterCategory = '';

  $: if (browser && $isAdmin === false) goto('/campaigns');

  onMount(async () => {
    try {
      types = await api.get('/treasure-types');
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  const CAT_LABELS = { hoard: 'Hoard (A-O)', individual: 'Individual (P-T)', group: 'Group (U-V)' };
  const CAT_ORDER = ['hoard', 'individual', 'group'];

  $: filtered = filterCategory
    ? types.filter(t => t.category === filterCategory)
    : types;

  $: grouped = CAT_ORDER
    .map(cat => ({
      cat,
      label: CAT_LABELS[cat],
      items: filtered.filter(t => t.category === cat),
    }))
    .filter(g => g.items.length > 0);
</script>

<svelte:head>
  <title>Treasure Types — OSE Sheet</title>
</svelte:head>

<PageWrapper title="Treasure Types">
  <!-- Quick Roller -->
  <div class="panel mb-6">
    <h2 class="section-title">Quick Roller</h2>
    <TreasureRoller />
  </div>

  <!-- Type List -->
  <div class="flex flex-wrap gap-3 mb-4 items-end">
    <div>
      <label class="block text-xs text-ink-faint mb-1" for="filter-cat">Category</label>
      <select id="filter-cat" class="input" bind:value={filterCategory}>
        <option value="">All</option>
        <option value="hoard">Hoards (A-O)</option>
        <option value="individual">Individual (P-T)</option>
        <option value="group">Group (U-V)</option>
      </select>
    </div>
    <a href="/treasure/new" class="btn ml-auto">+ New Type</a>
  </div>

  {#if loading}
    <p class="text-ink-faint">Loading...</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else}
    {#each grouped as group}
      <div class="mb-6">
        <h3 class="section-title">{group.label}</h3>
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {#each group.items as tt}
            <a href="/treasure/{tt.id}" class="panel hover:shadow-md transition-shadow block">
              <div class="flex items-start justify-between mb-1">
                <h3 class="font-serif text-lg text-ink">{tt.key}</h3>
                {#if !tt.is_default}
                  <Badge label="Custom" variant="gm" />
                {/if}
              </div>
              <div class="text-xs text-ink-faint">{tt.name}</div>
              {#if tt.average_gp != null}
                <div class="text-xs text-ink-faint mt-1">Avg: {tt.average_gp.toLocaleString()} gp</div>
              {/if}
            </a>
          {/each}
        </div>
      </div>
    {/each}
  {/if}
</PageWrapper>
