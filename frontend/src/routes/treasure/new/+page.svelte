<script>
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { api } from '$lib/api.js';
  import { isAdmin } from '$lib/stores.js';
  import PageWrapper from '$lib/components/PageWrapper.svelte';
  import TreasureTypeForm from '$lib/components/treasure/TreasureTypeForm.svelte';

  $: if (browser && $isAdmin === false) goto('/campaigns');

  async function handleSubmit(payload) {
    const tt = await api.post('/treasure-types', payload);
    goto(`/treasure/${tt.id}`);
  }
</script>

<svelte:head>
  <title>New Treasure Type — OSE Sheet</title>
</svelte:head>

<PageWrapper title="New Treasure Type" maxWidth="max-w-2xl">
  <TreasureTypeForm onSubmit={handleSubmit} />
</PageWrapper>
