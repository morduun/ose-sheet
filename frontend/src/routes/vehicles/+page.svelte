<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import Badge from '$lib/components/shared/Badge.svelte';

  let vehicleTypes = [];
  let loading = true;
  let error = '';
  let searchName = '';
  let filterClass = '';

  $: if (browser && $isAdmin === false) goto('/campaigns');

  async function fetchTypes() {
    loading = true;
    try {
      vehicleTypes = await api.get('/vehicle-types');
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  onMount(fetchTypes);

  const CLASS_LABELS = { land: 'Land', seaworthy: 'Seaworthy', unseaworthy: 'Unseaworthy' };
  const CLASS_ORDER = ['land', 'seaworthy', 'unseaworthy'];

  $: filtered = vehicleTypes.filter(t => {
    if (filterClass && t.vehicle_class !== filterClass) return false;
    if (searchName.trim() && !t.name.toLowerCase().includes(searchName.toLowerCase())) return false;
    return true;
  });

  // Group by class for display
  $: grouped = CLASS_ORDER
    .map(cls => ({
      cls,
      label: CLASS_LABELS[cls],
      items: filtered.filter(t => t.vehicle_class === cls),
    }))
    .filter(g => g.items.length > 0);
</script>

<svelte:head>
  <title>Vehicle Types — OSE Sheet</title>
</svelte:head>

<PageWrapper title="Vehicle Types">
  <div class="flex flex-wrap gap-3 mb-4 items-end">
    <div>
      <label class="block text-xs text-ink-faint mb-1" for="filter-name">Search</label>
      <input id="filter-name" class="input" type="text" bind:value={searchName} placeholder="Filter by name..." />
    </div>
    <div>
      <label class="block text-xs text-ink-faint mb-1" for="filter-class">Class</label>
      <select id="filter-class" class="input" bind:value={filterClass}>
        <option value="">All</option>
        <option value="land">Land</option>
        <option value="seaworthy">Seaworthy</option>
        <option value="unseaworthy">Unseaworthy</option>
      </select>
    </div>
    <a href="/vehicles/new" class="btn ml-auto">+ New Vehicle Type</a>
  </div>

  {#if loading}
    <p class="text-ink-faint">Loading...</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else if filtered.length === 0}
    <p class="text-ink-faint">No vehicle types found.</p>
  {:else}
    {#each grouped as group}
      <div class="mb-6">
        <h3 class="section-title">{group.label}</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {#each group.items as vt}
            <a href="/vehicles/{vt.id}" class="panel hover:shadow-md transition-shadow block">
              <div class="flex items-start justify-between mb-1">
                <h3 class="font-serif text-lg text-ink">{vt.name}</h3>
                {#if !vt.is_default}
                  <Badge label="Custom" variant="gm" />
                {/if}
              </div>
              <div class="flex flex-wrap gap-x-3 gap-y-1 text-xs text-ink-faint">
                <span>HP {vt.hp}</span>
                <span>AC {vt.ac}</span>
                <span>Mv {vt.movement_rate}'</span>
                <span>Cargo {vt.cargo_capacity.toLocaleString()} cn</span>
                {#if vt.cost_gp}<span>{vt.cost_gp.toLocaleString()} gp</span>{/if}
                {#if vt.crew_min > 0}<span>Crew {vt.crew_min}+</span>{/if}
              </div>
              {#if vt.description}
                <p class="text-sm text-ink-light mt-1 line-clamp-2">{vt.description}</p>
              {/if}
            </a>
          {/each}
        </div>
      </div>
    {/each}
  {/if}
</PageWrapper>
