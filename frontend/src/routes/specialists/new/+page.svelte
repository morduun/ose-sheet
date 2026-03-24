<script>
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import SpecialistTypeForm from '$lib/components/specialists/SpecialistTypeForm.svelte';

  $: if (browser && $isAdmin === false) goto('/campaigns');

  async function handleSubmit(payload) {
    const st = await api.post('/specialist-types', payload);
    goto(`/specialists/${st.id}`);
  }
</script>

<svelte:head>
  <title>New Specialist Type — OSE Sheet</title>
</svelte:head>

<PageWrapper title="New Specialist Type" maxWidth="max-w-2xl">
  <SpecialistTypeForm onSubmit={handleSubmit} />
</PageWrapper>
