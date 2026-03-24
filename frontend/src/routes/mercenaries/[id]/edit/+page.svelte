<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import MercenaryTypeForm from '$lib/components/mercenaries/MercenaryTypeForm.svelte';

  const typeId = $page.params.id;

  let mt = null;
  let loading = true;
  let error = '';

  $: if (browser && $isAdmin === false) goto('/campaigns');

  onMount(async () => {
    try {
      mt = await api.get(`/mercenary-types/${typeId}`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  async function handleSubmit(payload) {
    await api.patch(`/mercenary-types/${typeId}`, payload);
    goto(`/mercenaries/${typeId}`);
  }
</script>

<svelte:head>
  <title>Edit {mt?.name ?? 'Mercenary Type'} — OSE Sheet</title>
</svelte:head>

<PageWrapper title="Edit Mercenary Type" maxWidth="max-w-2xl">
  {#if loading}
    <p class="text-ink-faint">Loading...</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else if mt}
    <MercenaryTypeForm initialData={mt} onSubmit={handleSubmit} />
  {/if}
</PageWrapper>
