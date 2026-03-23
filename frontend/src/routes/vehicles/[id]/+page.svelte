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

  let vt = null;
  let loading = true;
  let error = '';

  $: if (browser && $isAdmin === false) goto('/campaigns');

  const CLASS_LABELS = { land: 'Land', seaworthy: 'Seaworthy', unseaworthy: 'Unseaworthy' };

  onMount(async () => {
    try {
      vt = await api.get(`/vehicle-types/${typeId}`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  async function deleteType() {
    if (!confirm(`Delete ${vt.name}? This cannot be undone.`)) return;
    try {
      await api.delete(`/vehicle-types/${typeId}`);
      goto('/vehicles');
    } catch (e) {
      alert(e.message);
    }
  }
</script>

<svelte:head>
  <title>{vt?.name ?? 'Vehicle Type'} — OSE Sheet</title>
</svelte:head>

<PageWrapper title={vt?.name ?? 'Vehicle Type'} maxWidth="max-w-2xl">
  {#if loading}
    <p class="text-ink-faint">Loading...</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else if vt}
    <div class="panel">
      <div class="flex items-start justify-between mb-4">
        <div>
          <h1 class="font-serif text-3xl text-ink">{vt.name}</h1>
          <p class="text-ink-faint text-sm mt-1">
            <span class="font-mono">{vt.key}</span> · {CLASS_LABELS[vt.vehicle_class] ?? vt.vehicle_class}
            {#if vt.is_default}
              · Default
            {:else}
              · <Badge label="Custom" variant="gm" />
            {/if}
          </p>
        </div>
        <div class="text-right">
          <div class="text-xs text-ink-faint">AC</div>
          <div class="font-serif text-3xl text-ink">{vt.ac}</div>
        </div>
      </div>

      <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
        <div class="text-center border border-ink-faint/30 rounded-sm p-2">
          <div class="text-xs text-ink-faint uppercase">Hull Points</div>
          <div class="font-serif text-2xl text-ink">{vt.hp}</div>
        </div>
        <div class="text-center border border-ink-faint/30 rounded-sm p-2">
          <div class="text-xs text-ink-faint uppercase">Movement</div>
          <div class="font-serif text-2xl text-ink">{vt.movement_rate}'</div>
        </div>
        <div class="text-center border border-ink-faint/30 rounded-sm p-2">
          <div class="text-xs text-ink-faint uppercase">Cargo</div>
          <div class="font-serif text-2xl text-ink">{vt.cargo_capacity.toLocaleString()}</div>
          <div class="text-xs text-ink-faint">coins</div>
        </div>
        <div class="text-center border border-ink-faint/30 rounded-sm p-2">
          <div class="text-xs text-ink-faint uppercase">Cost</div>
          <div class="font-serif text-2xl text-ink">{vt.cost_gp?.toLocaleString() ?? '—'}</div>
          <div class="text-xs text-ink-faint">gp</div>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4 mb-4 text-sm">
        <div>
          <span class="text-ink-faint">Min Crew:</span>
          <span class="text-ink font-medium">{vt.crew_min}</span>
        </div>
        {#if vt.passengers != null}
          <div>
            <span class="text-ink-faint">Passengers:</span>
            <span class="text-ink font-medium">{vt.passengers}</span>
          </div>
        {/if}
      </div>

      {#if vt.description}
        <p class="text-sm text-ink-light">{vt.description}</p>
      {/if}
    </div>

    <div class="flex gap-3 mt-4">
      <a href="/vehicles/{typeId}/edit" class="btn">Edit</a>
      <button class="btn-danger" on:click={deleteType}>Delete</button>
      <a href="/vehicles" class="btn-ghost ml-auto">← Back</a>
    </div>
  {/if}
</PageWrapper>
