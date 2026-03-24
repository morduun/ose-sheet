<script>
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import MercenaryTypeForm from '$lib/components/mercenaries/MercenaryTypeForm.svelte';

  $: if (browser && $isAdmin === false) goto('/campaigns');

  async function handleSubmit(payload) {
    const mt = await api.post('/mercenary-types', payload);
    goto(`/mercenaries/${mt.id}`);
  }
</script>

<svelte:head>
  <title>New Mercenary Type — OSE Sheet</title>
</svelte:head>

<PageWrapper title="New Mercenary Type" maxWidth="max-w-2xl">
  <MercenaryTypeForm onSubmit={handleSubmit} />
</PageWrapper>
