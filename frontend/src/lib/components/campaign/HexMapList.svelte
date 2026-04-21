<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import Modal from '$lib/components/shared/Modal.svelte';

  export let campaignId;
  export let isGM = false;

  let maps = [];
  let loading = true;
  let error = '';

  // Create modal
  let showCreateModal = false;
  let newName = '';
  let newWidth = 15;
  let newHeight = 10;
  let newHexSize = 6;
  let creating = false;

  onMount(loadMaps);

  async function loadMaps() {
    loading = true;
    try {
      maps = await api.get(`/campaigns/${campaignId}/hex-maps`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function createMap() {
    if (!newName.trim()) return;
    creating = true;
    try {
      await api.post(`/campaigns/${campaignId}/hex-maps`, {
        name: newName.trim(),
        width: newWidth,
        height: newHeight,
        hex_size_miles: newHexSize,
      });
      newName = '';
      newWidth = 15;
      newHeight = 10;
      newHexSize = 6;
      showCreateModal = false;
      await loadMaps();
    } catch (e) {
      alert(e.message);
    } finally {
      creating = false;
    }
  }

  async function deleteMap(m) {
    if (!confirm(`Delete hex map "${m.name}" and all its cells?`)) return;
    try {
      await api.delete(`/campaigns/${campaignId}/hex-maps/${m.id}`);
      await loadMaps();
    } catch (e) {
      alert(e.message);
    }
  }
</script>

<div>
  <div class="flex items-center justify-between mb-4">
    <h2 class="section-title mb-0 border-none">Hex Maps</h2>
    {#if isGM}
      <button class="btn text-xs" on:click={() => showCreateModal = true}>+ New Hex Map</button>
    {/if}
  </div>

  {#if loading}
    <p class="text-ink-faint text-sm">Loading...</p>
  {:else if error}
    <p class="text-red-700 text-sm">{error}</p>
  {:else if maps.length === 0}
    <div class="panel text-center py-6">
      <p class="text-ink-faint text-sm">No hex maps yet. {isGM ? 'Create one to start mapping.' : ''}</p>
    </div>
  {:else}
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {#each maps as m}
        <div class="panel">
          <div class="flex items-start justify-between mb-2">
            <a href="/campaigns/{campaignId}/hexmap/{m.id}" class="font-serif text-lg text-ink hover:underline">
              {m.name}
            </a>
            {#if isGM}
              <button class="btn-danger text-xs" on:click={() => deleteMap(m)}>Delete</button>
            {/if}
          </div>
          <div class="flex items-center gap-3 text-xs text-ink-faint">
            <span>{m.width}&times;{m.height} hexes</span>
            <span>{m.hex_size_miles} mi/hex</span>
            <span>{m.cell_count} painted</span>
            {#if m.party_col != null}
              <span>Party: ({m.party_col}, {m.party_row})</span>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<Modal bind:open={showCreateModal} title="New Hex Map">
  <div class="space-y-4">
    <div>
      <label class="block text-sm text-ink mb-1" for="hm-name">Region Name</label>
      <input id="hm-name" class="input w-full" type="text" bind:value={newName} placeholder="The Borderlands" />
    </div>
    <div class="grid grid-cols-2 gap-3">
      <div>
        <label class="block text-sm text-ink mb-1" for="hm-w">Width (columns)</label>
        <input id="hm-w" class="input w-full" type="number" min="1" max="100" bind:value={newWidth} />
      </div>
      <div>
        <label class="block text-sm text-ink mb-1" for="hm-h">Height (rows)</label>
        <input id="hm-h" class="input w-full" type="number" min="1" max="100" bind:value={newHeight} />
      </div>
    </div>
    <div>
      <label class="block text-sm text-ink mb-1" for="hm-size">Miles per Hex</label>
      <input id="hm-size" class="input w-full" type="number" min="1" max="24" bind:value={newHexSize} />
    </div>
    <button class="btn w-full" on:click={createMap} disabled={creating || !newName.trim()}>
      {creating ? 'Creating...' : 'Create Hex Map'}
    </button>
  </div>
</Modal>
