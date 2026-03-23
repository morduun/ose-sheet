<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import VehicleTypeForm from '$lib/components/vehicles/VehicleTypeForm.svelte';

  const typeId = $page.params.id;

  let vt = null;
  let loading = true;
  let error = '';

  $: if (browser && $isAdmin === false) goto('/campaigns');

  onMount(async () => {
    try {
      vt = await api.get(`/vehicle-types/${typeId}`);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  async function handleSubmit(payload) {
    await api.patch(`/vehicle-types/${typeId}`, payload);
    goto(`/vehicles/${typeId}`);
  }
</script>

<svelte:head>
  <title>Edit {vt?.name ?? 'Vehicle Type'} — OSE Sheet</title>
</svelte:head>

<PageWrapper title="Edit Vehicle Type" maxWidth="max-w-2xl">
  {#if loading}
    <p class="text-ink-faint">Loading...</p>
  {:else if error}
    <p class="text-red-700">{error}</p>
  {:else if vt}
    <VehicleTypeForm initialData={vt} onSubmit={handleSubmit} />
  {/if}
</PageWrapper>
