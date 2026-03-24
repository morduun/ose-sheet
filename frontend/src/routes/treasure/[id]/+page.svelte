<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import Badge from '$lib/components/shared/Badge.svelte';
  import TreasureRoller from '$lib/components/treasure/TreasureRoller.svelte';

  const typeId = $page.params.id;

  let tt = null;
  let loading = true;
  let error = '';

  $: if (browser && $isAdmin === false) goto('/campaigns');

  const CAT_LABELS = { hoard: 'Hoard', individual: 'Individual', group: 'Group' };

  onMount(async () => {
    try {
      tt = await api.get(`/treasure-types/${typeId}`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  async function deleteType() {
    if (!confirm(`Delete ${tt.name}?`)) return;
    try {
      await api.delete(`/treasure-types/${typeId}`);
      goto('/treasure');
    } catch (e) {
      alert(e.message);
    }
  }

  function entryLabel(entry) {
    const parts = [];
    if (entry.chance) parts.push(`${entry.chance}%:`);
    if (entry.dice) {
      let qty = entry.dice;
      if (entry.multiplier && entry.multiplier > 1) qty += ` x ${entry.multiplier.toLocaleString()}`;
      parts.push(qty);
    }
    if (entry.type === 'magic') {
      const rolls = entry.rolls || [{ count: entry.count || 1, table: entry.subtype || 'any' }];
      const descs = rolls.map(r => `${r.count} ${r.table === 'any' ? 'magic item' : r.table}${r.count > 1 ? 's' : ''}`);
      parts.push(descs.join(' + '));
    } else {
      parts.push(entry.type);
    }
    return parts.join(' ');
  }
</script>

<svelte:head>
  <title>{tt?.name ?? 'Treasure Type'} — OSE Sheet</title>
</svelte:head>

<PageWrapper title={tt?.key ?? 'Treasure Type'} maxWidth="max-w-3xl">
  {#if loading}
    <p class="text-ink-faint">Loading...</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else if tt}
    <div class="panel mb-4">
      <div class="flex items-start justify-between mb-4">
        <div>
          <h1 class="font-serif text-3xl text-ink">{tt.name}</h1>
          <p class="text-ink-faint text-sm mt-1">
            {CAT_LABELS[tt.category] ?? tt.category}
            · Avg: {(tt.average_gp ?? 0).toLocaleString()} gp
            {#if !tt.is_default}
              · <Badge label="Custom" variant="gm" />
            {/if}
          </p>
        </div>
        <div class="text-right">
          <div class="font-serif text-4xl text-ink">{tt.key}</div>
        </div>
      </div>

      <!-- Entries breakdown -->
      <h3 class="section-title">Roll Table</h3>
      <div class="space-y-1">
        {#each tt.entries as entry}
          <div class="flex items-baseline gap-2 text-sm">
            <span class="text-ink-faint w-12 text-right shrink-0">
              {entry.chance ? `${entry.chance}%` : '—'}
            </span>
            <span class="text-ink">{entryLabel(entry)}</span>
          </div>
        {/each}
      </div>
    </div>

    <!-- Roller -->
    <div class="panel mb-4">
      <h3 class="section-title">Roll {tt.key}</h3>
      <TreasureRoller treasureType={tt.key} showInput={false} />
    </div>

    <div class="flex gap-3">
      <a href="/treasure/{typeId}/edit" class="btn">Edit</a>
      <button class="btn-danger" on:click={deleteType}>Delete</button>
      <a href="/treasure" class="btn-ghost ml-auto">Back</a>
    </div>
  {/if}
</PageWrapper>
