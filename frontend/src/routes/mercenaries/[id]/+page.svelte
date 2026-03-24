<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import Badge from '$lib/components/shared/Badge.svelte';

  const typeId = $page.params.id;

  let mt = null;
  let loading = true;
  let error = '';

  $: if (browser && $isAdmin === false) goto('/campaigns');

  onMount(async () => {
    try {
      mt = await api.get(`/mercenary-types/${typeId}`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  async function deleteType() {
    if (!confirm(`Delete ${mt.name}?`)) return;
    try {
      await api.delete(`/mercenary-types/${typeId}`);
      goto('/mercenaries');
    } catch (e) {
      alert(e.message);
    }
  }
</script>

<svelte:head>
  <title>{mt?.name ?? 'Mercenary Type'} — OSE Sheet</title>
</svelte:head>

<PageWrapper title={mt?.name ?? 'Mercenary Type'} maxWidth="max-w-2xl">
  {#if loading}
    <p class="text-ink-faint">Loading...</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else if mt}
    <div class="panel">
      <div class="flex items-start justify-between mb-4">
        <div>
          <h1 class="font-serif text-3xl text-ink">{mt.name}</h1>
          <p class="text-ink-faint text-sm mt-1">
            <span class="font-mono">{mt.key}</span>
            {#if !mt.is_default}
              · <Badge label="Custom" variant="gm" />
            {/if}
          </p>
        </div>
        <div class="text-right">
          <div class="text-xs text-ink-faint">AC</div>
          <div class="font-serif text-3xl text-ink">{mt.ac}</div>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4 mb-4">
        <div class="text-center border border-ink-faint/30 rounded-sm p-2">
          <div class="text-xs text-ink-faint uppercase">Armour Class</div>
          <div class="font-serif text-2xl text-ink">{mt.ac}</div>
        </div>
        <div class="text-center border border-ink-faint/30 rounded-sm p-2">
          <div class="text-xs text-ink-faint uppercase">Morale</div>
          <div class="font-serif text-2xl text-ink">{mt.morale}</div>
        </div>
      </div>

      {#if mt.description}
        <p class="text-sm text-ink-light mb-4">{mt.description}</p>
      {/if}

      {#if mt.race_costs && Object.keys(mt.race_costs).length > 0}
        <h3 class="section-title">Race Costs</h3>
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-ink-faint/30">
              <th class="text-left py-1 text-ink-faint font-normal">Race</th>
              <th class="text-right py-1 text-ink-faint font-normal">Cost (gp/month)</th>
            </tr>
          </thead>
          <tbody>
            {#each Object.entries(mt.race_costs) as [race, cost]}
              <tr class="border-b border-ink-faint/10">
                <td class="py-1 capitalize text-ink">{race}</td>
                <td class="py-1 text-right text-ink">{cost}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>

    <div class="flex gap-3 mt-4">
      <a href="/mercenaries/{typeId}/edit" class="btn">Edit</a>
      <button class="btn-danger" on:click={deleteType}>Delete</button>
      <a href="/mercenaries" class="btn-ghost ml-auto">Back</a>
    </div>
  {/if}
</PageWrapper>
