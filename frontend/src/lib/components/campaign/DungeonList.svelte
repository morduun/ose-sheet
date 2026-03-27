<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import Modal from '$lib/components/shared/Modal.svelte';

  export let campaignId;
  export let isGM = false;

  let dungeons = [];
  let loading = true;
  let error = '';

  // Create dungeon modal
  let showCreateModal = false;
  let newName = '';
  let newDesc = '';
  let creating = false;

  onMount(loadDungeons);

  async function loadDungeons() {
    loading = true;
    try {
      dungeons = await api.get(`/campaigns/${campaignId}/dungeons`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function createDungeon() {
    if (!newName.trim()) return;
    creating = true;
    try {
      await api.post(`/campaigns/${campaignId}/dungeons`, {
        name: newName.trim(),
        description: newDesc.trim() || null,
      });
      newName = '';
      newDesc = '';
      showCreateModal = false;
      await loadDungeons();
    } catch (e) {
      alert(e.message);
    } finally {
      creating = false;
    }
  }

  async function deleteDungeon(d) {
    if (!confirm(`Delete ${d.name} and all its rooms?`)) return;
    try {
      await api.delete(`/campaigns/${campaignId}/dungeons/${d.id}`);
      await loadDungeons();
    } catch (e) {
      alert(e.message);
    }
  }
</script>

<div>
  <div class="flex items-center justify-between mb-4">
    <h2 class="section-title mb-0 border-none">Dungeons</h2>
    {#if isGM}
      <button class="btn text-xs" on:click={() => showCreateModal = true}>+ New Dungeon</button>
    {/if}
  </div>

  {#if loading}
    <p class="text-ink-faint text-sm">Loading...</p>
  {:else if error}
    <p class="text-red-700 text-sm">{error}</p>
  {:else if dungeons.length === 0}
    <div class="panel text-center py-6">
      <p class="text-ink-faint text-sm">No dungeons yet. {isGM ? 'Create one to start planning.' : ''}</p>
    </div>
  {:else}
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {#each dungeons as d}
        <div class="panel">
          <div class="flex items-start justify-between mb-2">
            <a href="/campaigns/{campaignId}/dungeons/{d.id}" class="font-serif text-lg text-ink hover:underline">
              {d.name}
            </a>
            {#if isGM}
              <button class="btn-danger text-xs" on:click={() => deleteDungeon(d)}>Delete</button>
            {/if}
          </div>
          {#if d.description}
            <p class="text-sm text-ink-faint mb-2">{d.description}</p>
          {/if}
          <div class="flex items-center gap-3 text-xs text-ink-faint">
            <span>{d.room_count} rooms</span>
            {#if d.room_count > 0}
              <span>{d.cleared_count}/{d.room_count} cleared</span>
              {@const pct = Math.round((d.cleared_count / d.room_count) * 100)}
              <div class="flex-1 h-1.5 bg-parchment-200 rounded overflow-hidden">
                <div
                  class="h-full rounded transition-all bg-green-600"
                  style="width: {pct}%"
                ></div>
              </div>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<Modal bind:open={showCreateModal} title="New Dungeon">
  <div class="space-y-4">
    <div>
      <label class="block text-sm text-ink mb-1" for="dg-name">Name</label>
      <input id="dg-name" class="input w-full" type="text" bind:value={newName} placeholder="Stonehell" />
    </div>
    <div>
      <label class="block text-sm text-ink mb-1" for="dg-desc">Description</label>
      <textarea id="dg-desc" class="input w-full resize-none" rows="3" bind:value={newDesc} placeholder="A megadungeon beneath the hills..."></textarea>
    </div>
    <button class="btn w-full" on:click={createDungeon} disabled={creating || !newName.trim()}>
      {creating ? 'Creating...' : 'Create Dungeon'}
    </button>
  </div>
</Modal>
