<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import TreasureTypeForm from '$lib/components/treasure/TreasureTypeForm.svelte';

  const typeId = $page.params.id;

  let tt = null;
  let loading = true;
  let error = '';

  $: if (browser && $isAdmin === false) goto('/campaigns');

  onMount(async () => {
    try {
      tt = await api.get(`/treasure-types/${typeId}`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  async function handleSubmit(payload) {
    await api.patch(`/treasure-types/${typeId}`, payload);
    goto(`/treasure/${typeId}`);
  }
</script>

<svelte:head>
  <title>Edit {tt?.name ?? 'Treasure Type'} — OSE Sheet</title>
</svelte:head>

<PageWrapper title="Edit Treasure Type" maxWidth="max-w-2xl">
  {#if loading}
    <p class="text-ink-faint">Loading...</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else if tt}
    <TreasureTypeForm initialData={tt} onSubmit={handleSubmit} />
  {/if}
</PageWrapper>
