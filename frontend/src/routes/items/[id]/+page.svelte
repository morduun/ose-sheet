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
  import { WEAPON_QUALITIES, itemTypeLabel, normalizeQualities } from '$lib/item-metadata.js';

  // Admin guard
  $: if (browser && $isAdmin === false) goto('/campaigns');

  const itemId = $page.params.id;

  let item = null;
  let loading = true;
  let error = '';
  let deleteError = '';
  let confirmDelete = false;
  let metaExpanded = false;

  onMount(async () => {
    try {
      item = await api.get(`/items/${itemId}`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  async function handleDelete() {
    try {
      await api.delete(`/items/${itemId}`);
      goto('/items');
    } catch (e) {
      deleteError = e.message;
      confirmDelete = false;
    }
  }

  function formatCost(cost) {
    if (cost == null) return null;
    if (cost < 1) return `${Math.round(cost * 100)} cp`;
    return `${cost} gp`;
  }

  // Extract notable metadata fields for the properties panel
  function getMetaProperties(meta) {
    if (!meta) return [];
    const props = [];
    if (meta.damage_dice) props.push(['Damage', meta.damage_dice]);
    if (meta.weapon_type) props.push(['Weapon Type', meta.weapon_type]);
    if (meta.range) props.push(['Range', meta.range]);
    if (meta.ac != null) props.push(['AC', meta.ac]);
    if (meta.ac_bonus != null) props.push(['AC Bonus', `+${meta.ac_bonus}`]);
    if (meta.armor_type) props.push(['Armor Type', meta.armor_type]);
    if (meta.requires_ammo) props.push(['Requires', meta.requires_ammo]);
    if (meta.effect) props.push(['Effect', meta.effect]);
    if (meta.charges != null) props.push(['Charges', meta.charges]);
    if (meta.duration) props.push(['Duration', meta.duration]);
    if (meta.spell_name) props.push(['Spell', meta.spell_name]);
    if (meta.spell_level != null) props.push(['Spell Level', meta.spell_level]);
    if (meta.spell_class) props.push(['Class', meta.spell_class]);
    if (meta.save != null) props.push(['Save', `${meta.save}+`]);
    if (meta.onset) props.push(['Onset', meta.onset]);
    if (meta.effect_failed) props.push(['On Fail', meta.effect_failed]);
    if (meta.effect_saved) props.push(['On Save', meta.effect_saved]);
    if (meta.detection != null) props.push(['Detection', `${meta.detection}%`]);
    return props;
  }
</script>

<svelte:head>
  <title>{item?.name || 'Item'} — OSE Sheet</title>
</svelte:head>

<PageWrapper>
  {#if loading}
    <p class="text-ink-faint">Loading...</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else if item}
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3 flex-wrap">
        <h1 class="font-serif text-3xl text-ink">
          {item.name}
          {#if item.unidentified_name}
            <span class="text-lg text-ink-faint font-sans">({item.unidentified_name})</span>
          {/if}
        </h1>
        <Badge label={itemTypeLabel(item)} variant="default" />
        {#if item.equippable}
          <Badge label="equippable" variant="gm" />
        {/if}
        {#if normalizeQualities(item.item_metadata?.qualities).length}
          {#each normalizeQualities(item.item_metadata?.qualities) as q}
            <span
              class="text-xs px-2 py-0.5 rounded bg-parchment-200 text-ink-faint"
              title={WEAPON_QUALITIES[q] ?? ''}
            >{q}</span>
          {/each}
        {/if}
      </div>
      <div class="flex gap-2">
        <a href="/items/{itemId}/edit" class="btn">Edit</a>
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

    <!-- Properties -->
    {#if item.weight != null || item.cost_gp != null || getMetaProperties(item.item_metadata).length > 0}
      <div class="panel mb-4">
        <h2 class="section-title">Properties</h2>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          {#if item.weight != null}
            <div><span class="text-ink-faint">Weight:</span> <strong>{item.weight} coins</strong></div>
          {/if}
          {#if item.cost_gp != null}
            <div><span class="text-ink-faint">Cost:</span> <strong>{formatCost(item.cost_gp)}</strong></div>
          {/if}
          {#each getMetaProperties(item.item_metadata) as [label, value]}
            <div><span class="text-ink-faint">{label}:</span> <strong>{value}</strong></div>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Player Description -->
    {#if item.description_player}
      <div class="panel mb-4">
        <h2 class="section-title">Player Description</h2>
        <div class="text-sm text-ink">
          <Markdown text={item.description_player} />
        </div>
      </div>
    {/if}

    <!-- GM Description -->
    {#if item.description_gm}
      <div class="panel mb-4">
        <h2 class="section-title">GM Description</h2>
        <div class="text-sm text-ink">
          <Markdown text={item.description_gm} />
        </div>
      </div>
    {/if}

    <!-- Secrets -->
    {#if item.secrets?.length}
      <div class="panel mb-4">
        <h2 class="section-title">Secrets</h2>
        <div class="space-y-2">
          {#each item.secrets as secret, i}
            <div class="flex items-start gap-2 text-sm">
              <span class="shrink-0">
                {#if secret.revealed}
                  <Badge label="revealed" variant="default" />
                {:else}
                  <Badge label="hidden" variant="gm" />
                {/if}
              </span>
              <span class="text-ink">{secret.text}</span>
            </div>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Metadata (collapsible) -->
    {#if item.item_metadata}
      <div class="panel mb-4">
        <button
          class="section-title w-full text-left flex items-center justify-between"
          on:click={() => metaExpanded = !metaExpanded}
        >
          <span>Metadata</span>
          <span class="text-ink-faint text-sm">{metaExpanded ? '▼' : '▶'}</span>
        </button>
        {#if metaExpanded}
          <pre class="mt-2 text-xs font-mono bg-parchment-100 p-3 rounded overflow-x-auto">{JSON.stringify(item.item_metadata, null, 2)}</pre>
        {/if}
      </div>
    {/if}

    <div class="mt-6">
      <a href="/items" class="btn-ghost">&larr; Back to Items</a>
    </div>
  {/if}
</PageWrapper>
