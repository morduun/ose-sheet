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

  const spellId = $page.params.id;

  let spell = null;
  let loading = true;
  let error = '';
  let deleteError = '';
  let confirmDelete = false;

  onMount(async () => {
    try {
      spell = await api.get(`/spells/${spellId}`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  async function handleDelete() {
    try {
      await api.delete(`/spells/${spellId}`);
      goto('/spells');
    } catch (e) {
      deleteError = e.message;
      confirmDelete = false;
    }
  }
</script>

<svelte:head>
  <title>{spell?.name || 'Spell'} — OSE Sheet</title>
</svelte:head>

<PageWrapper>
  {#if loading}
    <p class="text-ink-faint">Loading...</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else if spell}
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <h1 class="font-serif text-3xl text-ink">{spell.name}</h1>
        <Badge label={spell.spell_class} variant="default" />
        <Badge label="Lvl {spell.level}" variant="default" />
      </div>
      <div class="flex gap-2">
        <a href="/spells/{spellId}/edit" class="btn">Edit</a>
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
    {#if spell.range || spell.duration || spell.aoe || spell.save}
      <div class="panel mb-4">
        <h2 class="section-title">Properties</h2>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          {#if spell.range}
            <div><span class="text-ink-faint">Range:</span> <strong>{spell.range}</strong></div>
          {/if}
          {#if spell.duration}
            <div><span class="text-ink-faint">Duration:</span> <strong>{spell.duration}</strong></div>
          {/if}
          {#if spell.aoe}
            <div><span class="text-ink-faint">Area of Effect:</span> <strong>{spell.aoe}</strong></div>
          {/if}
          {#if spell.save}
            <div><span class="text-ink-faint">Save:</span> <strong>{spell.save}</strong></div>
          {/if}
        </div>
      </div>
    {/if}

    <!-- Description -->
    <div class="panel mb-4">
      <h2 class="section-title">Description</h2>
      <div class="text-sm text-ink">
        <Markdown text={spell.description} />
      </div>
    </div>

    <!-- Reversed Form -->
    {#if spell.reversed}
      <div class="panel mb-4">
        <h2 class="section-title">Reversed Form</h2>
        <div class="text-sm text-ink">
          <Markdown text={spell.reversed} />
        </div>
      </div>
    {/if}

    <div class="mt-6">
      <a href="/spells" class="btn-ghost">&larr; Back to Spells</a>
    </div>
  {/if}
</PageWrapper>
