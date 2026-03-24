<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import SpecialistTypeForm from '$lib/components/specialists/SpecialistTypeForm.svelte';

  const typeId = $page.params.id;

  let st = null;
  let loading = true;
  let error = '';

  $: if (browser && $isAdmin === false) goto('/campaigns');

  onMount(async () => {
    try {
      st = await api.get(`/specialist-types/${typeId}`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  async function handleSubmit(payload) {
    await api.patch(`/specialist-types/${typeId}`, payload);
    goto(`/specialists/${typeId}`);
  }
</script>

<svelte:head>
  <title>Edit {st?.name ?? 'Specialist Type'} — OSE Sheet</title>
</svelte:head>

<PageWrapper title="Edit Specialist Type" maxWidth="max-w-2xl">
  {#if loading}
    <p class="text-ink-faint">Loading...</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else if st}
    <SpecialistTypeForm initialData={st} onSubmit={handleSubmit} />
  {/if}
</PageWrapper>
