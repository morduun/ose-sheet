<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import Badge from '$lib/components/shared/Badge.svelte';
  import Markdown from '$lib/components/shared/Markdown.svelte';

  // Admin guard
  $: if (browser && $isAdmin === false) goto('/campaigns');

  const monsterId = $page.params.id;

  let monster = null;
  let loading = true;
  let error = '';
  let deleteError = '';
  let confirmDelete = false;

  onMount(async () => {
    try {
      monster = await api.get(`/monsters/${monsterId}`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  async function handleDelete() {
    try {
      await api.delete(`/monsters/${monsterId}`);
      goto('/monsters');
    } catch (e) {
      deleteError = e.message;
      confirmDelete = false;
    }
  }

  $: meta = monster?.monster_metadata || {};
  $: attacks = meta.attacks || [];
  $: saves = meta.saves || {};
  $: hasSaves = Object.keys(saves).length > 0;
  $: numberAppearing = meta.number_appearing || {};
  $: treasureType = meta.treasure_type || [];
  $: abilities = meta.abilities || {};
  $: abilityKeys = Object.keys(abilities);
</script>

<svelte:head>
  <title>{monster?.name || 'Monster'} — OSE Sheet</title>
</svelte:head>

<PageWrapper>
  {#if loading}
    <p class="text-ink-faint">Loading...</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else if monster}
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3 flex-wrap">
        <h1 class="font-serif text-3xl text-ink">{monster.name}</h1>
        {#if monster.alignment}
          <Badge label={monster.alignment} variant="default" />
        {/if}
      </div>
      <div class="flex gap-2">
        <a href="/monsters/{monsterId}/edit" class="btn">Edit</a>
        {#if confirmDelete}
          <button class="btn-danger" on:click={handleDelete}>Confirm Delete</button>
          <button class="btn-ghost" on:click={() => confirmDelete = false}>Cancel</button>
        {:else}
          <button class="btn-danger" on:click={() => confirmDelete = true}>Delete</button>
        {/if}
      </div>
    </div>

    {#if deleteError}
      <p class="text-red-700 text-sm mb-4">{deleteError}</p>
    {/if}

    <!-- Stats Grid -->
    <div class="panel mb-4">
      <h2 class="section-title">Stats</h2>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
        <div><span class="text-ink-faint">AC:</span> <strong class="font-serif text-lg">{monster.ac ?? '—'}</strong></div>
        <div><span class="text-ink-faint">HD:</span> <strong>{monster.hit_dice ?? '—'}</strong></div>
        <div><span class="text-ink-faint">HP:</span> <strong>{monster.hp ?? '—'}</strong></div>
        <div><span class="text-ink-faint">THAC0:</span> <strong>{monster.thac0 ?? '—'}</strong></div>
        <div><span class="text-ink-faint">Movement:</span> <strong>{monster.movement_rate ?? '—'}</strong></div>
        <div><span class="text-ink-faint">Morale:</span> <strong>{monster.morale ?? '—'}</strong></div>
        <div><span class="text-ink-faint">Alignment:</span> <strong>{monster.alignment ?? '—'}</strong></div>
        <div><span class="text-ink-faint">XP:</span> <strong>{monster.xp ?? '—'}</strong></div>
      </div>
    </div>

    <!-- Saves -->
    {#if hasSaves}
      <div class="panel mb-4">
        <h2 class="section-title">Saving Throws</h2>
        <div class="grid grid-cols-5 gap-4 text-sm text-center">
          <div><span class="text-ink-faint block text-xs">Death</span> <strong>{saves.D ?? '—'}</strong></div>
          <div><span class="text-ink-faint block text-xs">Wands</span> <strong>{saves.W ?? '—'}</strong></div>
          <div><span class="text-ink-faint block text-xs">Paralysis</span> <strong>{saves.P ?? '—'}</strong></div>
          <div><span class="text-ink-faint block text-xs">Breath</span> <strong>{saves.B ?? '—'}</strong></div>
          <div><span class="text-ink-faint block text-xs">Spells</span> <strong>{saves.S ?? '—'}</strong></div>
        </div>
      </div>
    {/if}

    <!-- Attacks -->
    {#if attacks.length > 0}
      <div class="panel mb-4">
        <h2 class="section-title">Attacks</h2>
        <table class="w-full text-sm">
          <thead>
            <tr class="text-xs text-ink-faint uppercase tracking-wide">
              <th class="text-left pb-1">Attack</th>
              <th class="text-left pb-1">Damage</th>
              <th class="text-left pb-1">Effects</th>
            </tr>
          </thead>
          <tbody>
            {#each attacks as atk}
              <tr class="border-t border-parchment-200">
                <td class="py-1 font-medium">{atk.name}</td>
                <td class="py-1">{atk.damage || '—'}</td>
                <td class="py-1 text-ink-faint">{atk.effects || '—'}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}

    <!-- Number Appearing & Treasure Type -->
    {#if numberAppearing.wild || numberAppearing.lair || treasureType.length > 0}
      <div class="panel mb-4">
        <h2 class="section-title">Encounter Details</h2>
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
          {#if numberAppearing.wild}
            <div><span class="text-ink-faint">No. Appearing (Wild):</span> <strong>{numberAppearing.wild}</strong></div>
          {/if}
          {#if numberAppearing.lair}
            <div><span class="text-ink-faint">No. Appearing (Lair):</span> <strong>{numberAppearing.lair}</strong></div>
          {/if}
          {#if treasureType.length > 0}
            <div><span class="text-ink-faint">Treasure Type:</span> <strong>{treasureType.join(', ')}</strong></div>
          {/if}
        </div>
      </div>
    {/if}

    <!-- Abilities -->
    {#if abilityKeys.length > 0}
      <div class="panel mb-4">
        <h2 class="section-title">Abilities</h2>
        <div class="space-y-3">
          {#each abilityKeys as key}
            <div>
              <h3 class="font-medium text-ink">{key}</h3>
              <div class="text-sm text-ink-light">
                <Markdown text={abilities[key]} />
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Description -->
    {#if monster.description}
      <div class="panel mb-4">
        <h2 class="section-title">Description</h2>
        <div class="text-sm text-ink">
          <Markdown text={monster.description} />
        </div>
      </div>
    {/if}

    <div class="mt-6">
      <a href="/monsters" class="btn-ghost">&larr; Back to Monsters</a>
    </div>
  {/if}
</PageWrapper>
