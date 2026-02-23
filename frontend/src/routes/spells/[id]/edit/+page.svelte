<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import SpellForm from '$lib/components/spells/SpellForm.svelte';

  // Admin guard
  $: if (browser && $isAdmin === false) goto('/campaigns');

  const spellId = $page.params.id;

  let spell = null;
  let loading = true;
  let error = '';

  onMount(async () => {
    try {
      spell = await api.get(`/spells/${spellId}`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  async function handleSubmit(payload) {
    // SpellUpdate schema does not accept is_default
    const { is_default, ...updatePayload } = payload;
    await api.patch(`/spells/${spellId}`, updatePayload);
    goto(`/spells/${spellId}`);
  }
</script>

<svelte:head>
  <title>Edit {spell?.name || 'Spell'} — OSE Sheet</title>
</svelte:head>

<PageWrapper title="Edit {spell?.name || 'Spell'}">
  {#if loading}
    <p class="text-ink-faint">Loading...</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else if spell}
    <SpellForm
      initialData={spell}
      onSubmit={handleSubmit}
    />
  {/if}
</PageWrapper>
