<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import Badge from '$lib/components/shared/Badge.svelte';

  let classes = [];
  let loading = true;
  let error = '';

  // Admin guard
  $: if (browser && $isAdmin === false) goto('/campaigns');

  onMount(async () => {
    try {
      classes = await api.get('/character-classes/');
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });
</script>

<svelte:head>
  <title>Character Classes — OSE Sheet</title>
</svelte:head>

<PageWrapper title="Character Classes">
  {#if loading}
    <p class="text-ink-faint">Loading classes...</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else}
    <div class="mb-4">
      <a href="/classes/new" class="btn">+ New Class</a>
    </div>

    {#if classes.length === 0}
      <p class="text-ink-faint">No character classes found. Create one to get started.</p>
    {:else}
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {#each classes as cls}
          <a href="/classes/{cls.id}" class="panel hover:shadow-md transition-shadow block">
            <div class="flex items-start justify-between mb-2">
              <h2 class="font-serif text-xl text-ink">{cls.name}</h2>
              <Badge label={cls.class_data?.hit_dice || '?'} variant="default" />
            </div>
            {#if cls.class_data?.max_level}
              <p class="text-xs text-ink-faint mb-1">Max Level {cls.class_data.max_level}</p>
            {/if}
            {#if cls.class_data?.prime_requisite?.length}
              <p class="text-xs text-ink-faint mb-1">Prime Req: {cls.class_data.prime_requisite.join(', ')}</p>
            {/if}
            {#if cls.class_data?.Requirements && Object.keys(cls.class_data.Requirements).length}
              <p class="text-xs text-ink-faint mb-2">Requires: {Object.entries(cls.class_data.Requirements).map(([a, m]) => `${a} ${m}+`).join(', ')}</p>
            {/if}
            {#if cls.description}
              <p class="text-sm text-ink-light line-clamp-2">{cls.description}</p>
            {/if}
          </a>
        {/each}
      </div>
    {/if}
  {/if}
</PageWrapper>
