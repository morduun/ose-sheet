<script>
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import VehicleTypeForm from '$lib/components/vehicles/VehicleTypeForm.svelte';

  $: if (browser && $isAdmin === false) goto('/campaigns');

  async function handleSubmit(payload) {
    const vt = await api.post('/vehicle-types', payload);
    goto(`/vehicles/${vt.id}`);
  }
</script>

<svelte:head>
  <title>New Vehicle Type — OSE Sheet</title>
</svelte:head>

<PageWrapper title="New Vehicle Type" maxWidth="max-w-2xl">
  <VehicleTypeForm onSubmit={handleSubmit} />
</PageWrapper>
