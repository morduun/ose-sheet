<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import Badge from '$lib/components/shared/Badge.svelte';

  let types = [];
  let loading = true;
  let error = '';
  let searchName = '';

  $: if (browser && $isAdmin === false) goto('/campaigns');

  onMount(async () => {
    try {
      types = await api.get('/specialist-types');
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  $: filtered = types.filter(t =>
    !searchName.trim() || t.name.toLowerCase().includes(searchName.toLowerCase())
  );
</script>

<svelte:head>
  <title>Specialist Types — OSE Sheet</title>
</svelte:head>

<PageWrapper title="Specialist Types">
  <div class="flex flex-wrap gap-3 mb-4 items-end">
    <div>
      <label class="block text-xs text-ink-faint mb-1" for="filter-name">Search</label>
      <input id="filter-name" class="input" type="text" bind:value={searchName} placeholder="Filter by name..." />
    </div>
    <a href="/specialists/new" class="btn ml-auto">+ New Type</a>
  </div>

  {#if loading}
    <p class="text-ink-faint">Loading...</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else if filtered.length === 0}
    <p class="text-ink-faint">No specialist types found.</p>
  {:else}
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {#each filtered as st}
        <a href="/specialists/{st.id}" class="panel hover:shadow-md transition-shadow block">
          <div class="flex items-start justify-between mb-1">
            <h3 class="font-serif text-lg text-ink">{st.name}</h3>
            {#if !st.is_default}
              <Badge label="Custom" variant="gm" />
            {/if}
          </div>
          <div class="text-xs text-ink-faint">{st.wage} gp/month</div>
          {#if st.description}
            <p class="text-sm text-ink-light mt-1 line-clamp-2">{st.description}</p>
          {/if}
        </a>
      {/each}
    </div>
  {/if}
</PageWrapper>
