<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import MonsterForm from '$lib/components/monsters/MonsterForm.svelte';

  // Admin guard
  $: if (browser && $isAdmin === false) goto('/campaigns');

  const monsterId = $page.params.id;

  let monster = null;
  let loading = true;
  let error = '';

  onMount(async () => {
    try {
      monster = await api.get(`/monsters/${monsterId}`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  async function handleSubmit(payload) {
    const { is_default, campaign_id, ...updatePayload } = payload;
    await api.patch(`/monsters/${monsterId}`, updatePayload);
    goto(`/monsters/${monsterId}`);
  }
</script>

<svelte:head>
  <title>Edit {monster?.name || 'Monster'} — OSE Sheet</title>
</svelte:head>

<PageWrapper title="Edit {monster?.name || 'Monster'}">
  {#if loading}
    <p class="text-ink-faint">Loading...</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else if monster}
    <MonsterForm
      initialData={monster}
      onSubmit={handleSubmit}
    />
  {/if}
</PageWrapper>
